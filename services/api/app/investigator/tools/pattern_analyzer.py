"""Scam Pattern Analyzer Investigation Tool."""

import json
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.errors import LLMGenerationError, ProviderUnavailableError
from app.investigator.schemas import ScamPatternAnalysis
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.prompts.loader import format_prompt
from app.providers.llm import LLMProvider


class ScamPatternAnalyzerTool(InvestigationTool):
    """Analyzes behavioral scam patterns and linguistic pressure indicators."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    @property
    def name(self) -> str:
        return "scam_pattern_analyzer"

    @property
    def description(self) -> str:
        return "Correlates message tactics with known securities fraud techniques and manipulation patterns."

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
        entities = state.get("entities", [])
        claims = state.get("claims", [])

        if not text.strip():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[],
                output_data={"patterns": [], "indicators": [], "explanation": "Empty text."},
                duration_ms=duration_ms,
            )

        prompt, prompt_version = format_prompt(
            "investigator",
            "scam_pattern_analysis_v1",
            input_text=text,
            entities_json=json.dumps(entities, default=str),
            claims_json=json.dumps(claims, default=str),
        )

        try:
            analysis: ScamPatternAnalysis = await self.llm_provider.generate_structured(
                schema=ScamPatternAnalysis,
                prompt=prompt,
                temperature=0.0,
            )
        except ProviderUnavailableError as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.RISK_SIGNAL,
                category="scam_pattern_analysis",
                severity=SeverityLevel.LOW,
                confidence=0.0,
                description="Scam pattern analysis unavailable: LLM backend offline.",
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
                type=EvidenceType.RISK_SIGNAL,
                category="scam_pattern_analysis",
                severity=SeverityLevel.LOW,
                confidence=0.0,
                description="Scam pattern analysis failed due to unparseable model response.",
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
        if analysis.patterns or analysis.indicators:
            evidence_items.append(
                EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.RISK_SIGNAL,
                    category="scam_behavioral_patterns",
                    severity=SeverityLevel.HIGH if len(analysis.patterns) >= 2 else SeverityLevel.MEDIUM,
                    confidence=analysis.confidence,
                    description=f"Behavioral pattern analysis: {analysis.explanation}",
                    source_type="model",
                    source_name=self.name,
                    source_version=f"{self.version}:{prompt_version}",
                    status=AnalysisStatus.SUCCESS,
                    raw_payload=analysis.model_dump(),
                )
            )

        status = AnalysisStatus.SUCCESS if analysis.patterns else AnalysisStatus.PARTIAL
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=status,
            evidence=evidence_items,
            output_data=analysis.model_dump(),
            duration_ms=duration_ms,
        )
