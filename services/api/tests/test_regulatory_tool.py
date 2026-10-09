"""Tests for the regulatory investigator tool."""

from uuid import uuid4

import pytest

from app.contracts.regulatory import RegulatoryParticipantType
from app.contracts.status import AnalysisStatus
from app.investigator.tools.regulatory_tool import RegulatoryVerificationTool
from app.investigator.tools.registry import create_default_registry
from app.providers.mock_llm import MockLLMProvider


@pytest.mark.asyncio
async def test_missing_request_does_not_attempt_verification():
    tool = RegulatoryVerificationTool()

    result = await tool.execute({"investigation_id": str(uuid4())})

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == []
    assert result.output_data["matched"] is None
    assert result.output_data["verification_status"] == (
        AnalysisStatus.INSUFFICIENT_EVIDENCE.value
    )


@pytest.mark.asyncio
async def test_invalid_request_does_not_claim_match():
    tool = RegulatoryVerificationTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid4()),
            "regulatory_verification_request": {
                "participant_type": "investment_adviser",
            },
        }
    )

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == []
    assert result.output_data["matched"] is None
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_default_service_returns_unavailable_without_live_adapter():
    tool = RegulatoryVerificationTool()

    result = await tool.execute(
        {
            "investigation_id": str(uuid4()),
            "regulatory_verification_request": {
                "participant_type": RegulatoryParticipantType.INVESTMENT_ADVISER.value,
                "subject_name": "Example Adviser",
            },
        }
    )

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.output_data["matched"] is None
    assert result.output_data["verification_status"] == (
        AnalysisStatus.UNAVAILABLE.value
    )
    assert result.evidence == []


@pytest.mark.asyncio
async def test_missing_investigation_id_fails_without_evidence():
    tool = RegulatoryVerificationTool()

    result = await tool.execute(
        {
            "regulatory_verification_request": {
                "participant_type": "investment_adviser",
                "subject_name": "Example Adviser",
            }
        }
    )

    assert result.status == AnalysisStatus.FAILED
    assert result.evidence == []


def test_default_registry_registers_regulatory_tool():
    registry = create_default_registry(llm_provider=MockLLMProvider())

    tool = registry.get("regulatory_verification")

    assert tool is not None
    assert isinstance(tool, RegulatoryVerificationTool)
