"""Face Detection Forensic Tool."""

import os
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.logging import get_logger
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.face_detector import FaceDetectorProvider
from app.providers.factory import get_face_detector_provider

logger = get_logger("app.investigator.tools.face_tool")


class FaceDetectionTool(InvestigationTool):
    """
    Forensic Face Detection tool isolating face bounding regions for subsequent
    deepfake, impersonation, or facial manipulation inspection.
    """

    def __init__(self, face_detector: FaceDetectorProvider | None = None) -> None:
        self.face_detector = face_detector or get_face_detector_provider()

    @property
    def name(self) -> str:
        return "face_detector"

    @property
    def description(self) -> str:
        return "Detects human face regions and bounding boxes within media frames."

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

        if not image_bytes and image_ref and os.path.exists(str(image_ref)):
            try:
                with open(str(image_ref), "rb") as f:
                    image_bytes = f.read()
            except Exception as exc:
                logger.warning(f"Could not read image file from reference {image_ref}: {exc}")

        # If no image provided
        if not image_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="face_detection",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No image media provided for face detection.",
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
                output_data={"faces": [], "face_count": 0},
                duration_ms=duration_ms,
            )

        # Check provider availability
        if not self.face_detector.is_available:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="face_detection",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="Face detection provider is unavailable.",
                source_type="provider",
                source_name=self.face_detector.provider_name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={"error": "Face detector unavailable"},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={"faces": [], "face_count": 0},
                error_message="Face detector is unavailable.",
                duration_ms=duration_ms,
            )

        try:
            res = await self.face_detector.detect_faces(
                investigation_id=investigation_id,
                image_bytes=image_bytes,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            res_status_str = res.get("status", AnalysisStatus.SUCCESS.value)
            try:
                res_status = AnalysisStatus(res_status_str)
            except ValueError:
                res_status = AnalysisStatus.SUCCESS

            faces = res.get("faces", [])
            face_count = int(res.get("face_count", len(faces)))

            # If no face detected, NOT fraud!
            if res_status == AnalysisStatus.INSUFFICIENT_EVIDENCE or face_count == 0:
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.FORENSIC_ARTIFACT,
                    category="face_detection",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=1.0,
                    description="No human face regions detected. Lack of faces is NOT considered evidence of fraud.",
                    source_type="provider",
                    source_name=self.face_detector.provider_name,
                    source_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    raw_payload=res,
                    metadata={"face_count": 0},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    evidence=[evidence],
                    output_data={"faces": [], "face_count": 0},
                    duration_ms=duration_ms,
                )

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="face_detection",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=1.0,
                description=f"Detected {face_count} human face regions for downstream forensic manipulation inspection.",
                source_type="provider",
                source_name=self.face_detector.provider_name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=res,
                metadata={"face_count": face_count, "faces": faces},
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data={"faces": faces, "face_count": face_count},
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error in FaceDetectionTool: {exc}", exc_info=True)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="face_detection",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"Face detection failed: {exc}",
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
                output_data={"faces": [], "face_count": 0},
                error_message=str(exc),
                duration_ms=duration_ms,
            )
