"""Integration tests for VERA Multimodal Investigation flow and API Startup Safety."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.status import AnalysisStatus
from app.investigator.orchestrator import VERAInvestigator
from app.investigator.tools.registry import create_default_registry
from app.main import app
from app.providers.deepfake import MockDeepfakeProvider
from app.providers.face_detector import MockFaceDetectorProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.ocr import MockOCRProvider


@pytest.mark.asyncio
async def test_multimodal_investigator_image_flow() -> None:
    """Verifies that an image input triggers multimodal analyzers within LangGraph."""
    inv_id = uuid.uuid4()
    mock_llm = MockLLMProvider(model_name="mock-qwen3")
    mock_ocr = MockOCRProvider(mock_text="Claim: 100% Guaranteed Return on VIP WhatsApp group.")
    mock_face = MockFaceDetectorProvider(mock_face_count=1)
    mock_df = MockDeepfakeProvider(mock_score=0.85, mock_confidence=0.90)

    registry = create_default_registry(
        llm_provider=mock_llm,
        ocr_provider=mock_ocr,
        face_detector=mock_face,
        deepfake_provider=mock_df,
    )

    investigator = VERAInvestigator(
        llm_provider=mock_llm,
        tool_registry=registry,
    )

    final_state = await investigator.run_investigation(
        investigation_id=inv_id,
        raw_input_text="Suspicious WhatsApp screenshot claiming guaranteed returns",
        input_type="image",
        image_bytes=b"fake_image_bytes_for_testing",
    )

    assert final_state.status in (AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL, AnalysisStatus.PENDING)
    assert len(final_state.evidence) > 0

    # Verify that multimodal evidence types were produced
    evidence_types = [ev["type"] for ev in final_state.evidence]
    assert "ocr_extraction" in evidence_types
    assert "deepfake_analysis" in evidence_types

    # Verify tool results logged
    executed_tools = [tr["tool_name"] for tr in final_state.tool_results]
    assert "ocr_analyzer" in executed_tools
    assert "face_detector" in executed_tools
    assert "deepfake_detector" in executed_tools


@pytest.mark.asyncio
async def test_text_only_investigator_skips_multimodal_tools_cleanly() -> None:
    """Verifies that text-only investigation does not execute nonexistent media analyzers."""
    inv_id = uuid.uuid4()
    mock_llm = MockLLMProvider(model_name="mock-qwen3")
    registry = create_default_registry(llm_provider=mock_llm)
    investigator = VERAInvestigator(llm_provider=mock_llm, tool_registry=registry)

    final_state = await investigator.run_investigation(
        investigation_id=inv_id,
        raw_input_text="Pure text investigation about an unauthorized Telegram channel",
        input_type="text",
    )

    assert final_state.status in (AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL)
    evidence_types = [ev["type"] for ev in final_state.evidence]

    # Multimodal media analyzers MUST NOT have executed for pure text input
    assert "ocr_extraction" not in evidence_types
    assert "deepfake_analysis" not in evidence_types
    assert "audio_transcription" not in evidence_types


@pytest.mark.asyncio
async def test_api_startup_and_health_without_multimodal_weights() -> None:
    """Verifies that the FastAPI application starts cleanly without multimodal weights or GPUs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Liveness check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "ok"

        # Readiness check (Postgres/Redis/MinIO mock)
        readiness_resp = await client.get("/health/ready")
        assert readiness_resp.status_code in (200, 503)
        readiness_data = readiness_resp.json()
        assert "services" in readiness_data
