"""APK foundation and Android manifest analysis provider for VERA."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any

from app.providers.base import BaseProvider


class APKAnalyzerProvider(BaseProvider):
    """Validate APK files and extract deterministic APK metadata."""

    def __init__(self, max_file_size_bytes: int = 50 * 1024 * 1024) -> None:
        self.max_file_size_bytes = max_file_size_bytes

    @property
    def provider_name(self) -> str:
        return "apk_analyzer"

    @property
    def is_available(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "available": self.is_available,
        }

    async def analyze(self, file_path: str | Path) -> dict[str, Any]:
        """Validate an APK and extract deterministic foundation metadata."""
        path = Path(file_path)

        validation_error = self._validate_file(path)
        if validation_error is not None:
            return self._failure(validation_error)

        try:
            file_size = path.stat().st_size
        except OSError as exc:
            return self._failure(f"Unable to read APK metadata: {exc}")

        if file_size > self.max_file_size_bytes:
            return self._failure(
                f"APK exceeds maximum allowed size of {self.max_file_size_bytes} bytes."
            )

        if file_size == 0:
            return self._failure("APK file is empty.")

        try:
            sha256 = await self._calculate_sha256(path)

            with zipfile.ZipFile(path, "r") as archive:
                bad_member = archive.testzip()

                if bad_member is not None:
                    return self._failure(
                        f"APK archive contains a corrupt member: {bad_member}"
                    )

                names = archive.namelist()

                return {
                    "status": "SUCCESS",
                    "valid": True,
                    "file_name": path.name,
                    "file_size_bytes": file_size,
                    "sha256": sha256,
                    "archive": {
                        "member_count": len(names),
                        "manifest_present": "AndroidManifest.xml" in names,
                        "classes_dex_count": sum(
                            1
                            for name in names
                            if name.startswith("classes") and name.endswith(".dex")
                        ),
                        "has_resources": "resources.arsc" in names,
                        "has_certificate_directory": any(
                            name.startswith("META-INF/") for name in names
                        ),
                    },
                }

        except zipfile.BadZipFile:
            return self._failure("File is not a valid ZIP/APK archive.")
        except OSError as exc:
            return self._failure(f"Unable to read APK archive: {exc}")

    async def analyze_manifest(self, file_path: str | Path) -> dict[str, Any]:
        """Extract deterministic Android manifest metadata from an APK."""
        path = Path(file_path)

        validation_error = self._validate_file(path)
        if validation_error is not None:
            return self._failure(validation_error)

        try:
            file_size = path.stat().st_size
        except OSError as exc:
            return self._failure(f"Unable to read APK metadata: {exc}")

        if file_size > self.max_file_size_bytes:
            return self._failure(
                f"APK exceeds maximum allowed size of {self.max_file_size_bytes} bytes."
            )

        if file_size == 0:
            return self._failure("APK file is empty.")

        try:
            with zipfile.ZipFile(path, "r") as archive:
                if archive.testzip() is not None:
                    return self._failure("APK archive contains a corrupt member.")

                if "AndroidManifest.xml" not in archive.namelist():
                    return self._failure(
                        "AndroidManifest.xml is missing from the APK."
                    )

        except zipfile.BadZipFile:
            return self._failure("File is not a valid ZIP/APK archive.")
        except OSError as exc:
            return self._failure(f"Unable to read APK archive: {exc}")

        try:
            from androguard.core.apk import APK
        except ImportError:
            return {
                "status": "UNAVAILABLE",
                "valid": False,
                "error": "Androguard is not installed.",
            }

        try:
            apk = APK(str(path), skip_analysis=True)

            permissions = self._sorted_strings(apk.get_permissions())
            activities = self._sorted_strings(apk.get_activities())
            activity_aliases = self._sorted_strings(apk.get_activity_aliases())
            services = self._sorted_strings(apk.get_services())
            receivers = self._sorted_strings(apk.get_receivers())
            providers = self._sorted_strings(apk.get_providers())

            return {
                "status": "SUCCESS",
                "valid": True,
                "package_name": apk.get_package(),
                "application_name": self._safe_get_app_name(apk),
                "permissions": permissions,
                "components": {
                    "activities": activities,
                    "activity_aliases": activity_aliases,
                    "services": services,
                    "receivers": receivers,
                    "providers": providers,
                },
                "sdk": {
                    "min": apk.get_min_sdk_version(),
                    "target": apk.get_target_sdk_version(),
                    "effective_target": apk.get_effective_target_sdk_version(),
                },
                "main_activity": apk.get_main_activity(),
            }

        except Exception as exc:
            return self._failure(f"Unable to parse Android manifest: {exc}")

    async def analyze_certificates(self, file_path: str | Path) -> dict[str, Any]:
        """Extract deterministic signing certificate metadata from an APK."""
        path = Path(file_path)

        validation_error = self._validate_file(path)
        if validation_error is not None:
            return self._failure(validation_error)

        try:
            file_size = path.stat().st_size
        except OSError as exc:
            return self._failure(f"Unable to read APK metadata: {exc}")

        if file_size > self.max_file_size_bytes:
            return self._failure(
                f"APK exceeds maximum allowed size of {self.max_file_size_bytes} bytes."
            )

        if file_size == 0:
            return self._failure("APK file is empty.")

        try:
            from androguard.core.apk import APK
        except ImportError:
            return {
                "status": "UNAVAILABLE",
                "valid": False,
                "error": "Androguard is not installed.",
            }

        try:
            apk = APK(str(path), skip_analysis=True)

            signature_names = sorted(set(apk.get_signature_names()))
            certificates = apk.get_certificates()

            certificate_data = [
                self._certificate_to_dict(certificate)
                for certificate in certificates
                if certificate is not None
            ]

            return {
                "status": "SUCCESS",
                "valid": True,
                "signature_schemes": signature_names,
                "certificate_count": len(certificate_data),
                "certificates": certificate_data,
            }

        except Exception as exc:
            return self._failure(
                f"Unable to extract APK signing certificates: {exc}"
            )

    @staticmethod
    def _certificate_to_dict(certificate: Any) -> dict[str, Any]:
        """Convert an asn1crypto certificate into deterministic metadata."""
        certificate_der = certificate.dump()
        fingerprint = hashlib.sha256(certificate_der).hexdigest()

        subject = certificate.subject
        issuer = certificate.issuer

        return {
            "sha256_fingerprint": fingerprint,
            "serial_number": str(certificate.serial_number),
            "subject": APKAnalyzerProvider._name_to_string(subject),
            "issuer": APKAnalyzerProvider._name_to_string(issuer),
            "validity": {
                "not_before": APKAnalyzerProvider._safe_datetime(
                    certificate["tbs_certificate"]["validity"]["not_before"]
                ),
                "not_after": APKAnalyzerProvider._safe_datetime(
                    certificate["tbs_certificate"]["validity"]["not_after"]
                ),
            },
        }

    @staticmethod
    def _name_to_string(name: Any) -> str:
        """Convert an X.509 distinguished name to a stable string."""
        try:
            return name.human_friendly
        except Exception:
            return str(name)

    @staticmethod
    def _safe_datetime(value: Any) -> str | None:
        """Normalize an ASN.1 time value to an ISO-like string."""
        try:
            native_value = value.native

            if native_value is None:
                return None

            if hasattr(native_value, "isoformat"):
                return native_value.isoformat()

            return str(native_value)
        except Exception:
            return None

    @staticmethod
    def _validate_file(path: Path) -> str | None:
        """Return a validation error, or None when the path is usable."""
        if not path.exists():
            return "APK file does not exist."

        if not path.is_file():
            return "APK path is not a regular file."

        return None

    @staticmethod
    def _sorted_strings(values: Any) -> list[str]:
        """Normalize an iterable of string-like values deterministically."""
        if values is None:
            return []

        return sorted({str(value) for value in values if value})

    @staticmethod
    def _safe_get_app_name(apk: Any) -> str | None:
        """Extract application name without failing the complete manifest parse."""
        try:
            value = apk.get_app_name()
        except Exception:
            return None

        if value is None:
            return None

        return str(value)

    async def _calculate_sha256(self, path: Path) -> str:
        """Calculate SHA-256 without loading the entire APK into memory."""
        digest = hashlib.sha256()

        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)

        return digest.hexdigest()

    def _failure(self, message: str) -> dict[str, Any]:
        return {
            "status": "FAILED",
            "valid": False,
            "error": message,
        }