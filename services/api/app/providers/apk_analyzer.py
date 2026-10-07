"""Deterministic APK structural analyzer.

This module performs safe, dependency-free APK inspection.
It does not execute APK code and does not make a malware verdict.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from typing import Any


class APKAnalyzer:
    """Analyze basic structural properties of an Android APK."""

    APK_MAGIC = b"PK"

    def analyze(
        self,
        apk_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Analyze an APK without executing its contents."""

        result: dict[str, Any] = {
            "is_valid": False,
            "filename": filename,
            "size_bytes": len(apk_bytes),
            "sha256": hashlib.sha256(apk_bytes).hexdigest(),
            "has_android_manifest": False,
            "dex_files": [],
            "dex_count": 0,
            "native_libraries": [],
            "native_library_count": 0,
            "suspicious_entries": [],
            "warnings": [],
        }

        if not apk_bytes:
            result["warnings"].append("APK input is empty.")
            return result

        if not apk_bytes.startswith(self.APK_MAGIC):
            result["warnings"].append(
                "APK does not start with a ZIP archive signature."
            )
            return result

        try:
            with zipfile.ZipFile(io.BytesIO(apk_bytes)) as archive:
                bad_file = archive.testzip()
                if bad_file is not None:
                    result["warnings"].append(
                        f"APK ZIP integrity check failed for: {bad_file}"
                    )
                    return result

                names = archive.namelist()
                normalized_names = [name.replace("\\", "/") for name in names]

                manifest_present = "AndroidManifest.xml" in normalized_names
                result["has_android_manifest"] = manifest_present

                dex_files = sorted(
                    name
                    for name in normalized_names
                    if re.fullmatch(r"classes\d*\.dex", name)
                )
                result["dex_files"] = dex_files
                result["dex_count"] = len(dex_files)

                native_libraries = sorted(
                    name
                    for name in normalized_names
                    if name.startswith("lib/")
                    and name.lower().endswith((".so", ".dll"))
                )
                result["native_libraries"] = native_libraries
                result["native_library_count"] = len(native_libraries)

                suspicious_entries = sorted(
                    name
                    for name in normalized_names
                    if self._is_suspicious_entry(name)
                )
                result["suspicious_entries"] = suspicious_entries

                result["entry_count"] = len(normalized_names)

                if not manifest_present:
                    result["warnings"].append(
                        "AndroidManifest.xml is missing."
                    )

                if result["dex_count"] == 0:
                    result["warnings"].append(
                        "No classes*.dex file was found."
                    )

                result["is_valid"] = manifest_present and result["dex_count"] > 0

        except zipfile.BadZipFile:
            result["warnings"].append("APK is not a valid ZIP archive.")
        except (OSError, ValueError) as exc:
            result["warnings"].append(
                f"APK inspection failed: {type(exc).__name__}: {exc}"
            )

        return result

    @staticmethod
    def _is_suspicious_entry(name: str) -> bool:
        """Identify unusual archive entries for later investigation."""

        lowered = name.lower()

        suspicious_patterns = (
            "../",
            "..\\",
            "assets/.hidden",
            "lib/.",
            "classes.dex.bak",
            "classes.dex.tmp",
        )

        return any(pattern in lowered for pattern in suspicious_patterns)
