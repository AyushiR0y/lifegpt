"""Compatibility wrapper for shared PII service."""

from typing import Dict

from backend.core.pii_service import pii_service


class PIIMasker:
    """
    Detect and mask PII before sending text to an LLM,
    then restore the original values in the generated output.
    """

    def __init__(self) -> None:
        self._map: Dict[str, str] = {}
        self.pii_summary: Dict[str, int] = {}

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

        result = pii_service.mask_text(text)
        self._map = result.placeholders
        self.pii_summary = result.pii_summary
        return result.masked_text

    def unmask_text(self, text: str) -> str:
        """Restore all previously masked placeholders to their original values."""
        return pii_service.unmask_text(text, self._map)

    def get_pii_summary(self) -> Dict[str, int]:
        """Return entity-type → count of detected PII items."""
        return dict(self.pii_summary)

