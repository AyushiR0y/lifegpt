import os
import time
import re
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

MODE_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "summarise": (
        "summarise", "summarize", "summary", "gist", "main points", "key points",
        "concise overview", "quick overview", "brief overview", "tl;dr", "tldr",
        "executive summary", "condense", "in short", "extract", "abstract", "synopsis", "recap", "highlights",
        "summarization", "summarisation",
    ),
    "insurance": (
        "insurance", "policy", "premium", "claim", "coverage", "underwrite", "beneficiary",
        "deductible", "insurer", "insured", "annuity", "reinsurance", "irdai", "irda","insurance regulatory and development authority of india",
        "life insurance", "health insurance", "auto insurance", "property insurance", "liability insurance",
        "insurance industry", "insurance market", "insurance trends", "insurance regulations",
        "insurance analysis", "insurance insights", "insurance data",
        "questions about insurance", "insurance questions", "analyze insurance", "insurance analysis",
        "insurance policy", "insurance claim", "insurance coverage", "insurance premium", "insurance regulation",
    ),
    "multidoc": (
        "multi-doc", "multi doc", "multiple documents", "across documents", "across files","detailed analysis across documents", "synthesize information across documents", "integrate information across documents",
        "from all documents", "cross document", "combine documents",
    ),
    "compare": (
        "compare", "comparison", "difference", "differences", "contrast", "versus", "vs ",
        "side by side", "tabular comparison", "compare and contrast", "similarities and differences","compare across documents", "compare files",
    ),
    "numbers": (
        "numbers", "numeric", "data analysis", "financial analysis", "financial result", "financial results", "amount", "amounts",
        "figure", "figures", "statistics", "ratio", "variance", "growth", "trend", "percent",
        "percentage", "inr", "rs.", "rupee", "rupees", "currency", "calc", "calculate", "profit", "loss", 
        "revenue", "cost", "expense", "cash flow", "balance sheet", "income statement", "financial statement", "p&l", "profit and loss", "quarterly result", "quarterly results", "kpi", "key performance indicator", "financial metric", "numeric insight", "data insight",
        "quantitative analysis", "evidence-backed analysis", "number-backed analysis", "numeric summary", 
        "numeric breakdown", "numeric trends", "numeric inconsistencies", "numeric risks", "data-quality caveats", "numeric conclusions",
    ),
    "translate": (
        "translate", "translation", "translate document", "convert language", "hindi", "marathi",
        "gujarati", "tamil", "telugu", "bengali", "french", "german", "spanish", "italian",
        "portuguese", "russian", "chinese", "japanese", "korean", "arabic", "vietnamese", "urdu",
        "language translation", "document translation", "translate text", "translation request",
    ),
}

FILE_HEAVY_MODES = {"summarise", "multidoc", "compare", "translate"}

RESPONSE_FORMATTING_RULES = (
    "Formatting requirements for every response:\n"
    "- Use Markdown headings and subheadings.\n"
    "- Use bullet points for key items and findings.\n"
    "- Keep spacing readable with blank lines between sections.\n"
    "- Use section dividers (---) for long responses.\n"
    "- Bold important labels and key numbers.\n"
    "- Use Markdown tables when presenting structured comparisons or tabular data."
)


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


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


def _score_mode_keywords(query_text: str) -> Dict[str, int]:
    text = (query_text or "").lower()
    if not text:
        return {}

    def has_keyword(keyword: str) -> bool:
        key = str(keyword or "").strip().lower()
        if not key:
            return False
        # For phrase keywords, substring matching is acceptable.
        if " " in key or ";" in key or ":" in key:
            return key in text
        # For single-word keywords, enforce token boundaries to reduce false positives.
        return re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", text) is not None

    scores: Dict[str, int] = {}
    for mode, keywords in MODE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if has_keyword(kw):
                score += 2 if " " in kw else 1
        if score > 0:
            scores[mode] = score
    return scores


def _resolve_effective_mode(incoming_mode: str, query_text: str, attachments: list) -> tuple[str, list[str]]:
    current = (incoming_mode or "generic").strip().lower()
    if current not in ALLOWED_MODULES:
        current = "generic"

    scores = _score_mode_keywords(query_text)
    if not scores:
        return current, []

    attachment_count = len(attachments or [])
    ranked_modes = sorted(scores.keys(), key=lambda key: scores[key], reverse=True)

    # Avoid selecting file-heavy modes when no files are attached.
    filtered = [mode for mode in ranked_modes if not (mode in FILE_HEAVY_MODES and attachment_count == 0)]
    requested = filtered or ranked_modes

    # Keep current mode unless another mode is clearly stronger, while still allowing active switching.
    effective = current
    if requested:
        top_mode = requested[0]
        top_score = scores.get(top_mode, 0)
        current_score = scores.get(current, 0)

        if current == "generic":
            effective = top_mode
        elif top_mode != current and top_score >= current_score + 1:
            effective = top_mode
        elif current not in requested:
            effective = top_mode

    return effective, requested


