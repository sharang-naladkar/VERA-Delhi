"""Tests for LangGraph StateGraph Central VERA Investigator."""

from uuid import uuid4

import pytest

from app.contracts.status import AnalysisStatus
from app.investigator.orchestrator import VERAInvestigator
from app.investigator.state import InvestigationState
from app.investigator.tools.registry import create_default_registry
from app.providers.mock_llm import MockLLMProvider


@pytest.mark.asyncio
async def test_investigator_successful_flow() -> None:
    """Verifies complete 9-node LangGraph execution for a suspicious investment input."""
    mock_llm = MockLLMProvider(mode="guaranteed_return")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    investigation_id = uuid4()
    raw_text = "Join VIP Wealth Club! Guaranteed 200% monthly return! Send payment to wealth@fakeupi"

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=investigation_id,
        raw_input_text=raw_text,
        input_type="message",
    )

    assert state.investigation_id == investigation_id
    assert state.current_step == "completed"
    assert state.status == AnalysisStatus.SUCCESS
    assert state.normalized_input != ""
    assert len(state.entities) >= 1
    assert len(state.claims) >= 1
    assert len(state.indicators) >= 1
    assert state.investigation_plan is not None
    assert len(state.evidence) >= 3  # Normalizer + Entities + Claims + Pattern
    assert len(state.tool_results) >= 4
    assert len(state.errors) == 0

    # Critical architectural check: LLM/Investigator must NOT output numerical fraud risk score
    raw_dict = state.to_graph_state()
    assert "overall_score" not in raw_dict
    assert "fraud_probability" not in raw_dict


@pytest.mark.asyncio
async def test_investigator_clean_input_flow() -> None:
    """Verifies LangGraph correctly classifies clean/neutral financial message."""
    mock_llm = MockLLMProvider(mode="clean")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=uuid4(),
        raw_input_text="Tata Consultancy Services announced audited quarterly financial statements.",
        input_type="text",
    )

    assert state.current_step == "completed"
    assert state.status == AnalysisStatus.SUCCESS
    assert len(state.claims) == 0
    assert len(state.indicators) == 0


@pytest.mark.asyncio
async def test_investigator_empty_text_insufficient_evidence() -> None:
    """Verifies empty or blank input leads to INSUFFICIENT_EVIDENCE status."""
    mock_llm = MockLLMProvider(mode="insufficient_evidence")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=uuid4(),
        raw_input_text="   ",
        input_type="text",
    )

    assert state.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert state.current_step == "completed"


@pytest.mark.asyncio
async def test_investigator_llm_unavailable_fail_safe() -> None:
    """Verifies graph handles unavailable LLM gracefully without crashing, yielding PARTIAL/FAILED."""
    mock_llm = MockLLMProvider(mode="unavailable")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=uuid4(),
        raw_input_text="Invest in crypto guaranteed 50% daily return!",
        input_type="text",
    )

    # Must complete safely
    assert state.current_step == "completed"
    # Status must NOT be SUCCESS
    assert state.status in (AnalysisStatus.PARTIAL, AnalysisStatus.FAILED)
    # Errors must be recorded
    assert len(state.errors) >= 1
    # Evidence from normalizer must still be present
    assert len(state.evidence) >= 1
    # Unavailable evidence must be tagged UNAVAILABLE
    statuses = [e["status"] for e in state.evidence]
    assert AnalysisStatus.UNAVAILABLE.value in statuses


@pytest.mark.asyncio
async def test_investigator_malformed_llm_output_fail_safe() -> None:
    """Verifies graph handles malformed JSON from model gracefully without unhandled crashes."""
    mock_llm = MockLLMProvider(mode="malformed")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=uuid4(),
        raw_input_text="Invest now in our guaranteed program!",
        input_type="text",
    )

    assert state.current_step == "completed"
    assert state.status in (AnalysisStatus.PARTIAL, AnalysisStatus.FAILED)
    assert len(state.errors) >= 1
