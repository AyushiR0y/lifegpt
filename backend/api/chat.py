import os
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.modules.translate import translate as translate_module
from backend.modules.multidoc import answer_multidoc
from backend.modules.summarization.document_parser import DocumentParser
from backend.modules.summarization.pii_masker import PIIMasker
from backend.modules.summarization.summarizer import DocumentSummarizer
from backend.core.prompts import build_system_prompt
from openai import AzureOpenAI

router = APIRouter(prefix="/api", tags=["chat"])

ALLOWED_MODULES = {"generic", "insurance", "multidoc", "numbers", "translate", "summarise", "compare"}
MULTIDOC_SESSION_TTL_SECONDS = int(os.getenv("MULTIDOC_SESSION_TTL_SECONDS", "7200"))
MULTIDOC_MAX_SESSIONS = int(os.getenv("MULTIDOC_MAX_SESSIONS", "200"))
_multidoc_session_store: Dict[str, Dict[str, Any]] = {}
_summarization_parser = DocumentParser()
_summarization_masker = PIIMasker()
_summarization_client = AzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    azure_endpoint=os.getenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://balic-gpt-contentgenerationnew.openai.azure.com",
    ),
    api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
)
_summarization_llm = DocumentSummarizer(
    _summarization_client,
    os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o",
)


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _looks_like_summary_request(query_text: str) -> bool:
    text = (query_text or "").lower()
    signals = (
        "summarize",
        "summarise",
        "summary",
        "brief",
        "outline",
        "key points",
        "main points",
        "extract",
    )
    return any(signal in text for signal in signals)


def _decode_attachment_bytes(attachment: Dict[str, Any]) -> tuple[bytes, str]:
    name = str(attachment.get("name") or "upload")
    content = attachment.get("content") or {}
    raw = content.get("raw") if isinstance(content, dict) else attachment.get("raw")
    is_base64 = bool(content.get("isBase64")) if isinstance(content, dict) else False

    if isinstance(raw, bytes):
        return raw, name
    if not isinstance(raw, str):
        return b"", name

    if is_base64 and raw.startswith("data:"):
        header, encoded = raw.split(",", 1)
        return translate_module.base64.b64decode(encoded), name
    if is_base64:
        try:
            return translate_module.base64.b64decode(raw), name
        except Exception:
            return raw.encode("utf-8", errors="ignore"), name

    return raw.encode("utf-8", errors="ignore"), name


def _summarize_document_from_chat(payload: Dict[str, Any], attachments: list) -> Dict[str, Any]:
    if not attachments:
        raise HTTPException(status_code=400, detail="Upload a document to summarize it in Generic mode.")

    first_attachment = attachments[0]
    file_bytes, filename = _decode_attachment_bytes(first_attachment)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded document is empty or unreadable.")

    try:
        doc = _summarization_parser.parse(file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse document for summarization: {exc}")

    summary_depth = payload.get("summary_depth")
    if summary_depth == "concise":
        summary_type = "concise"
    elif summary_depth == "detailed":
        summary_type = "descriptive"
    else:
        summary_type = "mid_level"

    masked_text = _summarization_masker.mask_text(doc.text)
    summary = _summarization_llm.generate_summary(
        text=masked_text,
        summary_type=summary_type,
        file_type=doc.file_type,
        metadata=doc.metadata,
        images=getattr(doc, "images", []),
    )
    return {
        "content": [{"text": _summarization_masker.unmask_text(summary)}],
    }


def _cleanup_multidoc_sessions() -> None:
    now = time.time()
    expired = [
        chat_id
        for chat_id, payload in _multidoc_session_store.items()
        if now - float(payload.get("updated_at", now)) > MULTIDOC_SESSION_TTL_SECONDS
    ]
    for chat_id in expired:
        _multidoc_session_store.pop(chat_id, None)

    if len(_multidoc_session_store) <= MULTIDOC_MAX_SESSIONS:
        return

    ordered = sorted(
        _multidoc_session_store.items(),
        key=lambda item: float(item[1].get("updated_at", 0.0)),
    )
    overflow = len(_multidoc_session_store) - MULTIDOC_MAX_SESSIONS
    for chat_id, _ in ordered[:overflow]:
        _multidoc_session_store.pop(chat_id, None)


def _resolve_multidoc_attachments(chat_id: str, attachments: list) -> list:
    _cleanup_multidoc_sessions()

    if attachments:
        if chat_id:
            _multidoc_session_store[chat_id] = {
                "attachments": attachments,
                "updated_at": time.time(),
            }
        return attachments

    if chat_id and chat_id in _multidoc_session_store:
        cached = _multidoc_session_store[chat_id]
        cached["updated_at"] = time.time()
        return cached.get("attachments", [])

    return []


async def _run_chat(payload: Dict, forced_mode: str | None = None):
    messages = payload.get("messages", [])
    mode = forced_mode or payload.get("mode", "generic")
    summary_depth = payload.get("summary_depth")
    model = payload.get("model")
    max_tokens = int(payload.get("max_tokens", 1200))
    attachments = payload.get("attachments", [])
    chat_id = str(payload.get("chat_id") or "").strip()

    incoming_system = str(payload.get("system") or "").strip()
    module_system = incoming_system or build_system_prompt(mode, summary_depth)

    query_text = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            query_text = str(last_message.get("content") or "")

    if mode == "generic" and attachments and _looks_like_summary_request(query_text):
        return _summarize_document_from_chat(payload, attachments)

    if mode == "multidoc":
        active_attachments = _resolve_multidoc_attachments(chat_id, attachments)
        answer = await answer_multidoc(
            messages=messages,
            attachments=active_attachments,
            chat_id=chat_id,
            model=model,
            max_tokens=max_tokens,
        )
        return {"content": [{"text": answer}]}

    attachment_context = translate_module.build_attachment_context(attachments, query_text=query_text, mode=mode)
    if attachment_context and messages:
        last_message = messages[-1]
        if isinstance(last_message, dict) and isinstance(last_message.get("content"), str):
            last_message = dict(last_message)
            last_message["content"] = f"{last_message['content']}{attachment_context}"
            messages = messages[:-1] + [last_message]

    guardrails = (
        "You are LifeGPT, a professional assistant for finance, insurance, regulations, and document analysis. "
        "Refuse any personal, informal, social, entertainment, or unrelated questions. "
        "Do not answer requests that are outside the active module. "
        "If the user asks for private information, credentials, account details, or other personal data, "
        "treat it as redacted and do not repeat it."
    )

    combined_system = f"{guardrails}\n\n{module_system}".strip()
    answer = translate_module.call_azure_openai_chat(messages, combined_system, model=model, max_tokens=max_tokens)
    return {"content": [{"text": answer}]}


@router.post("/chat")
async def api_chat(payload: Dict):
    """Proxy chat requests to Azure OpenAI using credentials from .env."""
    return await _run_chat(payload)


@router.post("/modules/{module_name}/chat")
async def api_module_chat(module_name: str, payload: Dict):
    mode = (module_name or "").strip().lower()
    if mode not in ALLOWED_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_name}")
    return await _run_chat(payload, forced_mode=mode)
