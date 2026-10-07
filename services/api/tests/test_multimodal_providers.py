"""Unit Tests for Phase 03 Multimodal Providers and Provider Factory."""

import uuid
from types import SimpleNamespace

import pytest

from app.contracts.status import AnalysisStatus
from app.providers.deepfake import (
    MesoNetDeepfakeProvider,
    MockDeepfakeProvider,
    UnavailableDeepfakeProvider,
)
from app.providers.face_detector import (
    MockFaceDetectorProvider,
    OpenCVFaceDetectorProvider,
)
from app.providers.factory import (
    get_deepfake_provider,
    get_face_detector_provider,
    get_ocr_provider,
    get_stt_provider,
)
from app.providers.ocr import (
    MockOCRProvider,
    PaddleOCRProvider,
    UnavailableOCRProvider,
)
from app.providers.stt import (
    FasterWhisperSTTProvider,
    MockSTTProvider,
    UnavailableSTTProvider,
)
from app.providers.video_processor import VideoProcessor

# =============================================================================
# OCR Provider Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_ocr_provider_success() -> None:
    inv_id = uuid.uuid4()
    provider = MockOCRProvider(mock_text="SEBI Reg. No. INH000001234 - Guaranteed Returns")
    assert provider.is_available is True
    assert provider.provider_name == "mock_ocr"

    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.SUCCESS.value

    res = await provider.extract_text(investigation_id=inv_id, image_bytes=b"fake_image_bytes")
    assert res["status"] == AnalysisStatus.SUCCESS.value
    assert "SEBI Reg. No." in res["text"]
    assert len(res["blocks"]) > 0
    assert res["confidence"] == 0.95
    assert res["metadata"]["is_mock"] is True


