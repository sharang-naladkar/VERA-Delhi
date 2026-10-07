"""Deepfake and Facial Manipulation Forensic Tool."""

import os
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.logging import get_logger
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.deepfake import DeepfakeProvider
from app.providers.face_detector import FaceDetectorProvider
from app.providers.factory import get_deepfake_provider, get_face_detector_provider

logger = get_logger("app.investigator.tools.deepfake_tool")


class DeepfakeDetectionTool(InvestigationTool):
    """
    Forensic Deepfake Detection tool analyzing face regions across images and
    video frames using MesoNet/Meso4 architectures.
    Produces risk signals while strictly distinguishing model scores from fraud probabilities.
    """

    DISCLAIMER = "MODEL SCORE != PROBABILITY OF FRAUD; MODEL SCORE != LEGAL DETERMINATION"

    def __init__(
        self,
        deepfake_provider: DeepfakeProvider | None = None,
        face_detector: FaceDetectorProvider | None = None,
    ) -> None:
        self.deepfake_provider = deepfake_provider or get_deepfake_provider()
        self.face_detector = face_detector or get_face_detector_provider()

    @property
    def name(self) -> str:
        return "deepfake_detector"

    @property
    def description(self) -> str:
        return "Analyzes human facial regions for synthetic manipulation, AI-generation, or deepfake artifacts."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        # Check for image or media bytes
        media_bytes: bytes | None = state.get("image_bytes") or state.get("media_bytes")
        media_ref = state.get("raw_input_reference")
        media_type = state.get("media_type", "image")

        if not media_bytes and media_ref and os.path.exists(str(media_ref)):
            try:
                with open(str(media_ref), "rb") as f:
                    media_bytes = f.read()
            except Exception as exc:
                logger.warning(f"Could not read media file from reference {media_ref}: {exc}")

        # If no media provided
        if not media_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.DEEPFAKE_ANALYSIS,
                category="deepfake_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No media provided for deepfake analysis.",
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
                output_data={"manipulation_score": None},
                duration_ms=duration_ms,
            )

        # Check provider availability (e.g. missing weights)
        if not self.deepfake_provider.is_available:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.DEEPFAKE_ANALYSIS,
                category="deepfake_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=(
                    "Deepfake model weights unavailable. Cannot evaluate synthetic media manipulation. "
                    "Unavailability is NOT considered evidence of authenticity."
                ),
                source_type="provider",
                source_name=self.deepfake_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={"error": "Deepfake model weights unavailable", "fake": None},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={"manipulation_score": None, "fake": None},
                error_message="Deepfake model weights unavailable.",
                duration_ms=duration_ms,
            )

        try:
            # First check if faces exist in the media
            face_result = await self.face_detector.detect_faces(investigation_id, media_bytes)
            faces = face_result.get("faces", [])
            if not faces and face_result.get("status") == AnalysisStatus.INSUFFICIENT_EVIDENCE.value:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.DEEPFAKE_ANALYSIS,
                    category="deepfake_analysis",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description="No face regions detected for facial manipulation analysis.",
                    source_type="provider",
                    source_name=self.name,
                    source_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    metadata={"faces_analyzed": 0},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    evidence=[evidence],
                    output_data={"manipulation_score": None, "faces_analyzed": 0},
                    duration_ms=duration_ms,
                )

            # Execute deepfake provider analysis
            res = await self.deepfake_provider.analyze_media(
                investigation_id=investigation_id,
                media_bytes=media_bytes,
                media_type=media_type,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            res_status_str = res.get("status", AnalysisStatus.SUCCESS.value)
            try:
                res_status = AnalysisStatus(res_status_str)
            except ValueError:
                res_status = AnalysisStatus.SUCCESS

            if res_status in (AnalysisStatus.UNAVAILABLE, AnalysisStatus.FAILED):
                err = res.get("error", "Deepfake detector execution failed")
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.DEEPFAKE_ANALYSIS,
                    category="deepfake_analysis",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description=f"Deepfake analysis outcome: {err}",
                    source_type="provider",
                    source_name=self.deepfake_provider.provider_name,
                    source_version=self.version,
                    status=res_status,
                    metadata={"error": err},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=res_status,
                    evidence=[evidence],
                    output_data={"manipulation_score": None},
                    error_message=err,
                    duration_ms=duration_ms,
                )

            score = res.get("manipulation_score")
            conf = float(res.get("confidence", 0.0))
            faces_analyzed = int(res.get("faces_analyzed", len(faces)))
            model_name = res.get("model", "Meso4")

            # Determine severity based on manipulation signal
            severity = SeverityLevel.INFORMATIONAL
            if score is not None:
                if score >= 0.7:
                    severity = SeverityLevel.HIGH
                elif score >= 0.4:
                    severity = SeverityLevel.MEDIUM
                else:
                    severity = SeverityLevel.LOW

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.DEEPFAKE_ANALYSIS,
                category="deepfake_analysis",
                severity=severity,
                confidence=conf,
                description=(
                    f"MesoNet manipulation score: {score} across {faces_analyzed} face(s). "
                    f"Disclaimer: {self.DISCLAIMER}."
                ),
                source_type="model",
                source_name=self.deepfake_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=res,
                metadata={
                    "manipulation_score": score,
                    "confidence": conf,
                    "faces_analyzed": faces_analyzed,
                    "model": model_name,
                    "disclaimer": self.DISCLAIMER,
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data={
                    "manipulation_score": score,
                    "confidence": conf,
                    "faces_analyzed": faces_analyzed,
                    "model": model_name,
                    "disclaimer": self.DISCLAIMER,
                },
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error in DeepfakeDetectionTool: {exc}", exc_info=True)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.DEEPFAKE_ANALYSIS,
                category="deepfake_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"Deepfake detection failed with unexpected error: {exc}",
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
                output_data={"manipulation_score": None},
                error_message=str(exc),
                duration_ms=duration_ms,
            )
