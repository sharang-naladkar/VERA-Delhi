from __future__ import annotations

from typing import Any


HIGH_RISK_PERMISSIONS = {
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.RECORD_AUDIO",
    "android.permission.CAMERA",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.SYSTEM_ALERT_WINDOW",
}

SMS_PERMISSIONS = {
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.SEND_SMS",
}

AUTHENTICATION_PERMISSIONS = {
    "android.permission.USE_BIOMETRIC",
    "android.permission.USE_FINGERPRINT",
}

LEGACY_TARGET_SDK_THRESHOLD = 29


class APKStaticFeatureExtractor:
    """Extract deterministic static APK features."""

    def extract(
        self,
        foundation: dict[str, Any],
        manifest: dict[str, Any],
        certificates: dict[str, Any],
    ) -> dict[str, Any]:
        archive = foundation.get("archive", {})
        permissions = set(manifest.get("permissions", []))
        components = manifest.get("components", {})
        sdk = manifest.get("sdk", {})

        target_sdk = sdk.get("target")

        legacy_target_sdk = (
            target_sdk is not None
            and target_sdk < LEGACY_TARGET_SDK_THRESHOLD
        )

        feature_vector = {
            "permission_count": len(permissions),
            "high_risk_permission_count": len(
                permissions & HIGH_RISK_PERMISSIONS
            ),
            "sms_permission_indicator": int(
                bool(permissions & SMS_PERMISSIONS)
            ),
            "authentication_permission_indicator": int(
                bool(permissions & AUTHENTICATION_PERMISSIONS)
            ),
            "activity_count": len(components.get("activities", [])),
            "service_count": len(components.get("services", [])),
            "receiver_count": len(components.get("receivers", [])),
            "provider_count": len(components.get("providers", [])),
            "min_sdk": sdk.get("min"),
            "target_sdk": target_sdk,
            "legacy_target_sdk_indicator": int(legacy_target_sdk),
            "certificate_count": certificates.get("certificate_count", 0),
            "signature_scheme_count": len(
                certificates.get("signature_schemes", [])
            ),
            "dex_count": archive.get("classes_dex_count", 0),
            "native_library_count": archive.get(
                "native_library_count", 0
            ),
            "native_library_indicator": int(
                archive.get("has_native_libraries", False)
            ),
            "resource_indicator": int(
                archive.get("has_resources", False)
            ),
            "certificate_directory_indicator": int(
                archive.get("has_certificate_directory", False)
            ),
        }

        return {
            "status": "SUCCESS",
            "feature_vector": feature_vector,
            "feature_count": len(feature_vector),
        }
