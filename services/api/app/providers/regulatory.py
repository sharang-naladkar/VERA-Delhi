"""Regulatory knowledge retrieval provider interfaces."""

from abc import abstractmethod
from typing import Any

from app.contracts.regulatory import RegulatorySearchResponse
from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class RegulatoryKnowledgeProvider(BaseProvider):
    """Interface for authoritative regulatory knowledge retrieval."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> RegulatorySearchResponse:
        """Retrieve regulatory knowledge with source provenance."""
        raise NotImplementedError


class UnavailableRegulatoryKnowledgeProvider(RegulatoryKnowledgeProvider):
    """Fail-safe provider when regulatory knowledge is unavailable."""

    @property
    def provider_name(self) -> str:
        return "unavailable_regulatory_knowledge"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "Regulatory knowledge source is not configured.",
        }

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> RegulatorySearchResponse:
        return RegulatorySearchResponse(
            query=query,
            results=[],
            source_available=False,
            status=AnalysisStatus.UNAVAILABLE.value,
            metadata={
                "provider": self.provider_name,
                "top_k": top_k,
            },
        )


class MockRegulatoryKnowledgeProvider(RegulatoryKnowledgeProvider):
    """Deterministic regulatory knowledge provider for tests only."""

    def __init__(
        self,
        response: RegulatorySearchResponse | None = None,
    ) -> None:
        self._response = response

    @property
    def provider_name(self) -> str:
        return "mock_regulatory_knowledge"

    @property
    def is_available(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "Deterministic regulatory knowledge provider.",
        }

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> RegulatorySearchResponse:
        if self._response is not None:
            return self._response

        return RegulatorySearchResponse(
            query=query,
            results=[],
            source_available=True,
            status=AnalysisStatus.SUCCESS.value,
            metadata={
                "provider": self.provider_name,
                "test_fixture": True,
                "top_k": top_k,
            },
        )