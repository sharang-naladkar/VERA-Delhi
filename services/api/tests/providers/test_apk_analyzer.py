from __future__ import annotations

import io
import zipfile

from app.providers.apk_analyzer import APKAnalyzer


def make_apk(
    *,
    manifest: bool = True,
    dex_files: tuple[str, ...] = ("classes.dex",),
) -> bytes:
    """Create a minimal ZIP-shaped APK fixture."""

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if manifest:
            archive.writestr(
                "AndroidManifest.xml",
                b"fake-manifest",
            )

        for dex_file in dex_files:
            archive.writestr(
                dex_file,
                b"fake-dex",
            )

    return buffer.getvalue()


def test_valid_apk_is_detected() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(
        make_apk(),
        filename="sample.apk",
    )

    assert result["is_valid"] is True
    assert result["filename"] == "sample.apk"
    assert result["has_android_manifest"] is True
    assert result["dex_count"] == 1
    assert result["dex_files"] == ["classes.dex"]
    assert result["size_bytes"] > 0
    assert len(result["sha256"]) == 64


def test_multiple_dex_files_are_detected() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(
        make_apk(
            dex_files=(
                "classes.dex",
                "classes2.dex",
                "classes3.dex",
            )
        )
    )

    assert result["is_valid"] is True
    assert result["dex_count"] == 3
    assert result["dex_files"] == [
        "classes.dex",
        "classes2.dex",
        "classes3.dex",
    ]


def test_missing_manifest_is_invalid() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(
        make_apk(manifest=False),
    )

    assert result["is_valid"] is False
    assert result["has_android_manifest"] is False
    assert result["dex_count"] == 1
    assert "AndroidManifest.xml is missing." in result["warnings"]


def test_missing_dex_is_invalid() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(
        make_apk(dex_files=()),
    )

    assert result["is_valid"] is False
    assert result["has_android_manifest"] is True
    assert result["dex_count"] == 0
    assert "No classes*.dex file was found." in result["warnings"]


def test_empty_input_is_rejected() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(b"")

    assert result["is_valid"] is False
    assert result["size_bytes"] == 0
    assert "APK input is empty." in result["warnings"]


def test_non_zip_input_is_rejected() -> None:
    analyzer = APKAnalyzer()

    result = analyzer.analyze(
        b"this is not an apk",
        filename="fake.apk",
    )

    assert result["is_valid"] is False
    assert "APK does not start with a ZIP archive signature." in result["warnings"]


def test_sha256_is_deterministic() -> None:
    analyzer = APKAnalyzer()
    apk_bytes = make_apk()

    first = analyzer.analyze(apk_bytes)
    second = analyzer.analyze(apk_bytes)

    assert first["sha256"] == second["sha256"]


def test_native_libraries_are_detected() -> None:
    analyzer = APKAnalyzer()

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"fake-manifest")
        archive.writestr("classes.dex", b"fake-dex")
        archive.writestr("lib/arm64-v8a/libnative.so", b"fake-so")
        archive.writestr("lib/armeabi-v7a/liblegacy.so", b"fake-so")

    result = analyzer.analyze(buffer.getvalue())

    assert result["is_valid"] is True
    assert result["native_library_count"] == 2
    assert result["native_libraries"] == [
        "lib/arm64-v8a/libnative.so",
        "lib/armeabi-v7a/liblegacy.so",
    ]


def test_suspicious_archive_entries_are_flagged() -> None:
    analyzer = APKAnalyzer()

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"fake-manifest")
        archive.writestr("classes.dex", b"fake-dex")
        archive.writestr("../payload", b"unexpected")

    result = analyzer.analyze(buffer.getvalue())

    assert result["is_valid"] is True
    assert "../payload" in result["suspicious_entries"]
