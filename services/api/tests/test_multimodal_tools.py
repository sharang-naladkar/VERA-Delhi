"""Unit Tests for Phase 03 Multimodal Investigation Tools and Evidence Contracts."""

import os
import tempfile
import uuid

import pytest

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.audio_tool import AudioTranscriptionTool
from app.investigator.tools.deepfake_tool import DeepfakeDetectionTool
from app.investigator.tools.face_tool import FaceDetectionTool
from app.investigator.tools.ocr_tool import OCRTool
from app.investigator.tools.video_tool import VideoAnalysisTool
from app.providers.deepfake import (
    MesoNetDeepfakeProvider,
    MockDeepfakeProvider,
)
from app.providers.face_detector import (
    MockFaceDetectorProvider,
    UnavailableFaceDetectorProvider,
)
from app.providers.ocr import (
    MockOCRProvider,
    UnavailableOCRProvider,
)
from app.providers.stt import (
    MockSTTProvider,
    UnavailableSTTProvider,
)

# =============================================================================
# OCR Tool Tests
# =============================================================================

@pytest.mark.asyncio
async def test_ocr_tool_successful_extraction() -> None:
    inv_id = str(uuid.uuid4())
    mock_provider = MockOCRProvider(
        mock_text="SEBI Registered VIP Advisory. 100% Guaranteed Profit Daily.",
        mock_confidence=0.98,
    )
    tool = OCRTool(ocr_provider=mock_provider)
    assert tool.name == "ocr_analyzer"

    state = {
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"fake_screenshot_bytes",
    }
    result = await tool.execute(state)

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.type == EvidenceType.OCR_EXTRACTION
    assert ev.status == AnalysisStatus.SUCCESS
    assert ev.confidence == 0.98
    assert "SEBI Registered" in result.output_data["extracted_text"]
    assert "not fraud probability" in ev.description


@pytest.mark.asyncio
async def test_ocr_tool_no_image_in_state() -> None:
    inv_id = str(uuid.uuid4())
    tool = OCRTool(ocr_provider=MockOCRProvider())
    state = {
        "investigation_id": inv_id,
        "input_type": "text",
        "raw_input_text": "text only",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_ocr_tool_empty_text_detected() -> None:
    inv_id = str(uuid.uuid4())
    empty_ocr = MockOCRProvider(mock_text="", mock_status=AnalysisStatus.INSUFFICIENT_EVIDENCE)
    tool = OCRTool(ocr_provider=empty_ocr)
    state = {
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"blank_white_image",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_ocr_tool_unavailable_provider() -> None:
    inv_id = str(uuid.uuid4())
    tool = OCRTool(ocr_provider=UnavailableOCRProvider())
    state = {
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"some_image",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.evidence[0].status == AnalysisStatus.UNAVAILABLE


# =============================================================================
# Audio Transcription Tool Tests
# =============================================================================

@pytest.mark.asyncio
async def test_audio_tool_successful_transcription() -> None:
    inv_id = str(uuid.uuid4())
    mock_provider = MockSTTProvider(
        mock_transcript="Send payment to this UPI id for guaranteed 200% return.",
    )
    tool = AudioTranscriptionTool(stt_provider=mock_provider)
    assert tool.name == "audio_transcriber"

    state = {
        "investigation_id": inv_id,
        "input_type": "audio",
        "audio_bytes": b"fake_wav_bytes",
    }
    result = await tool.execute(state)

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.type == EvidenceType.AUDIO_TRANSCRIPTION
    assert ev.status == AnalysisStatus.SUCCESS
    assert "Send payment to this UPI id" in result.output_data["transcript"]
    assert "NOT fraud probability" in ev.description


@pytest.mark.asyncio
async def test_audio_tool_no_speech() -> None:
    inv_id = str(uuid.uuid4())
    no_speech_provider = MockSTTProvider(
        mock_transcript="", mock_status=AnalysisStatus.INSUFFICIENT_EVIDENCE
    )
    tool = AudioTranscriptionTool(stt_provider=no_speech_provider)
    state = {
        "investigation_id": inv_id,
        "input_type": "audio",
        "audio_bytes": b"silence_bytes",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_audio_tool_unavailable() -> None:
    inv_id = str(uuid.uuid4())
    tool = AudioTranscriptionTool(stt_provider=UnavailableSTTProvider())
    state = {
        "investigation_id": inv_id,
        "input_type": "audio",
        "audio_bytes": b"audio_data",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.evidence[0].status == AnalysisStatus.UNAVAILABLE


# =============================================================================
# Video Analysis Tool Tests
# =============================================================================

@pytest.mark.asyncio
async def test_video_tool_synthetic_video_processing() -> None:
    import cv2
    import numpy as np

    inv_id = str(uuid.uuid4())
    tool = VideoAnalysisTool()
    assert tool.name == "video_analyzer"

    # Create synthetic MP4 video
    p = tempfile.mktemp(suffix=".mp4")
    try:
        out = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 64))
        for _ in range(15):
            frame = np.full((64, 64, 3), 200, dtype=np.uint8)
            out.write(frame)
        out.release()

        with open(p, "rb") as f:
            v_bytes = f.read()

        state = {
            "investigation_id": inv_id,
            "input_type": "video",
            "video_bytes": v_bytes,
        }
        result = await tool.execute(state)

        assert result.status == AnalysisStatus.SUCCESS
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        assert ev.type == EvidenceType.FORENSIC_ARTIFACT
        assert result.output_data["sampled_frame_count"] > 0
    finally:
        if os.path.exists(p):
            os.remove(p)


@pytest.mark.asyncio
async def test_video_tool_no_video_and_invalid() -> None:
    inv_id = str(uuid.uuid4())
    tool = VideoAnalysisTool()

    # No video
    res_none = await tool.execute({"investigation_id": inv_id, "input_type": "text"})
    assert res_none.status == AnalysisStatus.INSUFFICIENT_EVIDENCE

    # Invalid video
    res_inv = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "video",
        "video_bytes": b"corrupt_video_data",
    })
    assert res_inv.status == AnalysisStatus.FAILED
    assert res_inv.evidence[0].status == AnalysisStatus.FAILED


# =============================================================================
# Face Detection Tool Tests
# =============================================================================

@pytest.mark.asyncio
async def test_face_tool_detection_and_no_faces() -> None:
    inv_id = str(uuid.uuid4())
    tool = FaceDetectionTool(face_detector=MockFaceDetectorProvider(mock_face_count=2))
    assert tool.name == "face_detector"

    # Detected faces
    res = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"face_image",
    })
    assert res.status == AnalysisStatus.SUCCESS
    assert res.output_data["face_count"] > 0
    assert res.evidence[0].status == AnalysisStatus.SUCCESS

    # No faces detected -> INSUFFICIENT_EVIDENCE, explicit note: NOT fraud!
    tool_no_face = FaceDetectionTool(face_detector=MockFaceDetectorProvider(mock_face_count=0))
    res_no_face = await tool_no_face.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"scenery_image",
    })
    assert res_no_face.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert "NOT considered evidence of fraud" in res_no_face.evidence[0].description