@pytest.mark.asyncio
async def test_mock_ocr_provider_empty_and_insufficient_evidence() -> None:
    inv_id = uuid.uuid4()
    provider = MockOCRProvider(mock_text="", mock_status=AnalysisStatus.INSUFFICIENT_EVIDENCE)
    res = await provider.extract_text(investigation_id=inv_id, image_bytes=b"fake_image_bytes")
    assert res["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value
    assert res["text"] == ""
    assert res["blocks"] == []


@pytest.mark.asyncio
async def test_mock_ocr_provider_failure_and_unavailable() -> None:
    inv_id = uuid.uuid4()
    failing_provider = MockOCRProvider(mock_status=AnalysisStatus.FAILED)
    res_fail = await failing_provider.extract_text(investigation_id=inv_id, image_bytes=b"fake_image")
    assert res_fail["status"] == AnalysisStatus.FAILED.value
    assert "Simulated mock OCR failure" in res_fail["error"]

    unavail_provider = MockOCRProvider(mock_status=AnalysisStatus.UNAVAILABLE)
    assert unavail_provider.is_available is False
    res_unavail = await unavail_provider.extract_text(investigation_id=inv_id, image_bytes=b"fake_image")
    assert res_unavail["status"] == AnalysisStatus.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_paddleocr_provider_graceful_handling() -> None:
    """PaddleOCR handles missing dependency or uninitialized state cleanly."""
    provider = PaddleOCRProvider()
    assert provider.provider_name == "paddleocr"
    # If paddleocr is not installed, it should not crash
    health = await provider.health_check()
    assert health["status"] in (AnalysisStatus.SUCCESS.value, AnalysisStatus.UNAVAILABLE.value)

    res = await provider.extract_text(investigation_id=uuid.uuid4(), image_bytes=b"")
    # Empty bytes should return INSUFFICIENT_EVIDENCE or UNAVAILABLE
    assert res["status"] in (AnalysisStatus.INSUFFICIENT_EVIDENCE.value, AnalysisStatus.UNAVAILABLE.value)


# =============================================================================
# STT Provider Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_stt_provider_success() -> None:
    inv_id = uuid.uuid4()
    provider = MockSTTProvider(mock_transcript="Invest 10000 rupees and get 50000 in two days guaranteed.")
    assert provider.is_available is True
    assert provider.provider_name == "mock_stt"

    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.SUCCESS.value

    res = await provider.transcribe(investigation_id=inv_id, audio_bytes=b"fake_audio_bytes")
    assert res["status"] == AnalysisStatus.SUCCESS.value
    assert "Invest 10000 rupees" in res["transcript"]
    assert len(res["segments"]) > 0
    assert res["language"] == "en"


@pytest.mark.asyncio
async def test_mock_stt_provider_no_speech_and_insufficient_evidence() -> None:
    inv_id = uuid.uuid4()
    provider = MockSTTProvider(mock_transcript="", mock_status=AnalysisStatus.INSUFFICIENT_EVIDENCE)
    res = await provider.transcribe(investigation_id=inv_id, audio_bytes=b"fake_audio_bytes")
    assert res["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value
    assert res["transcript"] == ""
    assert res["segments"] == []


@pytest.mark.asyncio
async def test_mock_stt_provider_failure_and_unavailable() -> None:
    inv_id = uuid.uuid4()
    failing = MockSTTProvider(mock_status=AnalysisStatus.FAILED)
    res_f = await failing.transcribe(investigation_id=inv_id, audio_bytes=b"fake_audio")
    assert res_f["status"] == AnalysisStatus.FAILED.value
    assert "Simulated mock STT failure" in res_f["error"]

    unavail = MockSTTProvider(mock_status=AnalysisStatus.UNAVAILABLE)
    assert unavail.is_available is False
    res_u = await unavail.transcribe(investigation_id=inv_id, audio_bytes=b"fake_audio")
    assert res_u["status"] == AnalysisStatus.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_faster_whisper_provider_graceful_handling() -> None:
    """faster-whisper handles missing dependency or uninitialized state cleanly."""
    provider = FasterWhisperSTTProvider()
    assert provider.provider_name == "faster_whisper"
    health = await provider.health_check()
    assert health["status"] in (AnalysisStatus.SUCCESS.value, AnalysisStatus.UNAVAILABLE.value)

    res = await provider.transcribe(investigation_id=uuid.uuid4(), audio_bytes=b"")
    assert res["status"] in (AnalysisStatus.INSUFFICIENT_EVIDENCE.value, AnalysisStatus.UNAVAILABLE.value)


# =============================================================================
# Face Detector Provider Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_face_detector_provider() -> None:
    inv_id = uuid.uuid4()
    provider = MockFaceDetectorProvider(mock_face_count=2)
    assert provider.is_available is True
    assert provider.provider_name == "mock_face_detector"

    res = await provider.detect_faces(investigation_id=inv_id, image_bytes=b"fake_image")
    assert res["status"] == AnalysisStatus.SUCCESS.value
    assert res["face_count"] == 1 or res["face_count"] == 2
    assert len(res["faces"]) > 0

    # No face detected
    no_faces = MockFaceDetectorProvider(mock_face_count=0)
    res_none = await no_faces.detect_faces(investigation_id=inv_id, image_bytes=b"fake_image")
    assert res_none["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value
    assert res_none["face_count"] == 0


@pytest.mark.asyncio
async def test_opencv_face_detector_offline() -> None:
    inv_id = uuid.uuid4()
    provider = OpenCVFaceDetectorProvider()
    assert provider.provider_name == "opencv_face_detector"

    # Empty image bytes
    res_empty = await provider.detect_faces(investigation_id=inv_id, image_bytes=b"")
    assert res_empty["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value

    # Invalid image bytes
    res_inv = await provider.detect_faces(investigation_id=inv_id, image_bytes=b"not_an_image")
    assert res_inv["status"] in (AnalysisStatus.FAILED.value, AnalysisStatus.UNAVAILABLE.value)


# =============================================================================
# Deepfake Provider Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mock_deepfake_provider_scores_and_disclaimer() -> None:
    inv_id = uuid.uuid4()
    provider = MockDeepfakeProvider(mock_score=0.88, mock_confidence=0.92)
    assert provider.is_available is True
    assert provider.provider_name == "mock_deepfake"

    res = await provider.analyze_media(investigation_id=inv_id, media_bytes=b"fake_media", media_type="image")
    assert res["status"] == AnalysisStatus.SUCCESS.value
    assert res["manipulation_score"] == 0.88
    assert res["confidence"] == 0.92
    assert "MODEL SCORE != PROBABILITY OF FRAUD" in res["disclaimer"]
    assert res["frames_analyzed"] == 5
    assert res["faces_analyzed"] == 2


@pytest.mark.asyncio
async def test_mesonet_deepfake_missing_weights_unavailable() -> None:
    """Missing model weights MUST return UNAVAILABLE and NEVER return authentic or fake=False."""
    inv_id = uuid.uuid4()
    provider = MesoNetDeepfakeProvider(weights_path="nonexistent_weights.h5")
    assert provider.is_available is False

    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value
    assert "weights unavailable" in health["message"].lower()

    res = await provider.analyze_media(investigation_id=inv_id, media_bytes=b"fake_media", media_type="image")
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["manipulation_score"] is None
    assert res.get("fake") is None or res.get("fake") is not False  # Must not claim authentic!
    assert "weights unavailable" in res["error"].lower()


# =============================================================================
# Video Processor Tests
# =============================================================================

def test_video_processor_bounds_and_empty() -> None:
    processor = VideoProcessor(max_frames=5, sample_interval_seconds=0.5, max_file_size_bytes=1000)

    # Empty bytes
    res_empty = processor.process_video(b"")
    assert res_empty["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value

    # Exceeding size
    oversized = b"x" * 2000
    res_oversized = processor.process_video(oversized)
    assert res_oversized["status"] == AnalysisStatus.FAILED.value
    assert "exceeds configured safety limit" in res_oversized["error"]

    # Invalid bytes
    res_invalid = processor.process_video(b"not_a_valid_video_stream")
    assert res_invalid["status"] == AnalysisStatus.FAILED.value


def test_video_processor_synthetic_video() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    p = tempfile.mktemp(suffix=".mp4")
    try:
        out = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 64))
        for _ in range(20):
            frame = np.full((64, 64, 3), 128, dtype=np.uint8)
            out.write(frame)
        out.release()

        with open(p, "rb") as f:
            video_bytes = f.read()

        processor = VideoProcessor(max_frames=5, sample_interval_seconds=0.2)
        res = processor.process_video(video_bytes)
        assert res["status"] == AnalysisStatus.SUCCESS.value
        metadata = res["metadata"]
        assert metadata["resolution"]["width"] == 64
        assert metadata["resolution"]["height"] == 64
        assert len(res["sampled_frames"]) <= 5
        assert res["sampled_frames"][0]["frame_bytes"] is not None
    finally:
        if os.path.exists(p):
            os.remove(p)


# =============================================================================
# Provider Factory Tests
# =============================================================================

def test_provider_factory_selection() -> None:
    # OCR factory
    mock_ocr = get_ocr_provider(SimpleNamespace(OCR_PROVIDER="mock"))
    assert isinstance(mock_ocr, MockOCRProvider)

    unavail_ocr = get_ocr_provider(SimpleNamespace(OCR_PROVIDER="unavailable"))
    assert isinstance(unavail_ocr, UnavailableOCRProvider)

    # STT factory
    mock_stt = get_stt_provider(SimpleNamespace(STT_PROVIDER="mock"))
    assert isinstance(mock_stt, MockSTTProvider)

    unavail_stt = get_stt_provider(SimpleNamespace(STT_PROVIDER="unavailable"))
    assert isinstance(unavail_stt, UnavailableSTTProvider)

    # Face detector factory
    mock_face = get_face_detector_provider(SimpleNamespace(FACE_DETECTOR_PROVIDER="mock"))
    assert isinstance(mock_face, MockFaceDetectorProvider)

    opencv_face = get_face_detector_provider(SimpleNamespace(FACE_DETECTOR_PROVIDER="opencv"))
    assert isinstance(opencv_face, OpenCVFaceDetectorProvider)

    # Deepfake factory
    mock_df = get_deepfake_provider(SimpleNamespace(DEEPFAKE_PROVIDER="mock"))
    assert isinstance(mock_df, MockDeepfakeProvider)

    unavail_df = get_deepfake_provider(SimpleNamespace(DEEPFAKE_PROVIDER="unavailable"))
    assert isinstance(unavail_df, UnavailableDeepfakeProvider)

    # MesoNet without weights
    mesonet_df = get_deepfake_provider(
        SimpleNamespace(DEEPFAKE_PROVIDER="mesonet", MESONET_WEIGHTS_PATH=None)
    )
    assert isinstance(mesonet_df, MesoNetDeepfakeProvider)
    assert mesonet_df.is_available is False
