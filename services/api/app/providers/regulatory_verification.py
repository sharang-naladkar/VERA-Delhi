"""Provider interface for VERA regulatory verification."""

from abc import abstractmethod

from app.contracts.regulatory import (
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.providers.base import BaseProvider


class RegulatoryVerificationProvider(BaseProvider):
    """Contract for providers that verify securities-market participants."""

    @property
    @abstractmethod
    def supported_source_ids(self) -> tuple[str, ...]:
        """Return the source IDs this provider can query."""
        raise NotImplementedError

    @abstractmethod
    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        """Verify a participant using an explicitly supported source.

        Implementations must not report a successful verification unless
        authoritative evidence was actually retrieved and evaluated.
        """
        raise NotImplementedError
