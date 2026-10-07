"""Speech-to-Text (STT) Provider Interface, FasterWhisper, Mock, and Unavailable Fallbacks."""

import tempfile
import time
from abc import abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger("app.providers.stt")


class STTProvider(BaseProvider):
    """Interface for Speech-to-Text audio transcription."""

    @abstractmethod
    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Transcribe speech to text with timestamps and segments."""
        pass


class FasterWhisperSTTProvider(STTProvider):
    """
    faster-whisper local/offline STT provider.
    Loads lazily and handles missing dependencies gracefully without crashing.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Any = None
        self._is_initialized = False
        self._init_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "faster_whisper"

    @property
    def is_available(self) -> bool:
        if not self._is_initialized:
            self._try_init()
        return self._model is not None and self._init_error is None

    def _try_init(self) -> None:
        """Lazy initialization of faster-whisper model."""
        self._is_initialized = True
        try:
            from faster_whisper import WhisperModel  # type: ignore

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._init_error = None
        except Exception as exc:
            self._model = None
            self._init_error = f"faster-whisper unavailable: {exc}"
            logger.warning(f"Failed to initialize faster-whisper engine: {exc}")

    async def health_check(self) -> dict[str, Any]:
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": self._init_error or "faster-whisper engine is not installed or available.",
            }
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "faster-whisper is ready.",
        }

    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "error": self._init_error or "faster-whisper dependency is not installed.",
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        if not audio_bytes:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "error": "Empty audio bytes provided.",
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        tmp_path = None
        try:
            # Write to temporary file for audio decoding
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = Path(tmp_file.name)

            segments_iter, info = self._model.transcribe(
                str(tmp_path),
                language=language,
                beam_size=5,
            )

            segments: list[dict[str, Any]] = []
            transcript_parts: list[str] = []
            total_prob = 0.0

            for seg in segments_iter:
                text = seg.text.strip()
                if text:
                    transcript_parts.append(text)
                    prob = getattr(seg, "avg_logprob", 0.0)
                    total_prob += prob
                    segments.append({
                        "id": seg.id,
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": text,
                        "confidence": round(float(getattr(seg, "no_speech_prob", 0.0)), 4),
                    })

            full_transcript = " ".join(transcript_parts).strip()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if not full_transcript:
                return {
                    "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "transcript": "",
                    "segments": [],
                    "language": info.language if hasattr(info, "language") else language,
                    "duration_ms": duration_ms,
                    "metadata": {"speech_detected": False},
                }

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": full_transcript,
                "segments": segments,
                "language": info.language if hasattr(info, "language") else language,
                "duration_ms": duration_ms,
                "metadata": {
                    "segment_count": len(segments),
                    "audio_duration_seconds": round(getattr(info, "duration", 0.0), 2),
                },
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error during audio transcription: {exc}", exc_info=True)
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "error": f"Audio transcription error: {exc}",
                "duration_ms": duration_ms,
            }
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


class MockSTTProvider(STTProvider):
    """Deterministic Mock STT provider for unit tests and local mock scenarios."""

    def __init__(
        self,
        mock_transcript: str = "Deposit money into this account today and receive guaranteed 50% weekly profit.",
        mock_status: AnalysisStatus = AnalysisStatus.SUCCESS,
        mock_language: str = "en",
        mock_segments: list[dict[str, Any]] | None = None,
    ) -> None:
        self.mock_transcript = mock_transcript
        self.mock_status = mock_status
        self.mock_language = mock_language
        self.mock_segments = mock_segments or [
            {
                "id": 0,
                "start": 0.0,
                "end": 4.5,
                "text": mock_transcript,
                "confidence": 0.96,
            }
        ]

    @property
    def provider_name(self) -> str:
        return "mock_stt"

    @property
    def is_available(self) -> bool:
        return self.mock_status != AnalysisStatus.UNAVAILABLE

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.mock_status.value,
            "provider": self.provider_name,
            "message": "Mock STT provider active.",
        }

    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        if self.mock_status == AnalysisStatus.UNAVAILABLE:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "error": "Mock STT provider configured as unavailable.",
            }

        if self.mock_status == AnalysisStatus.FAILED:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "error": "Simulated mock STT failure.",
            }

        if not self.mock_transcript.strip() or self.mock_status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "transcript": "",
                "segments": [],
                "language": self.mock_language,
                "metadata": {"speech_detected": False},
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "transcript": self.mock_transcript,
            "segments": self.mock_segments,
            "language": language or self.mock_language,
            "metadata": {
                "segment_count": len(self.mock_segments),
                "is_mock": True,
            },
        }


class UnavailableSTTProvider(STTProvider):
    """Fail-safe placeholder for STT provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_stt"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "STT engine is not configured in Phase 01.",
        }

    async def transcribe(
        self,
        investigation_id: UUID,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "transcript": "",
            "segments": [],
            "error": "STT provider is unavailable.",
        }