def _looks_structured_markdown(text: str) -> bool:
    raw = str(text or "")
    return re.search(r"(^|\n)\s*(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|```|\|.+\|)", raw, flags=re.M) is not None


def _looks_like_summary_output(text: str) -> bool:
    """Check if text looks like a summary with section headers and Label: Description pairs."""
    raw = str(text or "").lower()
    # Common summary section headers
    summary_headers = ("overview", "main content", "key details", "conclusion", "summary", "executive", "detail")
    has_headers = any(f"\n{h}" in raw for h in summary_headers)
    # Check for "Label: Description" pairs
    has_label_pairs = re.search(r"\n\s*[A-Z][A-Za-z\s]+:\s*.+", text) is not None
    return has_headers or (has_label_pairs and len(text.split("\n")) > 5)


def _format_generic_answer_markdown(text: str) -> str:
    raw = str(text or "").replace("\r\n", "\n").strip()
    if not raw:
        return "## Response Overview\n\n- No content returned."
    if raw.lower().startswith("this question is outside the scope of lifegpt") or raw.lower().startswith("this question appears to be outside the scope of lifegpt"):
        return raw
    if _looks_structured_markdown(raw) or _looks_like_summary_output(raw):
        return raw

    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    if not lines:
        return "## Response Overview\n\n- No content returned."

    key_points = []
    details = []
    for line in lines:
        kv = re.match(r"^([A-Za-z][A-Za-z\s/&()'\-]{2,60}):\s*(.+)$", line)
        if kv:
            key_points.append(f"- **{kv.group(1).strip()}:** {kv.group(2).strip()}")
        else:
            details.append(line)

    if not key_points and len(details) == 1:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", details[0]) if s.strip()]
        if len(sentences) >= 3:
            key_points = [f"- {s}" for s in sentences]
            details = []

    output = ["## Response Overview", ""]
    if details:
        output.append(details[0])
    else:
        output.append("Structured response generated.")

    if key_points:
        output.extend(["", "---", "", "## Key Points", ""])
        output.extend(key_points)

    if len(details) > 1:
        output.extend(["", "---", "", "## Additional Details", ""])
        output.extend([f"- {line}" for line in details[1:]])

    return "\n".join(output).strip()


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
    max_tokens = _safe_int(payload.get("max_tokens"), 1200)
    attachments = payload.get("attachments", [])
    chat_id = str(payload.get("chat_id") or "").strip()

    incoming_system = str(payload.get("system") or "").strip()
    module_system = incoming_system or build_system_prompt(mode, summary_depth)

    query_text = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            query_text = str(last_message.get("content") or "")

    resolved_mode, requested_modes = _resolve_effective_mode(mode, query_text, attachments)
    mode = resolved_mode

    # Let users request multiple module lenses in the same chat thread.
    if len(requested_modes) > 1:
        mode_hint = ", ".join(requested_modes)
        incoming_system = (
            f"{incoming_system}\n\nRequested module lenses in this message: {mode_hint}. "
            "When useful, provide a section for each requested lens while staying grounded in uploaded evidence."
        ).strip()

    module_system = incoming_system or build_system_prompt(mode, summary_depth)

    if mode == "summarise" and attachments:
        return {
            **_summarize_document_from_chat(payload, attachments),
            "resolved_mode": mode,
            "requested_modes": requested_modes,
        }

    if mode == "generic" and attachments and _looks_like_summary_request(query_text):
        return {
            **_summarize_document_from_chat(payload, attachments),
            "resolved_mode": "summarise",
            "requested_modes": ["summarise"],
        }

    if mode == "numbers":
        # Allow richer numeric analysis output by reserving a larger completion budget.
        max_tokens = max(max_tokens, 3200)

    if mode == "multidoc":
        active_attachments = _resolve_multidoc_attachments(chat_id, attachments)
        answer = await answer_multidoc(
            messages=messages,
            attachments=active_attachments,
            chat_id=chat_id,
            model=model,
            max_tokens=max_tokens,
        )
        return {
            "content": [{"text": answer}],
            "resolved_mode": mode,
            "requested_modes": requested_modes,
        }

    try:
        attachment_context = translate_module.build_attachment_context(attachments, query_text=query_text, mode=mode)
    except Exception:
        # Do not fail the whole response if context extraction/OCR hits an edge case.
        attachment_context = ""

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

    combined_system = f"{guardrails}\n\n{RESPONSE_FORMATTING_RULES}\n\n{module_system}".strip()
    answer = translate_module.call_azure_openai_chat(messages, combined_system, model=model, max_tokens=max_tokens)
    if mode == "generic":
        answer = _format_generic_answer_markdown(answer)
    return {
        "content": [{"text": answer}],
        "resolved_mode": mode,
        "requested_modes": requested_modes,
    }


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
