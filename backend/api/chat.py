import os
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.modules.translate import translate as translate_module
from backend.modules.multidoc import answer_multidoc
from backend.core.prompts import build_system_prompt

router = APIRouter(prefix="/api", tags=["chat"])

ALLOWED_MODULES = {"generic", "insurance", "multidoc", "numbers", "translate", "summarise", "compare"}
MULTIDOC_SESSION_TTL_SECONDS = int(os.getenv("MULTIDOC_SESSION_TTL_SECONDS", "7200"))
MULTIDOC_MAX_SESSIONS = int(os.getenv("MULTIDOC_MAX_SESSIONS", "200"))
_multidoc_session_store: Dict[str, Dict[str, Any]] = {}


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
