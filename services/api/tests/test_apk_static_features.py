from app.providers.apk_static_features import APKStaticFeatureExtractor


def test_extracts_static_features():
    foundation = {
        "archive": {
            "classes_dex_count": 2,
            "has_resources": True,
            "has_certificate_directory": True,
            "native_library_count": 1,
            "has_native_libraries": True,
        }
    }

    manifest = {
        "permissions": [
            "android.permission.READ_SMS",
            "android.permission.CAMERA",
            "android.permission.INTERNET",
        ],
        "components": {
            "activities": ["MainActivity"],
            "services": ["SyncService"],
            "receivers": ["BootReceiver"],
            "providers": [],
        },
        "sdk": {
            "min": 23,
            "target": 28,
        },
    }

    certificates = {
        "certificate_count": 1,
        "signature_schemes": ["v2"],
    }

    result = APKStaticFeatureExtractor().extract(
        foundation,
        manifest,
        certificates,
    )

    assert result["status"] == "SUCCESS"

    features = result["feature_vector"]

    assert features["permission_count"] == 3
    assert features["high_risk_permission_count"] == 2
    assert features["sms_permission_indicator"] == 1
    assert features["authentication_permission_indicator"] == 0
    assert features["activity_count"] == 1
    assert features["service_count"] == 1
    assert features["receiver_count"] == 1
    assert features["provider_count"] == 0
    assert features["min_sdk"] == 23
    assert features["target_sdk"] == 28
    assert features["legacy_target_sdk_indicator"] == 1
    assert features["certificate_count"] == 1
    assert features["signature_scheme_count"] == 1
    assert features["dex_count"] == 2
    assert features["native_library_count"] == 1
    assert features["native_library_indicator"] == 1
    assert features["resource_indicator"] == 1
    assert features["certificate_directory_indicator"] == 1


def test_feature_extraction_is_deterministic():
    foundation = {
        "archive": {
            "classes_dex_count": 1,
            "has_resources": False,
            "has_certificate_directory": False,
            "native_library_count": 0,
            "has_native_libraries": False,
        }
    }

    manifest = {
        "permissions": [],
        "components": {
            "activities": [],
            "services": [],
            "receivers": [],
            "providers": [],
        },
        "sdk": {
            "min": 21,
            "target": 35,
        },
    }

    certificates = {
        "certificate_count": 0,
        "signature_schemes": [],
    }

    extractor = APKStaticFeatureExtractor()

    first = extractor.extract(foundation, manifest, certificates)
    second = extractor.extract(foundation, manifest, certificates)

    assert first == second
