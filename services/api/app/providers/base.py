"""Base classes and types for VERA Model & Service Providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Abstract base class for all pluggable analysis and intelligence providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider implementation."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Checks if provider backend/service is currently reachable and initialized."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Performs a self-check on the provider's dependencies."""
        pass
