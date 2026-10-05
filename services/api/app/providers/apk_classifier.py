"""APK Classifier Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class APKClassifier(BaseProvider):
    """Interface for Android APK static and dynamic malware/fraud analysis."""

    @abstractmethod
    async def analyze_apk(
        self,
        investigation_id: UUID,
        apk_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Analyze APK package for permissions, fake trading indicators, or trojan behavior."""
        pass


class UnavailableAPKClassifier(APKClassifier):
    """Fail-safe placeholder for APK classifier."""

    @property
    def provider_name(self) -> str:
        return "unavailable_apk_classifier"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "APK classifier engine is not configured in Phase 01.",
        }

    async def analyze_apk(
        self,
        investigation_id: UUID,
        apk_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "package_name": None,
            "risk_score": None,
            "error": "APK classifier is unavailable.",
        }
