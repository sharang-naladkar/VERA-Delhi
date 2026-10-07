"""Video Forensic Preprocessing and Metadata Analysis Tool."""

import os
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.logging import get_logger
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.video_processor import VideoProcessor

logger = get_logger("app.investigator.tools.video_tool")


class VideoAnalysisTool(InvestigationTool):
    """
    Forensic video analysis tool extracting metadata, duration, frame rates,
    and performing bounded, controlled frame sampling for computer vision inspection.
    """

    def __init__(self, video_processor: VideoProcessor | None = None) -> None:
        self.video_processor = video_processor or VideoProcessor()

    @property
    def name(self) -> str:
        return "video_analyzer"

    @property
    def description(self) -> str:
        return "Performs bounded frame extraction and extracts video metadata (duration, FPS, resolution)."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        # Check for video bytes or reference
        video_bytes: bytes | None = state.get("video_bytes") or state.get("media_bytes")
        video_ref = state.get("raw_input_reference")

        if not video_bytes and video_ref and os.path.exists(str(video_ref)):
            try:
                with open(str(video_ref), "rb") as f:
                    video_bytes = f.read()
            except Exception as exc:
                logger.warning(f"Could not read video file from reference {video_ref}: {exc}")

        # If no video provided
        if not video_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="video_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No video media provided for video processing.",
                source_type="heuristic",
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
                output_data={"sampled_frame_count": 0},
                duration_ms=duration_ms,
            )

        try:
            res = self.video_processor.process_video(video_bytes)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            res_status_str = res.get("status", AnalysisStatus.SUCCESS.value)
            try:
                res_status = AnalysisStatus(res_status_str)
            except ValueError:
                res_status = AnalysisStatus.SUCCESS

            if res_status == AnalysisStatus.FAILED:
                err_msg = res.get("error", "Video processing failed")
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.FORENSIC_ARTIFACT,
                    category="video_analysis",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description=f"Video analysis failed: {err_msg}",
                    source_type="heuristic",
                    source_name=self.name,
                    source_version=self.version,
                    status=AnalysisStatus.FAILED,
                    metadata={"error": err_msg},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.FAILED,
                    evidence=[evidence],
                    output_data={"error": err_msg},
                    error_message=err_msg,
                    duration_ms=duration_ms,
                )

            metadata = res.get("metadata", {})
            sampled_frames = res.get("sampled_frames", [])

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="video_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=1.0,
                description=(
                    f"Video metadata: {metadata.get('duration_seconds')}s duration, "
                    f"{metadata.get('fps')} FPS, {metadata.get('resolution')} resolution. "
                    f"Sampled {len(sampled_frames)} bounded frames for forensic inspection."
                ),
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=metadata,
                metadata=metadata,
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data={
                            "metadata": metadata,
                            "sampled_frame_count": len(sampled_frames),
                            "sampled_timestamps": [f.get("timestamp_seconds") for f in sampled_frames],
                            "_sampled_frames": sampled_frames,
                        },
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error in VideoAnalysisTool: {exc}", exc_info=True)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.FORENSIC_ARTIFACT,
                category="video_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"Video processing encountered unexpected error: {exc}",
                source_type="heuristic",
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
                output_data={"error": str(exc)},
                error_message=str(exc),
                duration_ms=duration_ms,
            )
