from __future__ import annotations

import io
import zipfile

from app.providers.apk_static_analyzer import APKStaticAnalyzer


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


def test_extracts_strings_from_dex() -> None:
    analyzer = APKStaticAnalyzer()

    dex = (
        b"\x00"
        b"https://example.com/api/login"
        b"\x00"
        b"com.example.investment"
        b"\x00"
    )

    result = analyzer.analyze(make_apk(dex))

    assert result["dex_count"] == 1
    assert "https://example.com/api/login" in result["strings"]
    assert "com.example.investment" in result["strings"]


def test_extracts_urls() -> None:
    analyzer = APKStaticAnalyzer()

    dex = (
        b"\x00https://example.com/login\x00"
        b"http://evil.example/pay\x00"
    )

    result = analyzer.analyze(make_apk(dex))

    assert result["urls"] == [
        "http://evil.example/pay",
        "https://example.com/login",
    ]


def test_extracts_valid_ipv4_addresses() -> None:
    analyzer = APKStaticAnalyzer()

    dex = (
        b"\x00192.168.1.10\x00"
        b"\x008.8.8.8\x00"
        b"\x00999.999.999.999\x00"
    )

    result = analyzer.analyze(make_apk(dex))

    assert "192.168.1.10" in result["ip_addresses"]
    assert "8.8.8.8" in result["ip_addresses"]
    assert "999.999.999.999" not in result["ip_addresses"]


def test_detects_android_api_indicators() -> None:
    analyzer = APKStaticAnalyzer()

    dex = (
        b"Landroid/telephony/SmsManager;"
        b"Landroid/webkit/WebView;"
        b"Ldalvik/system/DexClassLoader;"
    )

    result = analyzer.analyze(make_apk(dex))

    assert "sms_api" in result["api_indicators"]
    assert "webview_api" in result["api_indicators"]
    assert "dynamic_code_loading" in result["api_indicators"]


def test_detects_obfuscation_indicators() -> None:
    analyzer = APKStaticAnalyzer()

    dex = (
        b"Lx/a;"
        b"Lx/a/b/"
        b"base64"
        b"xor"
    )

    result = analyzer.analyze(make_apk(dex))

    assert "short_class_reference" in result["obfuscation_indicators"]
    assert "short_package_reference" in result["obfuscation_indicators"]
    assert "base64_reference" in result["obfuscation_indicators"]
    assert "xor_reference" in result["obfuscation_indicators"]


def test_multiple_dex_files_are_analyzed() -> None:
    analyzer = APKStaticAnalyzer()

    result = analyzer.analyze(
        make_apk(
            b"https://one.example",
            b"https://two.example",
        )
    )

    assert result["dex_count"] == 2
    assert "https://one.example" in result["urls"]
    assert "https://two.example" in result["urls"]


def test_empty_input_returns_warning() -> None:
    analyzer = APKStaticAnalyzer()

    result = analyzer.analyze(b"")

    assert result["dex_count"] == 0
    assert result["strings"] == []
    assert "APK input is empty." in result["warnings"]


def test_invalid_zip_returns_warning() -> None:
    analyzer = APKStaticAnalyzer()

    result = analyzer.analyze(b"not-an-apk")

    assert result["dex_count"] == 0
    assert result["urls"] == []
    assert "APK is not a valid ZIP archive." in result["warnings"]
