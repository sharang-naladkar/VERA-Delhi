from __future__ import annotations

import io
import uuid
import zipfile

import pytest

from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.apk_tool import APKIntelligenceTool


def make_apk(
    dex_contents: tuple[bytes, ...] = (b"fake-dex",),
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "AndroidManifest.xml",
            b"fake-manifest",
        )

        for index, content in enumerate(dex_contents, start=1):
            name = (
                "classes.dex"
                if index == 1
                else f"classes{index}.dex"
            )
            archive.writestr(name, content)

    return buffer.getvalue()


@pytest.mark.asyncio
async def test_valid_apk_returns_success() -> None:
    investigation_id = uuid.uuid4()
    tool = APKIntelligenceTool()

    result = await tool.execute(
        {
            "investigation_id": str(investigation_id),
            "apk_bytes": make_apk(),
            "filename": "sample.apk",
        }
    )

    assert result.tool_name == "apk_intelligence"
    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1

    evidence = result.evidence[0]

    assert evidence.type == EvidenceType.APK_ANALYSIS
    assert evidence.status == AnalysisStatus.SUCCESS
    assert evidence.investigation_id == investigation_id
    assert evidence.severity == SeverityLevel.LOW
    assert evidence.confidence == 1.0
    assert result.output_data["is_valid"] is True
    assert "static_analysis" in result.output_data


@pytest.mark.asyncio
async def test_static_urls_are_returned() -> None:
    tool = APKIntelligenceTool()

    dex = (
        b"com.example.app\x00"
        b"https://example.com/login\x00"
    )

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
            "apk_bytes": make_apk((dex,)),
        }
    )

    static = result.output_data["static_analysis"]

    assert result.status == AnalysisStatus.SUCCESS
    assert "https://example.com/login" in static["urls"]
    assert static["string_count"] >= 1


@pytest.mark.asyncio
async def test_static_indicators_raise_severity() -> None:
    tool = APKIntelligenceTool()

    dex = (
        b"https://example.com/login\x00"
        b"192.168.1.10\x00"
        b"Landroid/telephony/SmsManager;\x00"
        b"Ldalvik/system/DexClassLoader;\x00"
    )

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
            "apk_bytes": make_apk((dex,)),
        }
    )

    static = result.output_data["static_analysis"]

    assert result.status == AnalysisStatus.SUCCESS
    assert result.evidence[0].severity == SeverityLevel.HIGH
    assert "sms_api" in static["api_indicators"]
    assert "dynamic_code_loading" in static["api_indicators"]


@pytest.mark.asyncio
async def test_missing_apk_returns_insufficient_evidence() -> None:
    tool = APKIntelligenceTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
        }
    )

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert len(result.evidence) == 1
    assert result.evidence[0].type == EvidenceType.APK_ANALYSIS
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].metadata["is_skipped"] is True


@pytest.mark.asyncio
async def test_invalid_apk_returns_failed() -> None:
    tool = APKIntelligenceTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
            "apk_bytes": b"not-an-apk",
            "filename": "fake.apk",
        }
    )

    assert result.status == AnalysisStatus.FAILED
    assert len(result.evidence) == 1
    assert result.evidence[0].type == EvidenceType.APK_ANALYSIS
    assert result.evidence[0].status == AnalysisStatus.FAILED
    assert result.output_data["is_valid"] is False


@pytest.mark.asyncio
async def test_media_bytes_are_supported() -> None:
    tool = APKIntelligenceTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
            "media_bytes": make_apk(),
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert result.output_data["is_valid"] is True


@pytest.mark.asyncio
async def test_input_id_is_preserved() -> None:
    input_id = uuid.uuid4()
    tool = APKIntelligenceTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid.uuid4()),
            "input_id": str(input_id),
            "apk_bytes": make_apk(),
        }
    )

    assert result.evidence[0].input_id == input_id
