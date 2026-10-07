from __future__ import annotations

import io
import uuid
import zipfile

import pytest

from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.apk_tool import APKIntelligenceTool


def make_apk() -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"fake-manifest")
        archive.writestr("classes.dex", b"fake-dex")

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
