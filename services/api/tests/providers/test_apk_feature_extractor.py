from __future__ import annotations

from app.providers.apk_feature_extractor import APKFeatureExtractor


def test_extracts_numeric_features() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={
            "dex_count": 2,
            "native_library_count": 3,
            "has_android_manifest": True,
            "suspicious_entries": ["../payload"],
        },
        static_result={
            "string_count": 120,
            "urls": ["https://example.com", "https://evil.example"],
            "ip_addresses": ["8.8.8.8"],
            "api_indicators": ["sms_api", "webview_api"],
            "obfuscation_indicators": ["base64_reference"],
        },
    )

    features = result["features"]

    assert features["dex_count"] == 2
    assert features["native_library_count"] == 3
    assert features["string_count"] == 120
    assert features["url_count"] == 2
    assert features["ip_count"] == 1
    assert features["api_indicator_count"] == 2
    assert features["obfuscation_indicator_count"] == 1
    assert features["suspicious_entry_count"] == 1
    assert features["has_manifest"] == 1


def test_api_indicators_become_binary_features() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={},
        static_result={
            "api_indicators": [
                "sms_api",
                "dynamic_code_loading",
                "camera_api",
            ],
        },
    )

    features = result["features"]

    assert features["has_sms_api"] == 1
    assert features["has_dynamic_code_loading"] == 1
    assert features["has_camera_api"] == 1
    assert features["has_location_api"] == 0
    assert features["has_runtime_api"] == 0


def test_obfuscation_indicators_become_binary_features() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={},
        static_result={
            "obfuscation_indicators": [
                "short_class_reference",
                "xor_reference",
                "high_short_string_ratio",
            ],
        },
    )

    features = result["features"]

    assert features["has_short_class_reference"] == 1
    assert features["has_xor_reference"] == 1
    assert features["has_high_short_string_ratio"] == 1
    assert features["has_base64_reference"] == 0


def test_feature_vector_matches_feature_names() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={},
        static_result={},
    )

    assert len(result["feature_names"]) == len(
        result["feature_vector"]
    )
    assert result["feature_names"] == list(
        APKFeatureExtractor.FEATURE_NAMES
    )


def test_missing_values_default_to_zero() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={
            "dex_count": "invalid",
            "native_library_count": None,
        },
        static_result={
            "string_count": "invalid",
            "urls": "invalid",
            "api_indicators": None,
        },
    )

    features = result["features"]

    assert features["dex_count"] == 0
    assert features["native_library_count"] == 0
    assert features["string_count"] == 0
    assert features["url_count"] == 0
    assert features["api_indicator_count"] == 0


def test_counts_never_become_negative() -> None:
    extractor = APKFeatureExtractor()

    result = extractor.extract(
        structural_result={
            "dex_count": -5,
            "native_library_count": -2,
        },
        static_result={
            "string_count": -10,
        },
    )

    features = result["features"]

    assert features["dex_count"] == 0
    assert features["native_library_count"] == 0
    assert features["string_count"] == 0
