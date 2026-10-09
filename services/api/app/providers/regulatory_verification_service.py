"""Safe orchestration for regulatory verification."""

import logging
from typing import Any

from app.contracts.regulatory import (
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_provider import RegistryRegulatoryProvider
from app.providers.regulatory_result_validator import RegulatoryResultValidator

logger = logging.getLogger(__name__)


class RegulatoryVerificationService:
    """Validate requests and safely contain provider failures."""

    def __init__(
        self,
        provider: RegistryRegulatoryProvider | None = None,
        validator: RegulatoryResultValidator | None = None,
    ) -> None:
        self.provider = provider or RegistryRegulatoryProvider()
        self.validator = validator or RegulatoryResultValidator(
            self.provider._registry
        )

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        """Return a structured result even if verification fails."""
        try:
            request_errors = self.validator.validate_request(request)
            if request_errors:
                return self._failure_result(
                    request,
                    AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    "Verification request did not pass validation.",
                    request_errors,
                )

            result = await self.provider.verify(request)
            result_errors = self.validator.validate_result(request, result)

            if result_errors:
                logger.warning(
                    "Regulatory provider returned an invalid result: %s",
                    result_errors,
                )
                return self._failure_result(
                    request,
                    AnalysisStatus.FAILED,
                    "Provider returned a result that failed validation.",
                    result_errors,
                )

            return result

        except Exception:
            logger.exception("Unexpected regulatory verification failure")
            return self._failure_result(
                request,
                AnalysisStatus.FAILED,
                "An unexpected error prevented regulatory verification.",
                [
                    "No verified match outcome is available.",
                    "Retry or investigate the provider failure.",
                ],
            )

    @staticmethod
    def _failure_result(
        request: RegulatoryVerificationRequest,
        status: AnalysisStatus,
        explanation: str,
        limitations: list[str],
    ) -> RegulatoryVerificationResult:
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=status,
            subject_name=request.subject_name,
            registration_number=request.registration_number,
            matched=None,
            explanation=explanation,
            limitations=limitations,
        )
