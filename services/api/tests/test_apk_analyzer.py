from pathlib import Path
from zipfile import ZipFile

from app.providers.apk_analyzer import APKAnalyzerProvider


def create_valid_apk(path: Path) -> None:
    with ZipFile(path, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"manifest")
        zf.writestr("classes.dex", b"dex")
        zf.writestr("resources.arsc", b"resources")
        zf.writestr("META-INF/CERT.RSA", b"certificate")


async def test_analyze_valid_apk(tmp_path):
    apk_path = tmp_path / "sample.apk"
    create_valid_apk(apk_path)

    result = await APKAnalyzerProvider().analyze(apk_path)

    assert result["status"] == "SUCCESS"
    assert result["valid"] is True
    assert result["file_name"] == "sample.apk"
    assert result["file_size_bytes"] > 0
    assert len(result["sha256"]) == 64
    assert result["archive"]["member_count"] == 4
    assert result["archive"]["manifest_present"] is True
    assert result["archive"]["classes_dex_count"] == 1
    assert result["archive"]["has_resources"] is True
    assert result["archive"]["has_certificate_directory"] is True
    assert result["archive"]["has_native_libraries"] is False
    assert result["archive"]["native_library_count"] == 0


async def test_analyze_missing_file(tmp_path):
    result = await APKAnalyzerProvider().analyze(tmp_path / "missing.apk")

    assert result["status"] == "FAILED"
    assert result["valid"] is False


async def test_analyze_directory(tmp_path):
    result = await APKAnalyzerProvider().analyze(tmp_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


async def test_analyze_empty_file(tmp_path):
    apk_path = tmp_path / "empty.apk"
    apk_path.write_bytes(b"")

    result = await APKAnalyzerProvider().analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


async def test_analyze_invalid_archive(tmp_path):
    apk_path = tmp_path / "invalid.apk"
    apk_path.write_bytes(b"not an apk")

    result = await APKAnalyzerProvider().analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


async def test_analyze_size_limit(tmp_path):
    apk_path = tmp_path / "large.apk"
    apk_path.write_bytes(b"x")

    provider = APKAnalyzerProvider()
    provider.max_file_size_bytes = 0

    result = await provider.analyze(apk_path)

    assert result["status"] == "FAILED"
    assert result["valid"] is False


async def test_analyze_sha256_is_deterministic(tmp_path):
    apk_path = tmp_path / "sample.apk"
    create_valid_apk(apk_path)

    provider = APKAnalyzerProvider()

    first = await provider.analyze(apk_path)
    second = await provider.analyze(apk_path)

    assert first["sha256"] == second["sha256"]


async def test_analyze_detects_native_libraries(tmp_path):
    apk_path = tmp_path / "native.apk"

    with ZipFile(apk_path, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"manifest")
        zf.writestr("classes.dex", b"dex")
        zf.writestr("lib/arm64-v8a/libexample.so", b"native")

    result = await APKAnalyzerProvider().analyze(apk_path)

    assert result["status"] == "SUCCESS"
    assert result["archive"]["native_library_count"] == 1
    assert result["archive"]["has_native_libraries"] is True
