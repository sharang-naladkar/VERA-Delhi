"""OCR Screenshot and Document Forensic Extraction Tool."""

import os
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.logging import get_logger
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.factory import get_ocr_provider
from app.providers.ocr import OCRProvider

logger = get_logger("app.investigator.tools.ocr_tool")


class OCRTool(InvestigationTool):
    """
    Forensic OCR analyzer extracting textual claims and indicators
    from uploaded screenshots, payment proofs, and investment flyers.
    """

    def __init__(self, ocr_provider: OCRProvider | None = None) -> None:
        self.ocr_provider = ocr_provider or get_ocr_provider()

    @property
    def name(self) -> str:
        return "ocr_analyzer"

    @property
    def description(self) -> str:
        return "Extracts text from screenshots, charts, and promotional graphics using OCR."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        # Check for image bytes or reference
        image_bytes: bytes | None = state.get("image_bytes") or state.get("media_bytes")
        image_ref = state.get("raw_input_reference")
        filename = state.get("filename")

        if not image_bytes and image_ref and os.path.exists(str(image_ref)):
            try:
                with open(str(image_ref), "rb") as f:
                    image_bytes = f.read()
            except Exception as exc:
                logger.warning(f"Could not read image file from reference {image_ref}: {exc}")

        # If no image provided in text-only investigation
        if not image_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.OCR_EXTRACTION,
                category="ocr_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No image media provided for OCR extraction.",
                source_type="provider",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                metadata={"is_skipped": True},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[evidence],
                output_data={"extracted_text": "", "blocks": []},
                duration_ms=duration_ms,
            )

        # Check provider availability
        if not self.ocr_provider.is_available:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.OCR_EXTRACTION,
                category="ocr_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="OCR extraction provider is unavailable. Text could not be extracted.",
                source_type="provider",
                source_name=self.ocr_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={"error": "OCR provider unavailable"},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={"extracted_text": "", "blocks": []},
                error_message="OCR provider is unavailable.",
                duration_ms=duration_ms,
            )

        try:
            res = await self.ocr_provider.extract_text(
                investigation_id=investigation_id,
                image_bytes=image_bytes,
                filename=filename,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            res_status_str = res.get("status", AnalysisStatus.SUCCESS.value)
            try:
                res_status = AnalysisStatus(res_status_str)
            except ValueError:
                res_status = AnalysisStatus.SUCCESS

            extracted_text = res.get("text", "")
            blocks = res.get("blocks", [])
            confidence = float(res.get("confidence", 0.0))

            if res_status == AnalysisStatus.INSUFFICIENT_EVIDENCE or not extracted_text.strip():
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.OCR_EXTRACTION,
                    category="ocr_analysis",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description="OCR completed but no readable text detected in image.",
                    source_type="provider",
                    source_name=self.ocr_provider.provider_name,
                    source_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    raw_payload=res,
                    metadata={"blocks_count": 0},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    evidence=[evidence],
                    output_data={"extracted_text": "", "blocks": []},
                    duration_ms=duration_ms,
                )

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.OCR_EXTRACTION,
                category="ocr_analysis",
                severity=SeverityLevel.LOW,
                confidence=confidence,
                description=(
                    f"OCR extracted {len(blocks)} text blocks ({len(extracted_text)} chars). "
                    "Note: OCR confidence is text recognition accuracy, not fraud probability."
                ),
                source_type="provider",
                source_name=self.ocr_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=res,
                metadata={
                    "char_count": len(extracted_text),
                    "block_count": len(blocks),
                    "confidence": confidence,
                    "language": res.get("language", "en"),
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data={
                    "extracted_text": extracted_text,
                    "blocks": blocks,
                    "confidence": confidence,
                },
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error in OCR tool execution: {exc}", exc_info=True)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.OCR_EXTRACTION,
                category="ocr_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"OCR execution failed: {exc}",
                source_type="provider",
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
                output_data={"extracted_text": "", "blocks": []},
                error_message=str(exc),
                duration_ms=duration_ms,
            )
