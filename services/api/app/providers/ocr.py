"""OCR Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class OCRProvider(BaseProvider):
    """Interface for OCR document/screenshot text extraction."""

    @abstractmethod
    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Extract text and bounding metadata from an image."""
        pass


class UnavailableOCRProvider(OCRProvider):
    """Fail-safe placeholder for OCR provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_ocr"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "OCR engine is not configured in Phase 01.",
        }

    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "text": "",
            "blocks": [],
            "error": "OCR provider is unavailable.",
        }
