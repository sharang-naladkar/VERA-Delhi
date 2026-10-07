"""Input Normalization and Forensic Ingestion Tool."""

import re
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult


class InputNormalizerTool(InvestigationTool):
    """Sanitizes text inputs, normalizes unicode, and checks minimum forensic sufficiency."""

    @property
    def name(self) -> str:
        return "input_normalizer"

    @property
    def description(self) -> str:
        return "Normalizes whitespace, removes zero-width characters, and establishes ingestion baseline."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        raw_text = state.get("raw_input_text", "")
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        if not raw_text or not raw_text.strip():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="input_normalization",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=1.0,
                description="Input text is empty. Insufficient evidence for investigation.",
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[evidence],
                output_data={"normalized_text": "", "char_count": 0, "word_count": 0},
                duration_ms=duration_ms,
            )

        # Normalize unicode and whitespace
        normalized = re.sub(r"[\u200B-\u200D\uFEFF]", "", raw_text)  # Strip zero-width chars
        normalized = re.sub(r"\r\n|\r", "\n", normalized)  # Standardize newlines
        normalized = re.sub(r"[ \t]+", " ", normalized).strip()

        char_count = len(normalized)
        words = normalized.split()
        word_count = len(words)

        status = AnalysisStatus.SUCCESS
        if word_count < 3:
            status = AnalysisStatus.PARTIAL

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        evidence = EvidenceContract(
            investigation_id=investigation_id,
            input_id=input_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="input_normalization",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0,
            description=f"Input sanitized and normalized ({word_count} words, {char_count} chars).",
            source_type="heuristic",
            source_name=self.name,
            source_version=self.version,
            status=status,
            raw_payload={"char_count": char_count, "word_count": word_count},
        )

        return ToolResult(
            tool_name=self.name,
            tool_version=self.version,
            status=status,
            evidence=[evidence],
            output_data={
                "normalized_text": normalized,
                "char_count": char_count,
                "word_count": word_count,
            },
            duration_ms=duration_ms,
        )
