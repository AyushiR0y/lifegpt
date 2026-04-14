from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import os
import re
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

from backend.modules.summarization.document_parser import DocumentParser
from backend.modules.translate import translate as translate_module

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_EMB_MODEL = os.getenv("OPENAI_EMB_MODEL", "text-embedding-3-small").strip()
MULTIDOC_SESSION_TTL_SECONDS = int(os.getenv("MULTIDOC_SESSION_TTL_SECONDS", "7200"))
MULTIDOC_MAX_SESSIONS = int(os.getenv("MULTIDOC_MAX_SESSIONS", "200"))
MULTIDOC_MAX_CONTEXT_WORDS = int(os.getenv("MULTIDOC_MAX_CONTEXT_WORDS", "3200"))
MULTIDOC_EMBED_CACHE_MAX = int(os.getenv("MULTIDOC_EMBED_CACHE_MAX", "128"))

_STOP_WORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "for", "on", "at", "with",
    "this", "that", "it", "be", "as", "are", "was", "were", "by", "from", "have", "has",
    "not", "but", "what", "how", "when", "where", "all", "any", "can", "will", "do", "if",
    "its", "they", "we", "you", "i", "he", "she", "them", "there", "so", "more", "about",
    "also", "into", "been", "than", "then", "these", "those", "each", "would", "could", "should",
    "per", "which", "who", "my", "me", "us", "our", "their", "your",
}

_DOC_PARSER = DocumentParser()
_EMBED_CLIENT: Optional[httpx.AsyncClient] = None
_EMBED_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
_QUERY_EMBED_CACHE: OrderedDict[str, np.ndarray] = OrderedDict()


@dataclass
class MultidocSession:
    sid: str
    chunks: list[Dict[str, Any]] = field(default_factory=list)
    embeddings: Optional[np.ndarray] = None
    page_texts: Dict[tuple[str, int], str] = field(default_factory=dict)
    docs: list[Dict[str, Any]] = field(default_factory=list)
    history: list[Dict[str, Any]] = field(default_factory=list)
    indexed_docs: set[str] = field(default_factory=set)
    updated_at: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


class MultidocSessionStore:
    def __init__(self) -> None:
        self._store: Dict[str, MultidocSession] = {}

    def _cleanup(self) -> None:
        now = time.time()
        expired = [sid for sid, sess in self._store.items() if now - float(sess.updated_at) > MULTIDOC_SESSION_TTL_SECONDS]
        for sid in expired:
            self._store.pop(sid, None)

        if len(self._store) <= MULTIDOC_MAX_SESSIONS:
            return

        ordered = sorted(self._store.items(), key=lambda item: float(item[1].updated_at))
        overflow = len(self._store) - MULTIDOC_MAX_SESSIONS
        for sid, _ in ordered[:overflow]:
            self._store.pop(sid, None)

    def get_or_create(self, sid: str) -> MultidocSession:
        self._cleanup()
        if sid not in self._store:
            self._store[sid] = MultidocSession(sid=sid)
        return self._store[sid]


_STORE = MultidocSessionStore()


def _session_id(chat_id: Optional[str]) -> str:
    sid = str(chat_id or "").strip()
    return sid or "default"


def _tokenize(text: str) -> List[str]:
    return [token for token in re.sub(r"[^a-z0-9]", " ", (text or "").lower()).split() if len(token) > 1 and token not in _STOP_WORDS]


def _normalise(values: List[float]) -> List[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    span = (hi - lo) + 1e-9
    return [(value - lo) / span for value in values]


def _bm25_scores(query_tokens: List[str], chunks: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> List[float]:
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
            freq = term_freq.get(token, 0)
            if not freq:
                continue
            idf = np.log((n_docs - doc_freq.get(token, 0) + 0.5) / (doc_freq.get(token, 0) + 0.5) + 1)
            score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1e-9)))
        scores.append(float(score))

    return scores


async def _embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    if not OPENAI_API_KEY or not texts:
        return None

    if len(texts) == 1 and texts[0] in _QUERY_EMBED_CACHE:
        _QUERY_EMBED_CACHE.move_to_end(texts[0])
        return _QUERY_EMBED_CACHE[texts[0]]

    global _EMBED_CLIENT
    if _EMBED_CLIENT is None or _EMBED_CLIENT.is_closed:
        _EMBED_CLIENT = httpx.AsyncClient(timeout=60, limits=_EMBED_LIMITS)

    try:
        vectors: List[List[float]] = []
        for start in range(0, len(texts), 16):
            batch = texts[start : start + 16]
            resp = await _EMBED_CLIENT.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"input": batch, "model": OPENAI_EMB_MODEL},
            )
            if resp.status_code != 200:
                return None
            payload = resp.json()
            items = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
            vectors.extend(item.get("embedding", []) for item in items)

        result = np.array(vectors, dtype=np.float32)
        if len(texts) == 1:
            if len(_QUERY_EMBED_CACHE) >= MULTIDOC_EMBED_CACHE_MAX:
                _QUERY_EMBED_CACHE.popitem(last=False)
            _QUERY_EMBED_CACHE[texts[0]] = result
        return result
    except Exception:
        return None


def _decode_attachment(attachment: Dict[str, Any]) -> tuple[bytes, str]:
    name = str(attachment.get("name") or "attachment")
    content = attachment.get("content") or {}
    raw = content.get("raw") if isinstance(content, dict) else attachment.get("raw")
    is_base64 = bool(content.get("isBase64")) if isinstance(content, dict) else False

    if isinstance(raw, bytes):
        return raw, name
    if not isinstance(raw, str):
        return b"", name

    if is_base64 and raw.startswith("data:"):
        _, encoded = raw.split(",", 1)
        return base64.b64decode(encoded), name
    if is_base64:
        try:
            return base64.b64decode(raw), name
        except Exception:
            return raw.encode("utf-8", errors="ignore"), name
    return raw.encode("utf-8", errors="ignore"), name


def _doc_to_chunks(doc, filename: str) -> list[Dict[str, Any]]:
    chunks: list[Dict[str, Any]] = []
    page_texts = getattr(doc, "page_contents", {}) or {}

    for page_num, page_text in page_texts.items():
        text = translate_module.mask_pii_text(str(page_text or "").strip())
        if text:
            chunks.append({"doc": filename, "page": int(page_num), "text": text})

    if not chunks and getattr(doc, "text", ""):
        fallback_text = translate_module.mask_pii_text(str(doc.text).strip())
        if fallback_text:
            chunks.append({"doc": filename, "page": 1, "text": fallback_text})

    return chunks


