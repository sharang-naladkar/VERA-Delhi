import pytest

from app.contracts.status import AnalysisStatus
from app.investigator.tools.apk_tool import APKIntelligenceTool


INVESTIGATION_ID = "550e8400-e29b-41d4-a716-446655440000"


class FakeAPKAnalyzer:
    async def analyze(self, file_path):
        return {
            "status": "SUCCESS",
            "valid": True,
            "file_name": "sample.apk",
            "file_size_bytes": 1234,
            "sha256": "a" * 64,
            "archive": {
                "member_count": 10,
                "manifest_present": True,
                "classes_dex_count": 1,
                "has_resources": True,
                "has_certificate_directory": True,
            },
        }

    async def analyze_manifest(self, file_path):
        return {
            "status": "SUCCESS",
            "valid": True,
            "package_name": "com.example.test",
            "application_name": "Test App",
            "permissions": ["android.permission.INTERNET"],
            "components": {
                "activities": ["com.example.MainActivity"],
                "activity_aliases": [],
                "services": [],
                "receivers": [],
                "providers": [],
            },
            "sdk": {
                "min": 24,
                "target": 35,
                "effective_target": 35,
            },
            "main_activity": "com.example.MainActivity",
        }

    async def analyze_certificates(self, file_path):
        return {
            "status": "SUCCESS",
            "valid": True,
            "signature_schemes": ["v2", "v3"],
            "certificate_count": 1,
            "certificates": [
                {
                    "sha256_fingerprint": "b" * 64,
                    "serial_number": "123",
                    "subject": "CN=Test",
                    "issuer": "CN=Test",
                    "validity": {
                        "not_before": "2026-01-01T00:00:00+00:00",
                        "not_after": "2027-01-01T00:00:00+00:00",
                    },
                }
            ],
        }


class FakeClassifier:
    async def classify(self, feature_vector):
        assert len(feature_vector) == 18

        return {
            "status": "SUCCESS",
            "prediction": 1,
            "model_score": 0.91,
            "model_version": "test-model",
            "feature_count": 18,
            "feature_names": list(feature_vector.keys()),
        }


class UnavailableFakeClassifier:
    async def classify(self, feature_vector):
        return {
            "status": "UNAVAILABLE",
            "prediction": None,
            "model_score": None,
            "model_version": None,
            "feature_count": 0,
            "error": "Model artifact is not configured.",
        }


@pytest.mark.asyncio
async def test_apk_tool_requires_investigation_id():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute({"apk_path": "sample.apk"})

    assert result.status == AnalysisStatus.FAILED
    assert result.error_message == "Investigation ID is missing."


@pytest.mark.asyncio
async def test_apk_tool_requires_apk_path():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute(
        {"investigation_id": INVESTIGATION_ID}
    )

    assert result.status == AnalysisStatus.FAILED
    assert result.error_message == "APK input is missing."


@pytest.mark.asyncio
async def test_apk_tool_success():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 5

    assert "static_features" in result.output_data
    assert result.output_data["static_features"]["status"] == "SUCCESS"
    assert result.output_data["static_features"]["feature_count"] == 18

    # The default classifier has no configured model artifact.
    classification = result.output_data["apk_classification"]
    assert classification["status"] == "UNAVAILABLE"
    assert classification["prediction"] is None
    assert classification["model_score"] is None

    feature_evidence = [
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_static_features"
    ]

    assert len(feature_evidence) == 1
    assert feature_evidence[0].status == AnalysisStatus.SUCCESS

    classification_evidence = [
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_ml_classification"
    ]

    assert len(classification_evidence) == 1
    assert classification_evidence[0].status == AnalysisStatus.UNAVAILABLE
    assert classification_evidence[0].confidence == 0.0

    categories = {e.category for e in result.evidence}

    assert categories == {
        "apk_foundation",
        "apk_manifest_analysis",
        "apk_certificate_analysis",
        "apk_static_features",
        "apk_ml_classification",
    }

    assert (
        result.output_data["manifest_analysis"]["package_name"]
        == "com.example.test"
    )

    assert (
        result.output_data["certificate_analysis"]["signature_schemes"]
        == ["v2", "v3"]
    )


