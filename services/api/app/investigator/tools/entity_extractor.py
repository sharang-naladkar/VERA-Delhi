"""Entity Extraction Investigation Tool."""

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.errors import LLMGenerationError, ProviderUnavailableError
from app.investigator.schemas import EntityExtraction
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.prompts.loader import format_prompt
from app.providers.llm import LLMProvider


class EntityExtractorTool(InvestigationTool):
    """Extracts financial entities, communicative channels, and registration IDs via LLM."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    @property
    def name(self) -> str:
        return "entity_extractor"

    @property
    def description(self) -> str:
        return "Identifies persons, organizations, Telegram/WhatsApp channels, UPI handles, and registration numbers."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None
        text = state.get("normalized_input") or state.get("raw_input_text", "")

        if not text.strip():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[],
                output_data={"entities": [], "summary": "Empty input text."},
                duration_ms=duration_ms,
            )

        prompt, prompt_version = format_prompt("investigator", "entity_extraction_v1", input_text=text)

        try:
            extraction: EntityExtraction = await self.llm_provider.generate_structured(
                schema=EntityExtraction,
                prompt=prompt,
                temperature=0.0,
            )
        except ProviderUnavailableError as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.ENTITY_DETECTION,
                category="entity_extraction",
                severity=SeverityLevel.LOW,
                confidence=0.0,
                description="Entity extraction unavailable: LLM backend is offline.",
                source_type="model",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={"error": str(exc)},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                error_message=str(exc),
                duration_ms=duration_ms,
            )
        except LLMGenerationError as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.ENTITY_DETECTION,
                category="entity_extraction",
                severity=SeverityLevel.LOW,
                confidence=0.0,
                description="Entity extraction failed due to unparseable model response.",
                source_type="model",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.FAILED,
                metadata={"error": str(exc)},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[evidence],
                error_message=str(exc),
                duration_ms=duration_ms,
            )

        evidence_items: list[EvidenceContract] = []
        for entity in extraction.entities:
            # Map entity confidence to evidence confidence (NOT fraud probability)
            evidence_items.append(
                EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.ENTITY_DETECTION,
                    category=f"entity:{entity.entity_type.value}",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=entity.confidence,
                    description=f"Identified {entity.entity_type.value}: '{entity.name}' ({entity.normalized_value}). Not externally verified.",
                    source_type="model",
                    source_name=self.name,
                    source_version=f"{self.version}:{prompt_version}",
                    status=AnalysisStatus.SUCCESS,
                    raw_payload=entity.model_dump(),
                )
        )

        status = AnalysisStatus.SUCCESS if extraction.entities else AnalysisStatus.PARTIAL
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=status,
            evidence=evidence_items,
            output_data=extraction.model_dump(),
            duration_ms=duration_ms,
        )