def _chunk_key(filename: str, payload: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(filename.encode("utf-8", errors="ignore"))
    digest.update(payload)
    return digest.hexdigest()


async def _ensure_embeddings(sess: MultidocSession) -> None:
    if not OPENAI_API_KEY or not sess.chunks:
        return

    texts = [chunk["text"] for chunk in sess.chunks]
    vecs = await _embed_texts(texts)
    if vecs is not None:
        sess.embeddings = vecs


async def _ingest_attachments(sess: MultidocSession, attachments: List[Dict[str, Any]]) -> None:
    new_chunks: list[Dict[str, Any]] = []

    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            continue

        filename = str(attachment.get("name") or "attachment")
        payload, _ = _decode_attachment(attachment)
        if not payload:
            continue

        doc_key = _chunk_key(filename, payload)
        if doc_key in sess.indexed_docs:
            continue

        try:
            parsed = _DOC_PARSER.parse(payload, filename)
        except Exception:
            # Fallback for plain-text attachments if parsing fails.
            text = payload.decode("utf-8", errors="ignore").strip()
            parsed = type("ParsedDoc", (), {
                "page_contents": {1: text},
                "text": text,
                "total_pages": 1,
                "file_type": filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt",
                "metadata": {"filename": filename},
            })()

        chunks = _doc_to_chunks(parsed, filename)
        if not chunks:
            continue

        sess.indexed_docs.add(doc_key)
        sess.docs.append({
            "name": filename,
            "ext": getattr(parsed, "file_type", ""),
            "pages": getattr(parsed, "total_pages", len(chunks)),
            "chunks": len(chunks),
        })

        for chunk in chunks:
            sess.page_texts[(chunk["doc"], chunk["page"])] = chunk["text"]
            new_chunks.append(chunk)

    if new_chunks:
        sess.chunks.extend(new_chunks)
        await _ensure_embeddings(sess)


def _complex_query(query: str) -> bool:
    q = (query or "").lower()
    signals = [
        "and also", "as well as", "additionally", "furthermore",
        "compare", "difference between", " vs ", "versus",
        "list all", "what are all", "every", "complete list",
        "explain each", "describe all",
    ]
    return query.count("?") > 1 or any(word in q for word in signals) or len(query.split()) > 25


def _decompose_query(query: str) -> List[str]:
    parts = re.split(r"\?\s+(?=[A-Z])", query)
    parts = [part.strip().rstrip("?") + "?" for part in parts if len(part.strip()) > 8]
    if len(parts) <= 1:
        parts = re.split(r"\s+(?:and also|as well as|additionally)\s+", query, flags=re.I)
        parts = [part.strip() for part in parts if len(part.strip()) > 8]
    return parts if len(parts) > 1 else [query]


async def _retrieve(query: str, sess: MultidocSession, k: int = 14) -> List[Dict[str, Any]]:
    if not sess.chunks:
        return []

    N = len(sess.chunks)
    dense = [0.0] * N
    q_vec: Optional[np.ndarray] = None

    if sess.embeddings is not None and OPENAI_API_KEY:
        qv = await _embed_texts([query])
        if qv is not None and len(qv):
            q_vec = qv[0]
            qn = q_vec / (np.linalg.norm(q_vec) + 1e-9)
            M = sess.embeddings
            Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
            dense = ((Mn @ qn + 1.0) / 2.0).tolist()

    sparse = _bm25_scores(_tokenize(query), sess.chunks)
    combined = [0.55 * d + 0.45 * s for d, s in zip(_normalise(dense), _normalise(sparse))]
    top = sorted(range(N), key=lambda idx: combined[idx], reverse=True)[: min(40, N)]

    if q_vec is not None and sess.embeddings is not None:
        cv = sess.embeddings[top]
        qn = q_vec / (np.linalg.norm(q_vec) + 1e-9)
        cn = cv / (np.linalg.norm(cv, axis=1, keepdims=True) + 1e-9)
        rel = (cn @ qn).flatten()
        selected: list[int] = []
        remaining = list(range(len(top)))
        lam = 0.6
        while len(selected) < k and remaining:
            if not selected:
                best = max(remaining, key=lambda item: rel[item])
            else:
                sv = cn[np.array(selected)]
                best = max(remaining, key=lambda item: lam * rel[item] - (1 - lam) * float((sv @ cn[item]).max()))
            selected.append(best)
            remaining.remove(best)
        final = [top[i] for i in selected]
    else:
        final = top[:k]

    return [sess.chunks[i] for i in final]


def _build_context(selected_chunks: List[Dict[str, Any]], max_words: int = MULTIDOC_MAX_CONTEXT_WORDS) -> tuple[str, List[tuple[str, int]]]:
    parts: List[str] = []
    included: List[tuple[str, int]] = []
    words_used = 0

    for chunk in selected_chunks:
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        n_words = len(text.split())
        if words_used + n_words > max_words and parts:
            break
        doc = str(chunk.get("doc") or "")
        page = int(chunk.get("page") or 0)
        parts.append(f'[DOCUMENT:"{doc}" | PAGE:{page}]\n{text}')
        included.append((doc, page))
        words_used += n_words

    return "\n\n---\n\n".join(parts), included


def _system_prompt() -> str:
    return (
        "You are a strict multi-document enterprise QA assistant. "
        "Answer using ONLY the provided document context. "
        "Cite facts inline as [DOCUMENT:\"name\" | PAGE:n]. "
        "If something is not present in the documents, say so explicitly. "
        "Do not invent facts or use external knowledge."
    )


def _build_user_prompt(query: str, context: str, multi_note: str = "") -> str:
    return (
        f"Question:\n{query}\n\n"
        f"{multi_note}\n"
        "Document Context:\n"
        f"{context}\n\n"
        "Return a precise answer with short bullets only if they improve clarity."
    )


async def answer_multidoc(
    messages: List[Dict[str, Any]],
    attachments: List[Dict[str, Any]],
    chat_id: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1200,
) -> str:
    sid = _session_id(chat_id)
    sess = _STORE.get_or_create(sid)

    async with sess.lock:
        sess.updated_at = time.time()
        if attachments:
            await _ingest_attachments(sess, attachments)

        query_text = ""
        if messages:
            maybe_last = messages[-1]
            if isinstance(maybe_last, dict):
                query_text = str(maybe_last.get("content") or "")

        if not query_text.strip():
            return "Please ask a question after uploading one or more documents."

        if not sess.chunks:
            return "Please upload one or more documents in Multi-Doc mode so I can answer from document evidence."

        query = query_text.strip()
        selected = await _retrieve(query, sess, k=14)
        if not selected:
            return "I could not find enough relevant document context to answer this question."

        context, _included = _build_context(selected)
        if not context.strip():
            return "I could not build usable context from the uploaded documents. Please upload clearer files."

        user_query = query
        multi_note = ""
        if _complex_query(query):
            sub_queries = _decompose_query(query)
            if len(sub_queries) > 1:
                multi_note = "This question has multiple parts. Address each part clearly and separately:\n" + "\n".join(
                    f"- Part {idx + 1}: {part}" for idx, part in enumerate(sub_queries)
                )

        system_prompt = _system_prompt()
        user_prompt = _build_user_prompt(user_query, context, multi_note)

        response = translate_module.call_azure_openai_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            model=model,
            max_tokens=max_tokens,
        )

        sess.history.extend([
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": response},
        ])
        sess.updated_at = time.time()
        return response
