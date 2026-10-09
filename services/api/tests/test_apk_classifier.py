from __future__ import annotations

import pytest

from app.contracts.status import AnalysisStatus
from app.providers.apk_classifier import (
    APKClassifier,
    FEATURE_NAMES,
)


def _features() -> dict[str, int | float]:
    return {
        name: index + 1
        for index, name in enumerate(FEATURE_NAMES)
    }


@pytest.mark.asyncio
async def test_missing_model_is_unavailable(monkeypatch):
    monkeypatch.delenv("VERA_APK_XGB_MODEL_PATH", raising=False)

    classifier = APKClassifier()

    result = await classifier.classify(_features())

    assert result["status"] == AnalysisStatus.UNAVAILABLE.value
    assert result["prediction"] is None
    assert result["model_score"] is None


@pytest.mark.asyncio
async def test_missing_feature_is_failed(tmp_path):
    classifier = APKClassifier(
        model_path=str(tmp_path / "model.json")
    )

    features = _features()
    features.pop("dex_count")

    result = await classifier.classify(features)

    assert result["status"] == AnalysisStatus.FAILED.value
    assert "dex_count" in result["error"]


@pytest.mark.asyncio
async def test_extra_feature_is_failed(tmp_path):
    classifier = APKClassifier(
        model_path=str(tmp_path / "model.json")
    )

    features = _features()
    features["unexpected_feature"] = 1

    result = await classifier.classify(features)

    assert result["status"] == AnalysisStatus.FAILED.value
    assert "unexpected_feature" in result["error"]


@pytest.mark.asyncio
async def test_none_feature_is_failed(tmp_path):
    classifier = APKClassifier(
        model_path=str(tmp_path / "model.json")
    )

    features = _features()
    features["target_sdk"] = None

    result = await classifier.classify(features)

    assert result["status"] == AnalysisStatus.FAILED.value
    assert "target_sdk" in result["error"]


@pytest.mark.asyncio
async def test_nonexistent_model_is_unavailable(tmp_path):
    classifier = APKClassifier(
        model_path=str(tmp_path / "missing.json")
    )

    result = await classifier.classify(_features())

    assert result["status"] == AnalysisStatus.UNAVAILABLE.value
    assert result["prediction"] is None