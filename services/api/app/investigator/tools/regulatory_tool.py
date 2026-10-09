"""Investigator tool for structured regulatory verification."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.contracts.evidence import EvidenceContract
from app.contracts.regulatory import RegulatoryVerificationRequest
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.regulatory_verification_service import (
    RegulatoryVerificationService,
)


class RegulatoryVerificationTool(InvestigationTool):
    """Verify explicitly supplied regulatory claims through the safe service."""

    name = "regulatory_verification"
    description = (
        "Checks an explicitly supplied structured regulatory verification "
        "request and returns source-attributed results and limitations. "
        "It does not independently determine fraud or legitimacy."
    )
    version = "1.0.0"

    def __init__(
        self,
        service: RegulatoryVerificationService | None = None,
    ) -> None:
        self.service = service or RegulatoryVerificationService()

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Execute verification without inferring missing identifiers."""

        investigation_id = state.get("investigation_id")
        if not investigation_id:
            return self._result(
                AnalysisStatus.FAILED,
                error_message="Investigation ID is missing.",
            )

        try:
            parsed_investigation_id = UUID(str(investigation_id))
        except (ValueError, TypeError, AttributeError):
            return self._result(
                AnalysisStatus.FAILED,
                error_message="Investigation ID is invalid.",
            )

        raw_request = state.get("regulatory_verification_request")
        if raw_request is None:
            return self._result(
                AnalysisStatus.INSUFFICIENT_EVIDENCE,
                output_data={
                    "verification_status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                    "matched": None,
                    "explanation": (
                        "No structured regulatory verification request was supplied."
                    ),
                    "limitations": [
                        "No regulatory lookup was attempted.",
                        "No conclusion about registration, fraud, or legitimacy can be drawn.",
                    ],
                },
            )

        try:
            request = RegulatoryVerificationRequest.model_validate(raw_request)
        except (ValidationError, TypeError, ValueError) as exc:
            return self._result(
                AnalysisStatus.INSUFFICIENT_EVIDENCE,
                output_data={
                    "verification_status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                    "matched": None,
                    "explanation": "The regulatory verification request is invalid.",
                    "limitations": [
                        "No regulatory lookup was attempted.",
                        "Supply a valid participant type and at least one subject identifier.",
                    ],
                },
                error_message=f"Invalid regulatory verification request: {exc}",
            )

        try:
            verification = await self.service.verify(request)
        except Exception:
            # Defensive boundary: a service implementation must not crash the
            # investigation or turn an exception into a match determination.
            return self._result(
                AnalysisStatus.FAILED,
                output_data={
                    "verification_status": AnalysisStatus.FAILED.value,
                    "matched": None,
                    "explanation": (
                        "An unexpected error prevented regulatory verification."
                    ),
                    "limitations": [
                        "No verified match outcome is available.",
                        "The failure does not establish fraud or legitimacy.",
                    ],
                },
                error_message="Regulatory verification service execution failed.",
            )

        evidence: list[EvidenceContract] = []
        for item in verification.evidence:
            evidence.append(
                EvidenceContract(
                    investigation_id=parsed_investigation_id,
                    type=EvidenceType.FORENSIC_ARTIFACT,
                    category="regulatory_verification",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description=item.description,
                    source_type="official_source",
                    source_name=item.source_id,
                    source_version=self.version,
                    status=verification.status,
                    raw_payload=item.model_dump(mode="json"),
                    metadata={
                        "source_id": item.source_id,
                        "source_url": item.source_url,
                        "retrieved_at": (
                            item.retrieved_at.isoformat()
                            if item.retrieved_at
                            else None
                        ),
                        "confidence_note": (
                            "No calibrated evidence-confidence score was supplied."
                        ),
                    },
                )
            )

        output_data = verification.model_dump(mode="json")
        output_data["verification_status"] = verification.status.value
        output_data["matched"] = verification.matched
        output_data["limitations"] = list(verification.limitations)

        return self._result(
            verification.status,
            evidence=evidence,
            output_data=output_data,
        )

    def _result(
        self,
        status: AnalysisStatus,
        *,
        evidence: list[EvidenceContract] | None = None,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=status,
            evidence=evidence or [],
            output_data=output_data or {},
            error_message=error_message,
        )