@pytest.mark.asyncio
async def test_face_tool_unavailable() -> None:
    inv_id = str(uuid.uuid4())
    tool = FaceDetectionTool(face_detector=UnavailableFaceDetectorProvider())
    res = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"image",
    })
    assert res.status == AnalysisStatus.UNAVAILABLE
    assert res.evidence[0].status == AnalysisStatus.UNAVAILABLE


# =============================================================================
# Deepfake Detection Tool Tests
# =============================================================================

@pytest.mark.asyncio
async def test_deepfake_tool_mock_detection_score_and_disclaimer() -> None:
    inv_id = str(uuid.uuid4())
    mock_df = MockDeepfakeProvider(mock_score=0.89, mock_confidence=0.95)
    mock_face = MockFaceDetectorProvider(mock_face_count=1)
    tool = DeepfakeDetectionTool(deepfake_provider=mock_df, face_detector=mock_face)
    assert tool.name == "deepfake_detector"

    res = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"media_bytes",
    })
    assert res.status == AnalysisStatus.SUCCESS
    assert res.output_data["manipulation_score"] == 0.89
    ev = res.evidence[0]
    assert ev.type == EvidenceType.DEEPFAKE_ANALYSIS
    assert ev.severity == SeverityLevel.HIGH  # score >= 0.7
    assert "MODEL SCORE != PROBABILITY OF FRAUD" in ev.description


@pytest.mark.asyncio
async def test_deepfake_tool_missing_weights_failsafe() -> None:
    """Missing weights must produce UNAVAILABLE and never claim authentic or fake=False."""
    inv_id = str(uuid.uuid4())
    unavail_df = MesoNetDeepfakeProvider(weights_path="missing_weights.h5")
    mock_face = MockFaceDetectorProvider(mock_face_count=1)
    tool = DeepfakeDetectionTool(deepfake_provider=unavail_df, face_detector=mock_face)

    res = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"media_bytes",
    })
    assert res.status == AnalysisStatus.UNAVAILABLE
    assert res.output_data["manipulation_score"] is None
    ev = res.evidence[0]
    assert ev.status == AnalysisStatus.UNAVAILABLE
    assert "Deepfake model weights unavailable" in ev.description
    assert "NOT considered evidence of authenticity" in ev.description
    assert ev.metadata.get("fake") is not False


@pytest.mark.asyncio
async def test_deepfake_tool_no_face_detected() -> None:
    inv_id = str(uuid.uuid4())
    mock_df = MockDeepfakeProvider(mock_score=0.8)
    no_faces = MockFaceDetectorProvider(mock_face_count=0)
    tool = DeepfakeDetectionTool(deepfake_provider=mock_df, face_detector=no_faces)

    res = await tool.execute({
        "investigation_id": inv_id,
        "input_type": "image",
        "image_bytes": b"tree_image",
    })
    assert res.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert res.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert "No face regions detected" in res.evidence[0].description


# =============================================================================
# Evidence Serialization Tests
# =============================================================================

def test_multimodal_evidence_serialization() -> None:
    inv_id = uuid.uuid4()
    ev = EvidenceContract(
        investigation_id=inv_id,
        type=EvidenceType.DEEPFAKE_ANALYSIS,
        category="deepfake_analysis",
        severity=SeverityLevel.HIGH,
        confidence=0.92,
        description="MesoNet manipulation score: 0.88 across 1 face(s). Disclaimer: MODEL SCORE != PROBABILITY OF FRAUD.",
        source_type="model",
        source_name="mesonet_meso4",
        source_version="1.0.0",
        status=AnalysisStatus.SUCCESS,
        raw_payload={"manipulation_score": 0.88, "confidence": 0.92},
        metadata={"model": "Meso4", "faces_analyzed": 1},
    )

    ev_dict = ev.model_dump(mode="json")
    assert ev_dict["type"] == "deepfake_analysis"
    assert ev_dict["status"] == "SUCCESS"
    assert ev_dict["confidence"] == 0.92
    assert ev_dict["source_name"] == "mesonet_meso4"
    assert ev_dict["source_version"] == "1.0.0"
    assert ev_dict["raw_payload"]["manipulation_score"] == 0.88

    # Re-deserialize to verify round-trip integrity
    ev_reloaded = EvidenceContract.model_validate(ev_dict)
    assert ev_reloaded.investigation_id == inv_id
    assert ev_reloaded.confidence == 0.92
