"""Deterministic static intelligence extraction for Android APKs."""

from __future__ import annotations

import io
import ipaddress
import re
import zipfile
from typing import Any
from urllib.parse import urlsplit


class APKStaticAnalyzer:
    """Extract static indicators without executing APK code."""

    ASCII_STRING_RE = re.compile(rb"[\x20-\x7e]{4,}")

    UTF16_STRING_RE = re.compile(
        rb"(?:[\x20-\x7e]\x00){4,}"
    )

    URL_RE = re.compile(
        rb"https?://[^\x00-\x20\"'<>]{4,}"
    )

    IPV4_RE = re.compile(
        rb"(?<![\d.])"
        rb"(?:\d{1,3}\.){3}\d{1,3}"
        rb"(?![\d.])"
    )

    API_INDICATORS: tuple[tuple[str, str], ...] = (
        (r"Landroid/telephony/SmsManager;", "sms_api"),
        (r"Landroid/telephony/TelephonyManager;", "telephony_api"),
        (r"Landroid/location/LocationManager;", "location_api"),
        (r"Landroid/net/ConnectivityManager;", "network_api"),
        (r"Landroid/webkit/WebView;", "webview_api"),
        (r"Landroid/accessibilityservice/", "accessibility_api"),
        (r"Landroid/app/admin/DeviceAdmin", "device_admin_api"),
        (r"Ljava/net/HttpURLConnection;", "http_api"),
        (r"Ljava/net/URL;", "url_api"),
        (r"Ljavax/net/ssl/", "tls_api"),
        (r"Ljava/lang/Runtime;", "runtime_api"),
        (r"Ldalvik/system/DexClassLoader;", "dynamic_code_loading"),
        (r"Ldalvik/system/PathClassLoader;", "dynamic_class_loading"),
        (r"Landroid/content/pm/PackageManager;", "package_manager_api"),
        (r"Landroid/content/ClipboardManager;", "clipboard_api"),
        (r"Landroid/hardware/Camera", "camera_api"),
        (r"Landroid/media/AudioRecord;", "audio_record_api"),
        (r"Landroid/os/Build;", "device_information_api"),
    )

    OBFUSCATION_PATTERNS: tuple[tuple[str, str], ...] = (
        (r"L[a-z]/[a-z];", "short_class_reference"),
        (r"L[a-z]{1,2}/[a-z]{1,3}/", "short_package_reference"),
        (r"\\x[0-9a-fA-F]{2}", "hex_escape_sequence"),
        (r"base64", "base64_reference"),
        (r"xor", "xor_reference"),
    )

    def analyze(self, apk_bytes: bytes) -> dict[str, Any]:
        """Extract static indicators from APK archive contents."""

        result: dict[str, Any] = {
            "dex_files": [],
            "dex_count": 0,
            "string_count": 0,
            "strings": [],
            "urls": [],
            "ip_addresses": [],
            "api_indicators": [],
            "obfuscation_indicators": [],
            "warnings": [],
        }

        if not apk_bytes:
            result["warnings"].append("APK input is empty.")
            return result

        try:
            with zipfile.ZipFile(io.BytesIO(apk_bytes)) as archive:
                names = [
                    name.replace("\\", "/")
                    for name in archive.namelist()
                ]

                dex_names = sorted(
                    name
                    for name in names
                    if re.fullmatch(r"classes\d*\.dex", name)
                )

                result["dex_files"] = dex_names
                result["dex_count"] = len(dex_names)

                all_strings: set[str] = set()
                all_urls: set[str] = set()
                all_ips: set[str] = set()
                api_hits: set[str] = set()
                obfuscation_hits: set[str] = set()

                for dex_name in dex_names:
                    dex_bytes = archive.read(dex_name)

                    strings = self._extract_strings(dex_bytes)
                    all_strings.update(strings)

                    all_urls.update(
                        self._extract_urls(dex_bytes)
                    )
                    all_ips.update(
                        self._extract_ips(dex_bytes)
                    )

                    api_hits.update(
                        self._detect_api_indicators(dex_bytes)
                    )

                    obfuscation_hits.update(
                        self._detect_obfuscation(
                            strings,
                            dex_bytes,
                        )
                    )

                result["string_count"] = len(all_strings)
                result["strings"] = sorted(all_strings)[:500]
                result["urls"] = sorted(all_urls)[:200]
                result["ip_addresses"] = sorted(all_ips)
                result["api_indicators"] = sorted(api_hits)
                result["obfuscation_indicators"] = sorted(
                    obfuscation_hits
                )

                if not dex_names:
                    result["warnings"].append(
                        "No classes*.dex file was found."
                    )

        except zipfile.BadZipFile:
            result["warnings"].append(
                "APK is not a valid ZIP archive."
            )
        except (OSError, ValueError, RuntimeError) as exc:
            result["warnings"].append(
                f"Static APK inspection failed: "
                f"{type(exc).__name__}: {exc}"
            )

        return result

    @classmethod
    def _extract_strings(cls, data: bytes) -> set[str]:
        strings: set[str] = set()

        for match in cls.ASCII_STRING_RE.finditer(data):
            try:
                value = match.group().decode("ascii")
            except UnicodeDecodeError:
                continue
            strings.add(value)

        for match in cls.UTF16_STRING_RE.finditer(data):
            try:
                value = match.group().decode("utf-16le")
            except UnicodeDecodeError:
                continue
            if len(value) >= 4:
                strings.add(value)

        return strings

    @classmethod
    def _extract_urls(cls, data: bytes) -> set[str]:
        urls: set[str] = set()

        for match in cls.URL_RE.finditer(data):
            try:
                value = match.group().decode("ascii")
            except UnicodeDecodeError:
                continue

            value = value.rstrip(".,;)]}")
            try:
                parsed = urlsplit(value)
            except ValueError:
                continue

            if parsed.scheme in {"http", "https"} and parsed.netloc:
                urls.add(value)

        return urls

    @classmethod
    def _extract_ips(cls, data: bytes) -> set[str]:
        ips: set[str] = set()

        for match in cls.IPV4_RE.finditer(data):
            try:
                candidate = match.group().decode("ascii")
                ipaddress.IPv4Address(candidate)
            except (UnicodeDecodeError, ValueError):
                continue

            ips.add(candidate)

        return ips

    @classmethod
    def _detect_api_indicators(cls, data: bytes) -> set[str]:
        text = data.decode("latin-1", errors="ignore")
        hits: set[str] = set()

        for pattern, indicator in cls.API_INDICATORS:
            if re.search(pattern, text):
                hits.add(indicator)

        return hits

    @classmethod
    def _detect_obfuscation(
        cls,
        strings: set[str],
        data: bytes,
    ) -> set[str]:
        text = data.decode("latin-1", errors="ignore")
        hits: set[str] = set()

        for pattern, indicator in cls.OBFUSCATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                hits.add(indicator)

        short_strings = sum(
            1
            for value in strings
            if 4 <= len(value) <= 6
            and all(
                character.isalnum() or character in "_$"
                for character in value
            )
        )

        if len(strings) >= 20:
            short_string_ratio = short_strings / len(strings)
            if short_string_ratio >= 0.60:
                hits.add("high_short_string_ratio")

        return hits
