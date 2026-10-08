"""Tests for APK foundation analysis."""

from pathlib import Path
from zipfile import ZipFile

import pytest

from app.providers.apk_analyzer import APKAnalyzerProvider


@pytest.fixture
def provider() -> APKAnalyzerProvider:
    return APKAnalyzerProvider(max_file_size_bytes=1024 * 1024)


@pytest.mark.asyncio
async def test_apk_analyzer_valid_apk(provider: APKAnalyzerProvider, tmp_path: Path) -> None:
    apk_path = tmp_path / "sample.apk"

    with ZipFile(apk_path, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"manifest")
        archive.writestr("classes.dex", b"dex")
        archive.writestr("resources.arsc", b"resources")
        archive.writestr("META-INF/CERT.RSA", b"certificate")

    result = await provider.analyze(apk_path)

    assert result["status"] == "SUCCESS"
    assert result["valid"] is True
    assert len(result["sha256"]) == 64
    assert result["archive"]["member_count"] == 4
    assert result["archive"]["manifest_present"] is True
    assert result["archive"]["classes_dex_count"] == 1
    assert result["archive"]["has_resources"] is True
    assert result["archive"]["has_certificate_directory"] is True


@pytest.mark.asyncio
async def test_apk_analyzer_missing_file(
    provider: APKAnalyzerProvider,
    tmp_path: Path,
) -> None:
    result = await provider.analyze(tmp_path / "missing.apk")

    assert result["status"] == "FAILED"
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_apk_analyzer_rejects_directory(
    provider: APKAnalyzerProvider,
    tmp_path: Path,
) -> None:
    result = await provider.analyze(tmp_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_apk_analyzer_rejects_empty_file(
    provider: APKAnalyzerProvider,
    tmp_path: Path,
) -> None:
    apk_path = tmp_path / "empty.apk"
    apk_path.touch()

    result = await provider.analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_apk_analyzer_rejects_invalid_archive(
    provider: APKAnalyzerProvider,
    tmp_path: Path,
) -> None:
    apk_path = tmp_path / "invalid.apk"
    apk_path.write_bytes(b"not an apk")

    result = await provider.analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_apk_analyzer_enforces_size_limit(tmp_path: Path) -> None:
    provider = APKAnalyzerProvider(max_file_size_bytes=4)
    apk_path = tmp_path / "large.apk"
    apk_path.write_bytes(b"12345")

    result = await provider.analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False
    assert "maximum allowed size" in result["error"]


@pytest.mark.asyncio
async def test_apk_analyzer_sha256_is_deterministic(
    provider: APKAnalyzerProvider,
    tmp_path: Path,
) -> None:
    apk_path = tmp_path / "sample.apk"

    with ZipFile(apk_path, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"manifest")

    first = await provider.analyze(apk_path)
    second = await provider.analyze(apk_path)

    assert first["sha256"] == second["sha256"]
