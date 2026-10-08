"""Drebin-style deterministic feature extraction for APK analysis."""

from __future__ import annotations

from typing import Any


class APKFeatureExtractor:
    """Convert APK structural/static analysis into ML-ready features."""

    FEATURE_NAMES: tuple[str, ...] = (
        "dex_count",
        "native_library_count",
        "string_count",
        "url_count",
        "ip_count",
        "api_indicator_count",
        "obfuscation_indicator_count",
        "suspicious_entry_count",
        "has_manifest",
        "has_sms_api",
        "has_telephony_api",
        "has_location_api",
        "has_network_api",
        "has_webview_api",
        "has_accessibility_api",
        "has_device_admin_api",
        "has_http_api",
        "has_url_api",
        "has_tls_api",
        "has_runtime_api",
        "has_dynamic_code_loading",
        "has_dynamic_class_loading",
        "has_package_manager_api",
        "has_clipboard_api",
        "has_camera_api",
        "has_audio_record_api",
        "has_device_information_api",
        "has_short_class_reference",
        "has_short_package_reference",
        "has_base64_reference",
        "has_xor_reference",
        "has_high_short_string_ratio",
    )

    API_FEATURE_MAP: dict[str, str] = {
        "sms_api": "has_sms_api",
        "telephony_api": "has_telephony_api",
        "location_api": "has_location_api",
        "network_api": "has_network_api",
        "webview_api": "has_webview_api",
        "accessibility_api": "has_accessibility_api",
        "device_admin_api": "has_device_admin_api",
        "http_api": "has_http_api",
        "url_api": "has_url_api",
        "tls_api": "has_tls_api",
        "runtime_api": "has_runtime_api",
        "dynamic_code_loading": "has_dynamic_code_loading",
        "dynamic_class_loading": "has_dynamic_class_loading",
        "package_manager_api": "has_package_manager_api",
        "clipboard_api": "has_clipboard_api",
        "camera_api": "has_camera_api",
        "audio_record_api": "has_audio_record_api",
        "device_information_api": "has_device_information_api",
    }

    OBFUSCATION_FEATURE_MAP: dict[str, str] = {
        "short_class_reference": "has_short_class_reference",
        "short_package_reference": "has_short_package_reference",
        "base64_reference": "has_base64_reference",
        "xor_reference": "has_xor_reference",
        "high_short_string_ratio": "has_high_short_string_ratio",
    }

    def extract(
        self,
        structural_result: dict[str, Any],
        static_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a stable numeric/binary feature vector."""

        features: dict[str, int | float] = {
            "dex_count": self._non_negative_int(
                structural_result.get("dex_count", 0)
            ),
            "native_library_count": self._non_negative_int(
                structural_result.get("native_library_count", 0)
            ),
            "string_count": self._non_negative_int(
                static_result.get("string_count", 0)
            ),
            "url_count": self._list_count(
                static_result.get("urls", [])
            ),
            "ip_count": self._list_count(
                static_result.get("ip_addresses", [])
            ),
            "api_indicator_count": self._list_count(
                static_result.get("api_indicators", [])
            ),
            "obfuscation_indicator_count": self._list_count(
                static_result.get("obfuscation_indicators", [])
            ),
            "suspicious_entry_count": self._list_count(
                structural_result.get("suspicious_entries", [])
            ),
            "has_manifest": int(
                bool(structural_result.get("has_android_manifest"))
            ),
        }

        for feature_name in self.API_FEATURE_MAP.values():
            features[feature_name] = 0

        api_indicators = {
            str(value)
            for value in (
                static_result.get("api_indicators") or []
            )
        }

        for indicator, feature_name in self.API_FEATURE_MAP.items():
            features[feature_name] = int(
                indicator in api_indicators
            )

        for feature_name in self.OBFUSCATION_FEATURE_MAP.values():
            features[feature_name] = 0

        obfuscation_indicators = {
            str(value)
            for value in (
                static_result.get("obfuscation_indicators") or []
            )
        }

        for indicator, feature_name in self.OBFUSCATION_FEATURE_MAP.items():
            features[feature_name] = int(
                indicator in obfuscation_indicators
            )

        return {
            "feature_names": list(self.FEATURE_NAMES),
            "features": {
                name: features.get(name, 0)
                for name in self.FEATURE_NAMES
            },
            "feature_vector": [
                features.get(name, 0)
                for name in self.FEATURE_NAMES
            ],
        }

    @staticmethod
    def _non_negative_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _list_count(value: Any) -> int:
        if isinstance(value, (list, tuple, set)):
            return len(value)

        return 0
