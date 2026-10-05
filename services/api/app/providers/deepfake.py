"""Deepfake & Computer Vision Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class DeepfakeProvider(BaseProvider):
    """Interface for Deepfake (MesoNet / FaceForensics / CV) detection."""

    @abstractmethod
    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,  # image / video
    ) -> dict[str, Any]:
        """Analyze image or video stream for synthetic manipulation or deepfake signs."""
        pass


class UnavailableDeepfakeProvider(DeepfakeProvider):
    """Fail-safe placeholder for Deepfake provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_deepfake"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "Deepfake analysis engine is not configured in Phase 01.",
        }

    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "manipulation_score": None,
            "error": "Deepfake analysis engine is unavailable.",
        }
