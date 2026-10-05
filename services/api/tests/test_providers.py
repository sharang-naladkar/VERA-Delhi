"""Tests for Provider Interfaces and Fail-Safe Unavailable Fallbacks."""

import uuid

import pytest

from app.contracts.status import AnalysisStatus
from app.providers.apk_classifier import UnavailableAPKClassifier
from app.providers.deepfake import UnavailableDeepfakeProvider
from app.providers.embedding import UnavailableEmbeddingProvider
from app.providers.llm import UnavailableLLMProvider
from app.providers.ocr import UnavailableOCRProvider
from app.providers.stt import UnavailableSTTProvider
from app.providers.url_classifier import UnavailableURLClassifier


@pytest.mark.asyncio
async def test_unavailable_llm_provider() -> None:
    provider = UnavailableLLMProvider(model_name="qwen3:32b")
    assert provider.is_available is False
    assert "unavailable_llm" in provider.provider_name

    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    chat_resp = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert chat_resp["status"] == AnalysisStatus.UNAVAILABLE.value
    assert chat_resp["response"] is None

    claim_resp = await provider.analyze_fraud_claim(
        investigation_id=uuid.uuid4(),
        claim_text="Guaranteed 100% daily returns",
    )
    assert claim_resp["status"] == AnalysisStatus.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_unavailable_ocr_provider() -> None:
    provider = UnavailableOCRProvider()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    res = await provider.extract_text(investigation_id=uuid.uuid4(), image_bytes=b"fake")
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["text"] == ""


@pytest.mark.asyncio
async def test_unavailable_stt_provider() -> None:
    provider = UnavailableSTTProvider()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    res = await provider.transcribe(investigation_id=uuid.uuid4(), audio_bytes=b"fake")
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["transcript"] == ""


@pytest.mark.asyncio
async def test_unavailable_deepfake_provider() -> None:
    provider = UnavailableDeepfakeProvider()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    res = await provider.analyze_media(
        investigation_id=uuid.uuid4(), media_bytes=b"fake", media_type="video"
    )
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["manipulation_score"] is None


@pytest.mark.asyncio
async def test_unavailable_url_classifier() -> None:
    provider = UnavailableURLClassifier()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    res = await provider.classify_url(
        investigation_id=uuid.uuid4(), url="https://fake-sebi-invest.com"
    )
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["risk_score"] is None


@pytest.mark.asyncio
async def test_unavailable_apk_classifier() -> None:
    provider = UnavailableAPKClassifier()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    res = await provider.analyze_apk(investigation_id=uuid.uuid4(), apk_bytes=b"fake")
    assert res["status"] == AnalysisStatus.UNAVAILABLE.value
    assert res["risk_score"] is None


@pytest.mark.asyncio
async def test_unavailable_embedding_provider() -> None:
    provider = UnavailableEmbeddingProvider()
    assert provider.is_available is False
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    with pytest.raises(NotImplementedError):
        await provider.embed_texts(["sample text"])
