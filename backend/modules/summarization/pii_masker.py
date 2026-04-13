"""
pii_masker.py
PII Detection and Masking using Microsoft Presidio + custom regex patterns.
Supports: Names, Emails, Phone, PAN, Aadhaar, Credit Cards.
"""

import re
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class PIIEntity:
    """A single detected PII span."""
    entity_type: str
    text: str
    start: int
    end: int
    placeholder: str


class PIIMasker:
    """
    Detect and mask PII before sending text to an LLM,
    then restore the original values in the generated output.
    """

    # Map Presidio entity names → short placeholder tokens
    _TYPE_MAP: Dict[str, str] = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER":  "PHONE",
        "PHONE_IN":      "PHONE",
        "IN_PAN":        "PAN",
        "IN_AADHAAR":    "AADHAAR",
        "CREDIT_CARD":   "CREDIT_CARD",
        "PERSON":        "PERSON",
    }

    # Fallback regex patterns (used when Presidio is unavailable)
    _REGEX_PATTERNS: Dict[str, str] = {
        "EMAIL":       r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE":       r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",
        "PAN":         r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "AADHAAR":     r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "IFSC":        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    }

    def __init__(self) -> None:
        self._analyzer = None
        self._counter: Dict[str, int] = {}
        self._map: Dict[str, str] = {}          # placeholder → original
        self.pii_summary: Dict[str, int] = {}

        self._init_presidio()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_presidio(self) -> None:
        """Try to load Presidio; silently fall back to regex if unavailable."""
        try:
            from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

            engine = AnalyzerEngine()

            # Indian PAN
            engine.registry.add_recognizer(PatternRecognizer(
                supported_entity="IN_PAN",
                patterns=[Pattern("pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.9)],
                name="PAN",
            ))

            # Indian Aadhaar
            engine.registry.add_recognizer(PatternRecognizer(
                supported_entity="IN_AADHAAR",
                patterns=[Pattern("aadhaar", r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", 0.85)],
                name="Aadhaar",
            ))

            self._analyzer = engine
        except Exception:
            self._analyzer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mask_text(self, text: str) -> str:
        """
        Replace all PII in *text* with unique placeholders.
        Stores the reverse mapping for :meth:`unmask_text`.

        Returns the masked string.
        """
        if not text:
            return text

        # Reset state for this call
        self._counter = {}
        self._map = {}
        self.pii_summary = {}

        entities: List[PIIEntity] = []

        # --- Presidio pass ---
        if self._analyzer:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language="en",
                    entities=[
                        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                        "CREDIT_CARD", "IN_PAN", "IN_AADHAAR",
                    ],
                )
                for r in results:
                    ph = self._make_placeholder(r.entity_type)
                    entities.append(PIIEntity(
                        entity_type=r.entity_type,
                        text=text[r.start:r.end],
                        start=r.start,
                        end=r.end,
                        placeholder=ph,
                    ))
            except Exception:
                pass

        # --- Regex pass (fill gaps not covered by Presidio) ---
        for label, pattern in self._REGEX_PATTERNS.items():
            for m in re.finditer(pattern, text, re.IGNORECASE):
                # Skip if already covered
                if any(m.start() < e.end and m.end() > e.start for e in entities):
                    continue
                ph = self._make_placeholder(label)
                entities.append(PIIEntity(
                    entity_type=label,
                    text=m.group(),
                    start=m.start(),
                    end=m.end(),
                    placeholder=ph,
                ))

        # Replace from right to left so offsets stay valid
        entities.sort(key=lambda e: e.start, reverse=True)
        masked = text
        for ent in entities:
            masked = masked[: ent.start] + ent.placeholder + masked[ent.end :]
            self._map[ent.placeholder] = ent.text
            norm = self._TYPE_MAP.get(ent.entity_type, ent.entity_type)
            self.pii_summary[norm] = self.pii_summary.get(norm, 0) + 1

        return masked

    def unmask_text(self, text: str) -> str:
        """Restore all previously masked placeholders to their original values."""
        if not text or not self._map:
            return text
        for ph, original in self._map.items():
            text = text.replace(ph, original)
        return text

    def get_pii_summary(self) -> Dict[str, int]:
        """Return entity-type → count of detected PII items."""
        return dict(self.pii_summary)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_placeholder(self, entity_type: str) -> str:
        norm = self._TYPE_MAP.get(entity_type, entity_type)
        self._counter[norm] = self._counter.get(norm, 0) + 1
        return f"[{norm}_{self._counter[norm]}]"
