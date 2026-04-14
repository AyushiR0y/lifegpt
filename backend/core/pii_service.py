import re
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PIIMaskResult:
    masked_text: str
    placeholders: Dict[str, str] = field(default_factory=dict)
    pii_summary: Dict[str, int] = field(default_factory=dict)


class UniversalPIIService:
    """Shared PII masking service with Presidio and regex fallback."""

    _TYPE_MAP: Dict[str, str] = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "PHONE",
        "PHONE_IN": "PHONE",
        "IN_PAN": "PAN",
        "IN_AADHAAR": "AADHAAR",
        "CREDIT_CARD": "CREDIT_CARD",
        "PERSON": "PERSON",
        "IFSC": "IFSC",
    }

    _REGEX_PATTERNS: Dict[str, str] = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE": r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",
        "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "AADHAAR": r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    def __init__(self) -> None:
        self._analyzer = None
        self._presidio_attempted = False
        self._presidio_enabled = self._should_enable_presidio()
        self._compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in self._REGEX_PATTERNS.items()
        }

    @staticmethod
    def _should_enable_presidio() -> bool:
        override = os.getenv("PII_USE_PRESIDIO")
        if override is not None:
            return override.strip().lower() in {"1", "true", "yes", "on"}

        hosted = bool(os.getenv("PORT")) or os.getenv("RENDER", "").strip().lower() in {"1", "true", "yes", "on"}
        return not hosted

    def _init_presidio(self) -> None:
        """Try to initialize Presidio; fail open to regex-only mode."""
        if self._presidio_attempted or not self._presidio_enabled:
            return

        self._presidio_attempted = True
        try:
            from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

            engine = AnalyzerEngine()
            engine.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="IN_PAN",
                    patterns=[Pattern("pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.9)],
                    name="PAN",
                )
            )
            engine.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="IN_AADHAAR",
                    patterns=[Pattern("aadhaar", r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", 0.85)],
                    name="Aadhaar",
                )
            )
            engine.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="IFSC",
                    patterns=[Pattern("ifsc", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0.85)],
                    name="IFSC",
                )
            )
            self._analyzer = engine
        except Exception:
            self._analyzer = None

    @staticmethod
    def _overlaps(start: int, end: int, spans: List[Dict[str, Any]]) -> bool:
        return any(start < span["end"] and end > span["start"] for span in spans)

    def _placeholder(self, entity_type: str, counter: Dict[str, int]) -> str:
        norm = self._TYPE_MAP.get(entity_type, entity_type)
        counter[norm] = counter.get(norm, 0) + 1
        return f"[{norm}_{counter[norm]}]"

    def mask_text(self, text: str) -> PIIMaskResult:
        if not text:
            return PIIMaskResult(masked_text=text or "")

        self._init_presidio()

        spans: List[Dict[str, Any]] = []
        placeholders: Dict[str, str] = {}
        pii_summary: Dict[str, int] = {}
        counter: Dict[str, int] = {}

        if self._analyzer is not None:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language="en",
                    entities=[
                        "PERSON",
                        "EMAIL_ADDRESS",
                        "PHONE_NUMBER",
                        "CREDIT_CARD",
                        "IN_PAN",
                        "IN_AADHAAR",
                        "IFSC",
                    ],
                )
                for result in results:
                    start = int(result.start)
                    end = int(result.end)
                    if self._overlaps(start, end, spans):
                        continue
                    placeholder = self._placeholder(result.entity_type, counter)
                    spans.append(
                        {
                            "start": start,
                            "end": end,
                            "placeholder": placeholder,
                            "entity_type": result.entity_type,
                            "text": text[start:end],
                        }
                    )
            except Exception:
                pass

        for label, pattern in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                if self._overlaps(start, end, spans):
                    continue
                placeholder = self._placeholder(label, counter)
                spans.append(
                    {
                        "start": start,
                        "end": end,
                        "placeholder": placeholder,
                        "entity_type": label,
                        "text": match.group(),
                    }
                )

        spans.sort(key=lambda span: span["start"], reverse=True)
        masked = text
        for span in spans:
            masked = masked[: span["start"]] + span["placeholder"] + masked[span["end"] :]
            placeholders[span["placeholder"]] = span["text"]
            norm = self._TYPE_MAP.get(span["entity_type"], span["entity_type"])
            pii_summary[norm] = pii_summary.get(norm, 0) + 1

        return PIIMaskResult(masked_text=masked, placeholders=placeholders, pii_summary=pii_summary)

    @staticmethod
    def unmask_text(text: str, placeholders: Optional[Dict[str, str]] = None) -> str:
        if not text or not placeholders:
            return text

        restored = text
        for placeholder, original in placeholders.items():
            restored = restored.replace(placeholder, original)
        return restored

    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sanitized_messages: List[Dict[str, Any]] = []
        for message in messages or []:
            sanitized = dict(message)
            content = sanitized.get("content")
            if isinstance(content, str):
                sanitized["content"] = self.mask_text(content).masked_text
            elif isinstance(content, list):
                parts: List[Any] = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        updated = dict(part)
                        updated["text"] = self.mask_text(updated["text"]).masked_text
                        parts.append(updated)
                    else:
                        parts.append(part)
                sanitized["content"] = parts
            sanitized_messages.append(sanitized)
        return sanitized_messages


pii_service = UniversalPIIService()