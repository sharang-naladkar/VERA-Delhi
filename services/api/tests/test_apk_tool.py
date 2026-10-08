import pytest

from app.contracts.status import AnalysisStatus
from app.investigator.tools.apk_tool import APKIntelligenceTool


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


@pytest.mark.asyncio
async def test_apk_tool_requires_investigation_id():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute({"apk_path": "sample.apk"})

    assert result.status == AnalysisStatus.FAILED
    assert result.error_message == "Investigation ID is missing."


@pytest.mark.asyncio
async def test_apk_tool_requires_apk_path():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute({"investigation_id": "550e8400-e29b-41d4-a716-446655440000"})

    assert result.status == AnalysisStatus.FAILED
    assert result.error_message == "APK input is missing."


@pytest.mark.asyncio
async def test_apk_tool_success():
    tool = APKIntelligenceTool(analyzer=FakeAPKAnalyzer())

    result = await tool.execute(
        {
            "investigation_id": "550e8400-e29b-41d4-a716-446655440000",
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 3

    categories = {e.category for e in result.evidence}
    assert categories == {
        "apk_foundation",
        "apk_manifest_analysis",
        "apk_certificate_analysis",
    }

    assert result.output_data["manifest_analysis"]["package_name"] == "com.example.test"
    assert result.output_data["certificate_analysis"]["signature_schemes"] == [
        "v2",
        "v3",
    ]


@pytest.mark.asyncio
async def test_apk_tool_preserves_manifest_failure():
    class ManifestFailureAnalyzer(FakeAPKAnalyzer):
        async def analyze_manifest(self, file_path):
            return {
                "status": "FAILED",
                "valid": False,
                "error": "manifest parsing failed",
            }

    tool = APKIntelligenceTool(analyzer=ManifestFailureAnalyzer())

    result = await tool.execute(
        {
            "investigation_id": "550e8400-e29b-41d4-a716-446655440000",
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 3

    manifest_evidence = next(
        e for e in result.evidence if e.category == "apk_manifest_analysis"
    )

    assert manifest_evidence.status == AnalysisStatus.FAILED
    assert manifest_evidence.confidence == 0.0


@pytest.mark.asyncio
async def test_apk_tool_preserves_certificate_failure():
    class CertificateFailureAnalyzer(FakeAPKAnalyzer):
        async def analyze_certificates(self, file_path):
            return {
                "status": "FAILED",
                "valid": False,
                "error": "certificate parsing failed",
            }

    tool = APKIntelligenceTool(analyzer=CertificateFailureAnalyzer())

    result = await tool.execute(
        {
            "investigation_id": "550e8400-e29b-41d4-a716-446655440000",
            "apk_path": "sample.apk",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 3

    certificate_evidence = next(
        e
        for e in result.evidence
        if e.category == "apk_certificate_analysis"
    )

    assert certificate_evidence.status == AnalysisStatus.FAILED
    assert certificate_evidence.confidence == 0.0
