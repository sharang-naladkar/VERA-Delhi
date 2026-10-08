"""SEBI Regulatory Intelligence Investigation Tool."""

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.sebi import VerificationResult, VerificationStatus
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.sebi import SEBIProvider


class SEBIInvestigationTool(InvestigationTool):
    """Verifies regulatory entities using the configured SEBI provider."""

    def __init__(self, sebi_provider: SEBIProvider | None = None) -> None:
        self.sebi_provider = sebi_provider

    @property
    def name(self) -> str:
        return "sebi_investigation"

    @property
    def description(self) -> str:
        return "Verifies regulatory entities and returns SEBI regulatory evidence."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()

        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()

        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        entity_name = state.get("entity_name")
        registration_number = state.get("registration_number")
        entity_type = state.get("entity_type")
        claimed_organization = state.get("claimed_organization")

        if not any(
            (
                entity_name,
                registration_number,
                entity_type,
                claimed_organization,
            )
        ):
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[],
                output_data={
                    "verification": None,
                    "message": "No regulatory entity information was provided.",
                },
                duration_ms=duration_ms,
            )

        if self.sebi_provider is None:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.REGULATORY_CHECK,
                category="sebi_verification",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="SEBI regulatory provider is not configured.",
                source_type="provider",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={
                    "provider_available": False,
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={
                    "verification": None,
                    "message": "SEBI regulatory provider is unavailable.",
                },
                duration_ms=duration_ms,
            )

        try:
            verification: VerificationResult = (
                await self.sebi_provider.verify_entity(
                    entity_name=entity_name,
                    registration_number=registration_number,
                    entity_type=entity_type,
                    claimed_organization=claimed_organization,
                )
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.REGULATORY_CHECK,
                category="sebi_verification",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="SEBI verification failed due to a provider error.",
                source_type="provider",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.FAILED,
                metadata={
                    "error": str(exc),
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[evidence],
                error_message=str(exc),
                duration_ms=duration_ms,
            )

        status_mapping = {
            VerificationStatus.VERIFIED: AnalysisStatus.SUCCESS,
            VerificationStatus.NOT_VERIFIED: AnalysisStatus.NOT_VERIFIED,
            VerificationStatus.PARTIAL: AnalysisStatus.PARTIAL,
            VerificationStatus.FAILED: AnalysisStatus.FAILED,
            VerificationStatus.UNAVAILABLE: AnalysisStatus.UNAVAILABLE,
            VerificationStatus.INSUFFICIENT_EVIDENCE: AnalysisStatus.INSUFFICIENT_EVIDENCE,
        }

        tool_status = status_mapping[verification.status]

        confidence = (
            1.0
            if verification.status == VerificationStatus.VERIFIED
            else 0.0
        )

        evidence = EvidenceContract(
            investigation_id=investigation_id,
            input_id=input_id,
            type=EvidenceType.REGULATORY_CHECK,
            category="sebi_entity_verification",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=confidence,
            description=(
                verification.details
                or f"SEBI verification result: {verification.status.value}."
            ),
            source_type="regulatory_provider",
            source_name=self.sebi_provider.provider_name,
            source_version=self.version,
            status=tool_status,
            raw_payload=verification.model_dump(mode="json"),
            metadata={
                "verification_status": verification.status.value,
                "entity_name": verification.entity_name,
                "registration_number": verification.registration_number,
                "entity_type": verification.entity_type,
                "claimed_organization": verification.claimed_organization,
            },
        )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=tool_status,
            evidence=[evidence],
            output_data={
                "verification": verification.model_dump(mode="json"),
            },
            duration_ms=duration_ms,
        )