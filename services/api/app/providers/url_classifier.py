"""URL Classifier Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class URLClassifier(BaseProvider):
    """Interface for URL / Domain / Phishing classification and WHOIS intelligence."""

    @abstractmethod
    async def classify_url(
        self,
        investigation_id: UUID,
        url: str,
    ) -> dict[str, Any]:
        """Classify a given URL for phishing, impersonation, or malicious characteristics."""
        pass


class UnavailableURLClassifier(URLClassifier):
    """Fail-safe placeholder for URL classifier."""

    @property
    def provider_name(self) -> str:
        return "unavailable_url_classifier"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "URL classifier engine is not configured in Phase 01.",
        }

    async def classify_url(
        self,
        investigation_id: UUID,
        url: str,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "url": url,
            "risk_score": None,
            "error": "URL classifier is unavailable.",
        }
