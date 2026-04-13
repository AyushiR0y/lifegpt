import os
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.modules.translate import translate as translate_module

_STOP_WORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "for", "on", "at", "with",
    "this", "that", "it", "be", "as", "are", "was", "were", "by", "from", "have", "has",
    "not", "but", "what", "how", "when", "where", "all", "any", "can", "will", "do", "if",
    "its", "they", "we", "you", "i", "he", "she", "them", "there", "so", "more", "about",
    "also", "into", "been", "than", "then", "these", "those", "each", "would", "could", "should",
}


def _tokenize(text: str) -> List[str]:
    return [
        token
        for token in re.sub(r"[^a-z0-9]", " ", (text or "").lower()).split()
        if len(token) > 1 and token not in _STOP_WORDS
    ]


def _bm25_scores(query_tokens: List[str], chunks: List[Dict], k1: float = 1.5, b: float = 0.75) -> List[float]:
    n_docs = len(chunks)
    if not n_docs or not query_tokens:
        return [0.0] * n_docs

    for chunk in chunks:
        if "tokens" not in chunk:
            chunk["tokens"] = _tokenize(chunk.get("text", ""))

    avg_doc_len = sum(len(chunk["tokens"]) for chunk in chunks) / max(n_docs, 1)
    doc_freq: Dict[str, int] = {}
    for chunk in chunks:
        for token in set(chunk["tokens"]):
            doc_freq[token] = doc_freq.get(token, 0) + 1

    scores: List[float] = []
    for chunk in chunks:
        term_freq = Counter(chunk["tokens"])
        doc_len = len(chunk["tokens"])
        score = 0.0
        for token in query_tokens:
            f = term_freq.get(token, 0)
            if not f:
                continue
            idf = np.log((n_docs - doc_freq.get(token, 0) + 0.5) / (doc_freq.get(token, 0) + 0.5) + 1)
            score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1e-9)))
        scores.append(float(score))

    return scores


def _normalize(values: List[float]) -> List[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    span = (hi - lo) + 1e-9
    return [(value - lo) / span for value in values]


def _decode_data_url(data_url: str) -> Tuple[bytes, str]:
    header, encoded = data_url.split(",", 1)
    mime_type = header[5:].split(";", 1)[0].lower()
    return translate_module.base64.b64decode(encoded), mime_type


def _extract_attachment_sections(attachment: Dict) -> List[Dict]:
    name = str(attachment.get("name") or "attachment")
    content = attachment.get("content") or {}
    raw = content.get("raw")
    is_base64 = bool(content.get("isBase64"))

    if not raw:
        return []

    lower_name = name.lower()
    sections: List[Dict] = []

    if is_base64 and isinstance(raw, str) and raw.startswith("data:"):
        file_bytes, mime_type = _decode_data_url(raw)

        if mime_type.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")):
            sections = translate_module.extract_image_sections(file_bytes)
        elif mime_type == "application/pdf" or lower_name.endswith(".pdf"):
            sections = translate_module.extract_pdf_sections(file_bytes)
        elif lower_name.endswith((".xlsx", ".xlsm", ".xls")):
            sections = translate_module.extract_spreadsheet_sections(file_bytes, name)
        elif mime_type.startswith("text/"):
            try:
                text_content = file_bytes.decode("utf-8", errors="ignore")
                sections = [{"label": "Text", "text": text_content}]
            except Exception:
                sections = []
    else:
        text_raw = str(raw)
        if text_raw.strip():
            sections = [{"label": "Text", "text": text_raw}]

    chunked_sections: List[Dict] = []
    for section in sections:
        section_text = str(section.get("text") or "").strip()
        if not section_text:
            continue
        for idx, chunk_text in enumerate(translate_module.chunk_text_for_retrieval(section_text, max_chars=1400), start=1):
            chunked_sections.append(
                {
                    "doc": name,
                    "label": f"{section.get('label', 'Section')} #{idx}",
                    "text": chunk_text,
                }
            )

    return chunked_sections


def _build_chunks(attachments: List[Dict]) -> List[Dict]:
    chunks: List[Dict] = []
    for attachment in attachments or []:
        for section in _extract_attachment_sections(attachment):
            chunks.append(
                {
                    "doc": section["doc"],
                    "page": section["label"],
                    "text": translate_module.mask_pii_text(section["text"]),
                }
            )
    return chunks


def _retrieve(query: str, chunks: List[Dict], k: int = 12) -> List[Dict]:
    if not chunks:
        return []
    sparse = _bm25_scores(_tokenize(query), chunks)
    combined = _normalize(sparse)
    top_indices = sorted(range(len(chunks)), key=lambda i: combined[i], reverse=True)[: min(k, len(chunks))]
    return [chunks[i] for i in top_indices]


def _build_context(selected_chunks: List[Dict], max_words: int = 6000) -> str:
    parts: List[str] = []
    words_used = 0
    for chunk in selected_chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue
        n_words = len(text.split())
        if words_used + n_words > max_words and parts:
            break
        parts.append(f"[DOCUMENT:\"{chunk['doc']}\" | SECTION:{chunk['page']}]\n{text}")
        words_used += n_words
    return "\n\n---\n\n".join(parts)


def answer_multidoc(messages: List[Dict], attachments: List[Dict], model: Optional[str] = None, max_tokens: int = 2200) -> str:
    last_user_message = ""
    if messages:
        maybe_last = messages[-1]
        if isinstance(maybe_last, dict):
            last_user_message = str(maybe_last.get("content") or "")

    if not attachments:
        return "Please upload one or more documents in Multi-Doc Q&A mode so I can answer from document evidence."

    chunks = _build_chunks(attachments)
    if not chunks:
        return "I could not extract readable content from the uploaded files. Please upload text-based PDF, DOCX, TXT, CSV, XLSX, or clear image files."

    selected = _retrieve(last_user_message, chunks, k=14)
    context = _build_context(selected)

    system_prompt = (
        "You are a strict multi-document enterprise analyst. "
        "Answer using ONLY provided document context. "
        "When evidence is present, cite as [DOCUMENT: name | SECTION: label]. "
        "If something is not in the documents, explicitly say it is not present. "
        "Do not fabricate facts."
    )
    user_prompt = (
        f"Question:\n{last_user_message}\n\n"
        "Document Context:\n"
        f"{context}\n\n"
        "Return a precise answer with short bullets if useful, and include citations."
    )

    return translate_module.call_azure_openai_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        model=model,
        max_tokens=max_tokens,
    )
