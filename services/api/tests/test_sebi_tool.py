"""Tests for the SEBI regulatory intelligence investigation tool."""

from uuid import uuid4

import pytest

from app.contracts.sebi import VerificationStatus
from app.contracts.status import AnalysisStatus
from app.investigator.tools.sebi_tool import SEBIInvestigationTool
from app.providers.sebi import MockSEBIProvider, UnavailableSEBIProvider


@pytest.mark.asyncio
async def test_sebi_tool_missing_entity_information() -> None:
    tool = SEBIInvestigationTool(UnavailableSEBIProvider())

    result = await tool.execute({})

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == []
    assert result.output_data["verification"] is None


@pytest.mark.asyncio
async def test_sebi_tool_unavailable_provider() -> None:
    tool = SEBIInvestigationTool(UnavailableSEBIProvider())

    result = await tool.execute(
        {
            "investigation_id": str(uuid4()),
            "entity_name": "Example Advisor",
            "registration_number": "TEST-ONLY",
            "entity_type": "investment_adviser",
        }
    )

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert len(result.evidence) == 1
    assert result.evidence[0].status == AnalysisStatus.UNAVAILABLE

    verification = result.output_data["verification"]

    assert verification["status"] == VerificationStatus.UNAVAILABLE.value
    assert verification["entity_name"] == "Example Advisor"
    assert verification["registration_number"] == "TEST-ONLY"
    assert verification["entity_type"] == "investment_adviser"
    assert verification["metadata"]["source_available"] is False


@pytest.mark.asyncio
async def test_sebi_tool_verified_fixture() -> None:
    tool = SEBIInvestigationTool(
        MockSEBIProvider(status=VerificationStatus.VERIFIED)
    )

    result = await tool.execute(
        {
            "investigation_id": str(uuid4()),
            "entity_name": "Test Advisor",
            "registration_number": "TEST-VERIFIED",
            "entity_type": "investment_adviser",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1
    assert result.evidence[0].status == AnalysisStatus.SUCCESS
    assert result.evidence[0].confidence == 1.0

    verification = result.output_data["verification"]

    assert verification["status"] == VerificationStatus.VERIFIED.value
    assert verification["metadata"]["test_fixture"] is True


@pytest.mark.asyncio
async def test_sebi_tool_not_verified_fixture() -> None:
    tool = SEBIInvestigationTool(
        MockSEBIProvider(status=VerificationStatus.NOT_VERIFIED)
    )

    result = await tool.execute(
        {
            "entity_name": "Test Advisor",
            "registration_number": "TEST-NOT-VERIFIED",
            "entity_type": "investment_adviser",
        }
    )

    assert result.status == AnalysisStatus.NOT_VERIFIED
    assert result.evidence[0].status == AnalysisStatus.NOT_VERIFIED
    assert result.evidence[0].confidence == 0.0


@pytest.mark.asyncio
async def test_sebi_tool_partial_fixture() -> None:
    tool = SEBIInvestigationTool(
        MockSEBIProvider(status=VerificationStatus.PARTIAL)
    )

    result = await tool.execute(
        {
            "entity_name": "Test Advisor",
            "registration_number": "TEST-PARTIAL",
        }
    )

    assert result.status == AnalysisStatus.PARTIAL
    assert result.evidence[0].status == AnalysisStatus.PARTIAL


@pytest.mark.asyncio
async def test_sebi_tool_failed_provider() -> None:
    tool = SEBIInvestigationTool(
        MockSEBIProvider(status=VerificationStatus.FAILED)
    )

    result = await tool.execute(
        {
            "entity_name": "Test Advisor",
        }
    )

    assert result.status == AnalysisStatus.FAILED
    assert result.evidence[0].status == AnalysisStatus.FAILED


@pytest.mark.asyncio
async def test_sebi_tool_insufficient_evidence_fixture() -> None:
    tool = SEBIInvestigationTool(
        MockSEBIProvider(
            status=VerificationStatus.INSUFFICIENT_EVIDENCE
        )
    )

    result = await tool.execute(
        {
            "entity_name": "Test Advisor",
        }
    )

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE