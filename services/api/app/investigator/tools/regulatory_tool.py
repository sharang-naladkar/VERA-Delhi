"""Regulatory Knowledge Investigation Tool."""

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.regulatory import RegulatorySearchResponse
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.regulatory import RegulatoryKnowledgeProvider


class RegulatoryKnowledgeTool(InvestigationTool):
    """Retrieves authoritative regulatory knowledge with provenance."""

    def __init__(
        self,
        regulatory_provider: RegulatoryKnowledgeProvider | None = None,
    ) -> None:
        self.regulatory_provider = regulatory_provider

    @property
    def name(self) -> str:
        return "regulatory_knowledge"

    @property
    def description(self) -> str:
        return (
            "Retrieves authoritative regulatory knowledge and "
            "returns source-backed regulatory evidence."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()

        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()

        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        query = state.get("regulatory_query") or state.get("query")

        if not isinstance(query, str) or not query.strip():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[],
                output_data={
                    "query": query,
                    "results": [],
                    "message": "No regulatory query was provided.",
                },
                duration_ms=duration_ms,
            )

        query = query.strip()

        top_k = state.get("top_k", 5)
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            top_k = 5
        top_k = max(1, min(top_k, 20))

        if self.regulatory_provider is None:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.REGULATORY_CHECK,
                category="regulatory_knowledge",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="Regulatory knowledge provider is not configured.",
                source_type="provider",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={
                    "provider_available": False,
                    "query": query,
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={
                    "query": query,
                    "results": [],
                    "message": "Regulatory knowledge provider is unavailable.",
                },
                duration_ms=duration_ms,
            )

        try:
            response: RegulatorySearchResponse = (
                await self.regulatory_provider.search(
                    query,
                    top_k=top_k,
                )
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.REGULATORY_CHECK,
                category="regulatory_knowledge",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=(
                    "Regulatory knowledge retrieval failed "
                    "due to a provider error."
                ),
                source_type="provider",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.FAILED,
                metadata={
                    "query": query,
                    "error": str(exc),
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[evidence],
                output_data={
                    "query": query,
                    "results": [],
                },
                error_message=str(exc),
                duration_ms=duration_ms,
            )

        status_map = {
            AnalysisStatus.SUCCESS.value: AnalysisStatus.SUCCESS,
            AnalysisStatus.PARTIAL.value: AnalysisStatus.PARTIAL,
            AnalysisStatus.FAILED.value: AnalysisStatus.FAILED,
            AnalysisStatus.UNAVAILABLE.value: AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.INSUFFICIENT_EVIDENCE.value: (
                AnalysisStatus.INSUFFICIENT_EVIDENCE
            ),
        }

        response_status = str(response.status).upper()
        tool_status = status_map.get(
            response_status,
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
        )

        if not response.source_available:
            tool_status = AnalysisStatus.UNAVAILABLE

        result_payload = response.model_dump(mode="json")

        evidence_items: list[EvidenceContract] = []

        if response.results:
            for result in response.results:
                document = result.document
                chunk = result.chunk

                evidence_items.append(
                    EvidenceContract(
                        investigation_id=investigation_id,
                        input_id=input_id,
                        type=EvidenceType.REGULATORY_CHECK,
                        category="regulatory_knowledge",
                        severity=SeverityLevel.INFORMATIONAL,
                        confidence=min(max(result.score, 0.0), 1.0),
                        description=chunk.text,
                        source_type="regulatory_source",
                        source_name=document.source_name,
                        source_version=self.version,
                        status=tool_status,
                        raw_payload=result.model_dump(mode="json"),
                        metadata={
                            "query": query,
                            "document_id": str(document.id),
                            "document_title": document.title,
                            "source_url": document.source_url,
                            "document_reference": document.document_reference,
                            "section": chunk.section,
                            "page": chunk.page,
                            "retrieved_at": document.retrieved_at.isoformat(),
                        },
                    )
                )
        else:
            evidence_items.append(
                EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.REGULATORY_CHECK,
                    category="regulatory_knowledge",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description=(
                        "No regulatory source-backed results were retrieved."
                    ),
                    source_type="regulatory_provider",
                    source_name=self.regulatory_provider.provider_name,
                    source_version=self.version,
                    status=tool_status,
                    raw_payload=result_payload,
                    metadata={
                        "query": query,
                        "source_available": response.source_available,
                    },
                )
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=tool_status,
            evidence=evidence_items,
            output_data=result_payload,
            duration_ms=duration_ms,
        )