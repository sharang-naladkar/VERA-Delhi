"""Video Preprocessing, Metadata Extraction, and Bounded Frame Sampling."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from app.contracts.status import AnalysisStatus
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.providers.video_processor")


class VideoProcessor:
    """
    Deterministic, resource-bounded video preprocessing using OpenCV with optional FFmpeg awareness.
    Guarantees bounded sampling to prevent memory/CPU exhaustion.
    """

    def __init__(
        self,
        max_frames: int | None = None,
        sample_interval_seconds: float | None = None,
        max_file_size_bytes: int | None = None,
    ) -> None:
        self.max_frames = max_frames or getattr(settings, "VIDEO_MAX_FRAMES", 10)
        self.sample_interval_seconds = (
            sample_interval_seconds or getattr(settings, "VIDEO_SAMPLE_INTERVAL_SECONDS", 1.0)
        )
        self.max_file_size_bytes = (
            max_file_size_bytes or getattr(settings, "MAX_MEDIA_FILE_SIZE_BYTES", 52428800)
        )

    @property
    def is_ffmpeg_available(self) -> bool:
        """Checks if ffmpeg executable is discovered on PATH."""
        return shutil.which("ffmpeg") is not None

    def process_video(
        self,
        video_bytes: bytes,
        max_frames: int | None = None,
        sample_interval_seconds: float | None = None,
    ) -> dict[str, Any]:
        """
        Extracts duration, fps, resolution, and samples bounded frames from video bytes.
        """
        start_time = time.perf_counter()
        limit_frames = max_frames or self.max_frames
        interval_sec = sample_interval_seconds or self.sample_interval_seconds

        if not video_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "error": "Empty video bytes provided.",
                "metadata": {"ffmpeg_available": self.is_ffmpeg_available},
                "sampled_frames": [],
                "duration_ms": duration_ms,
            }

        if len(video_bytes) > self.max_file_size_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": AnalysisStatus.FAILED.value,
                "error": (
                    f"Video file size ({len(video_bytes)} bytes) exceeds configured "
                    f"safety limit ({self.max_file_size_bytes} bytes)."
                ),
                "metadata": {"ffmpeg_available": self.is_ffmpeg_available},
                "sampled_frames": [],
                "duration_ms": duration_ms,
            }

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_file.write(video_bytes)
                tmp_path = Path(tmp_file.name)

            import cv2  # type: ignore

            cap = cv2.VideoCapture(str(tmp_path))
            if not cap.isOpened():
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "status": AnalysisStatus.FAILED.value,
                    "error": "Failed to decode video stream. Invalid or unsupported video format.",
                    "metadata": {"ffmpeg_available": self.is_ffmpeg_available},
                    "sampled_frames": [],
                    "duration_ms": duration_ms,
                }

            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            duration_seconds = round(total_frames / fps, 2) if (fps > 0 and total_frames > 0) else 0.0

            # Compute bounded sampling step
            step = max(1, int(fps * interval_sec)) if fps > 0 else 1

            sampled_frames: list[dict[str, Any]] = []
            current_frame_idx = 0

            while cap.isOpened() and len(sampled_frames) < limit_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if current_frame_idx % step == 0:
                    timestamp = round(current_frame_idx / fps, 2) if fps > 0 else 0.0
                    # Encode frame to JPEG bytes for safe transport
                    success, buffer = cv2.imencode(".jpg", frame)
                    if success:
                        sampled_frames.append({
                            "frame_index": current_frame_idx,
                            "timestamp_seconds": timestamp,
                            "frame_bytes": buffer.tobytes(),
                        })

                current_frame_idx += 1

            cap.release()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "metadata": {
                    "duration_seconds": duration_seconds,
                    "fps": round(fps, 2),
                    "total_frames": total_frames,
                    "resolution": {"width": width, "height": height},
                    "sampled_frame_count": len(sampled_frames),
                    "max_frames_limit": limit_frames,
                    "sampling_interval_seconds": interval_sec,
                    "ffmpeg_available": self.is_ffmpeg_available,
                },
                "sampled_frames": sampled_frames,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error during video processing: {exc}", exc_info=True)
            return {
                "status": AnalysisStatus.FAILED.value,
                "error": f"Video processing error: {exc}",
                "metadata": {"ffmpeg_available": self.is_ffmpeg_available},
                "sampled_frames": [],
                "duration_ms": duration_ms,
            }
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
