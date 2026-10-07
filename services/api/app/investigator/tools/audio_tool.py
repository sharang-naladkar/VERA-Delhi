"""Audio and Speech-to-Text Forensic Transcription Tool."""

import os
import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.core.logging import get_logger
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.factory import get_stt_provider
from app.providers.stt import STTProvider

logger = get_logger("app.investigator.tools.audio_tool")


class AudioTranscriptionTool(InvestigationTool):
    """
    Forensic Speech-to-Text tool transcribing audio pitches, phone recordings,
    and voice notes into auditable textual evidence.
    """

    def __init__(self, stt_provider: STTProvider | None = None) -> None:
        self.stt_provider = stt_provider or get_stt_provider()

    @property
    def name(self) -> str:
        return "audio_transcriber"

    @property
    def description(self) -> str:
        return "Transcribes audio recordings, voice notes, and video audio streams into text."

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        inv_id_str = state.get("investigation_id")
        investigation_id = UUID(inv_id_str) if inv_id_str else uuid4()
        input_id_str = state.get("input_id")
        input_id = UUID(input_id_str) if input_id_str else None

        # Check for audio bytes or reference
        audio_bytes: bytes | None = state.get("audio_bytes") or state.get("media_bytes")
        audio_ref = state.get("raw_input_reference")
        language = state.get("language")

        if not audio_bytes and audio_ref and os.path.exists(str(audio_ref)):
            try:
                with open(str(audio_ref), "rb") as f:
                    audio_bytes = f.read()
            except Exception as exc:
                logger.warning(f"Could not read audio file from reference {audio_ref}: {exc}")

        # If no audio provided
        if not audio_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.AUDIO_TRANSCRIPTION,
                category="audio_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No audio media provided for speech transcription.",
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
                output_data={"transcript": "", "segments": []},
                duration_ms=duration_ms,
            )

        # Check provider availability
        if not self.stt_provider.is_available:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.AUDIO_TRANSCRIPTION,
                category="audio_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="STT transcription provider is unavailable. Audio could not be transcribed.",
                source_type="provider",
                source_name=self.stt_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                metadata={"error": "STT provider unavailable"},
            )
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.UNAVAILABLE,
                evidence=[evidence],
                output_data={"transcript": "", "segments": []},
                error_message="STT provider is unavailable.",
                duration_ms=duration_ms,
            )

        try:
            res = await self.stt_provider.transcribe(
                investigation_id=investigation_id,
                audio_bytes=audio_bytes,
                language=language,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            res_status_str = res.get("status", AnalysisStatus.SUCCESS.value)
            try:
                res_status = AnalysisStatus(res_status_str)
            except ValueError:
                res_status = AnalysisStatus.SUCCESS

            transcript = res.get("transcript", "")
            segments = res.get("segments", [])

            if res_status == AnalysisStatus.INSUFFICIENT_EVIDENCE or not transcript.strip():
                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.AUDIO_TRANSCRIPTION,
                    category="audio_analysis",
                    severity=SeverityLevel.INFORMATIONAL,
                    confidence=0.0,
                    description="Audio analyzed but no discernible speech was detected.",
                    source_type="provider",
                    source_name=self.stt_provider.provider_name,
                    source_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    raw_payload=res,
                    metadata={"segment_count": 0},
                )
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    evidence=[evidence],
                    output_data={"transcript": "", "segments": []},
                    duration_ms=duration_ms,
                )

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.AUDIO_TRANSCRIPTION,
                category="audio_analysis",
                severity=SeverityLevel.LOW,
                confidence=1.0,
                description=(
                    f"Transcribed audio into {len(segments)} segments ({len(transcript)} chars). "
                    "Note: STT accuracy is linguistic confidence, NOT fraud probability."
                ),
                source_type="provider",
                source_name=self.stt_provider.provider_name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=res,
                metadata={
                    "char_count": len(transcript),
                    "segment_count": len(segments),
                    "language": res.get("language"),
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data={
                    "transcript": transcript,
                    "segments": segments,
                },
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error in STT tool execution: {exc}", exc_info=True)
            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.AUDIO_TRANSCRIPTION,
                category="audio_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"Audio transcription failed: {exc}",
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
                output_data={"transcript": "", "segments": []},
                error_message=str(exc),
                duration_ms=duration_ms,
            )