@pytest.mark.asyncio
async def test_apk_tool_uses_classifier_output():
    tool = APKIntelligenceTool(
        analyzer=FakeAPKAnalyzer(),
        classifier=FakeClassifier(),
    )

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS

    classification = result.output_data["apk_classification"]

    assert classification["status"] == "SUCCESS"
    assert classification["prediction"] == 1
    assert classification["model_score"] == 0.91
    assert classification["model_version"] == "test-model"
    assert classification["feature_count"] == 18

    classification_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_ml_classification"
    )

    assert classification_evidence.status == AnalysisStatus.SUCCESS
    assert classification_evidence.metadata["prediction"] == 1
    assert classification_evidence.metadata["model_score"] == 0.91

    # The model prediction is evidence, not VERA's final risk score.
    assert "risk_score" not in classification


@pytest.mark.asyncio
async def test_apk_tool_handles_unavailable_classifier():
    tool = APKIntelligenceTool(
        analyzer=FakeAPKAnalyzer(),
        classifier=UnavailableFakeClassifier(),
    )

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS

    classification = result.output_data["apk_classification"]

    assert classification["status"] == "UNAVAILABLE"
    assert classification["prediction"] is None
    assert classification["model_score"] is None

    # Deterministic APK analysis still succeeds.
    assert result.output_data["static_features"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_apk_tool_preserves_manifest_failure():
    class ManifestFailureAnalyzer(FakeAPKAnalyzer):
        async def analyze_manifest(self, file_path):
            return {
                "status": "FAILED",
                "valid": False,
                "error": "manifest parsing failed",
            }

    tool = APKIntelligenceTool(
        analyzer=ManifestFailureAnalyzer()
    )

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 4

    manifest_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_manifest_analysis"
    )

    assert manifest_evidence.status == AnalysisStatus.FAILED
    assert manifest_evidence.confidence == 0.0

    classification = result.output_data["apk_classification"]

    assert classification["status"] == "INSUFFICIENT_EVIDENCE"
    assert classification["prediction"] is None

    classification_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_ml_classification"
    )

    assert (
        classification_evidence.status
        == AnalysisStatus.INSUFFICIENT_EVIDENCE
    )


@pytest.mark.asyncio
async def test_apk_tool_preserves_certificate_failure():
    class CertificateFailureAnalyzer(FakeAPKAnalyzer):
        async def analyze_certificates(self, file_path):
            return {
                "status": "FAILED",
                "valid": False,
                "error": "certificate parsing failed",
            }

    tool = APKIntelligenceTool(
        analyzer=CertificateFailureAnalyzer()
    )

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 4

    certificate_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_certificate_analysis"
    )

    assert certificate_evidence.status == AnalysisStatus.FAILED
    assert certificate_evidence.confidence == 0.0

    classification = result.output_data["apk_classification"]

    assert classification["status"] == "INSUFFICIENT_EVIDENCE"
    assert classification["prediction"] is None


@pytest.mark.asyncio
async def test_apk_tool_survives_classifier_exception():
    class BrokenClassifier:
        async def classify(self, feature_vector):
            raise RuntimeError("simulated model failure")

    tool = APKIntelligenceTool(
        analyzer=FakeAPKAnalyzer(),
        classifier=BrokenClassifier(),
    )

    result = await tool.execute(
        {
            "investigation_id": INVESTIGATION_ID,
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS

    classification = result.output_data["apk_classification"]

    assert classification["status"] == "FAILED"
    assert classification["prediction"] is None
    assert "simulated model failure" in classification["error"]

    assert result.output_data["static_features"]["status"] == "SUCCESS"

    classification_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.category == "apk_ml_classification"
    )

    assert classification_evidence.status == AnalysisStatus.FAILED
    assert classification_evidence.confidence == 0.0