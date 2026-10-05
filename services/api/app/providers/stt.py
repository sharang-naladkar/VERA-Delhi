"""Speech-to-Text (STT) Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class STTProvider(BaseProvider):
    """Interface for Speech-to-Text audio transcription."""

    @abstractmethod
    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Transcribe speech to text with timestamps and speaker segments."""
        pass


class UnavailableSTTProvider(STTProvider):
    """Fail-safe placeholder for STT provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_stt"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "STT engine is not configured in Phase 01.",
        }

    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "transcript": "",
            "segments": [],
            "error": "STT provider is unavailable.",
        }
