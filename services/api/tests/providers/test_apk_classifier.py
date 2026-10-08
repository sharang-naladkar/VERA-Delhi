from __future__ import annotations

import asyncio
import io
import zipfile
from uuid import uuid4

from app.contracts.status import AnalysisStatus
from app.providers.apk_classifier import (
    DrebinAPKClassifier,
    UnavailableAPKClassifier,
)


def make_apk(*dex_contents: bytes) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "AndroidManifest.xml",
            b"fake-manifest",
        )

        for index, content in enumerate(dex_contents, start=1):
            name = "classes.dex" if index == 1 else f"classes{index}.dex"
            archive.writestr(name, content)

    return buffer.getvalue()


def test_empty_apk_returns_insufficient_evidence() -> None:
    classifier = DrebinAPKClassifier()

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            b"",
        )
    )

    assert result["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value
    assert result["risk_score"] is None


def test_low_risk_apk_gets_low_score() -> None:
    classifier = DrebinAPKClassifier()

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            make_apk(
                b"hello world "
                b"com.example.app "
                b"ordinary application content"
            ),
        )
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["risk_score"] < 0.40
    assert result["risk_level"] == "LOW"


def test_sensitive_features_increase_risk() -> None:
    classifier = DrebinAPKClassifier()

    dex = (
        b"Landroid/telephony/SmsManager;"
        b"Landroid/telephony/TelephonyManager;"
        b"Landroid/accessibilityservice/AccessibilityService;"
        b"Ldalvik/system/DexClassLoader;"
        b"base64 "
        b"xor "
        b"Runtime.exec "
    )

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            make_apk(dex),
        )
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["risk_score"] >= 0.40
    assert result["risk_level"] in {"MEDIUM", "HIGH"}
    assert result["matched_features"]


def test_feature_vector_is_exposed() -> None:
    classifier = DrebinAPKClassifier()

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            make_apk(
                b"https://example.com/login "
                b"com.example.application"
            ),
        )
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["feature_names"]
    assert result["feature_vector"]
    assert len(result["feature_names"]) == len(result["feature_vector"])


def test_matched_features_are_sorted_by_contribution() -> None:
    classifier = DrebinAPKClassifier()

    dex = (
        b"Landroid/telephony/SmsManager;"
        b"Landroid/accessibilityservice/AccessibilityService;"
        b"Ldalvik/system/DexClassLoader;"
        b"base64 "
        b"xor "
    )

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            make_apk(dex),
        )
    )

    contributions = [
        item["contribution"]
        for item in result["matched_features"]
    ]

    assert contributions == sorted(contributions, reverse=True)


def test_invalid_apk_returns_failed() -> None:
    classifier = DrebinAPKClassifier()

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            b"not-an-apk",
        )
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["risk_score"] is None


def test_unavailable_classifier_contract() -> None:
    classifier = UnavailableAPKClassifier()

    result = asyncio.run(
        classifier.analyze_apk(
            uuid4(),
            b"fake-apk",
        )
    )

    assert result["status"] == AnalysisStatus.UNAVAILABLE.value
    assert result["risk_score"] is None
