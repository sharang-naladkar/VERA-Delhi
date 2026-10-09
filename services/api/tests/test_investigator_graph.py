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


@pytest.mark.asyncio
async def test_investigator_populates_evidence_correlation_and_graph() -> None:
    """Verifies that evidence correlation and graph are populated and round-trip serializable."""
    mock_llm = MockLLMProvider(mode="guaranteed_return")
    investigator = VERAInvestigator(llm_provider=mock_llm)

    investigation_id = uuid4()
    raw_text = "Join VIP Wealth Club! Guaranteed 200% monthly return! Contact @wealth"

    state: InvestigationState = await investigator.run_investigation(
        investigation_id=investigation_id,
        raw_input_text=raw_text,
        input_type="message",
    )

    assert state.status == AnalysisStatus.SUCCESS
    assert state.evidence_correlation is not None
    assert state.evidence_graph is not None

    # Correlation checks
    assert "entities" in state.evidence_correlation
    assert "claims" in state.evidence_correlation
    assert "indicators" in state.evidence_correlation
    assert "tool_results" in state.evidence_correlation
    assert "evidence" in state.evidence_correlation

    # Graph checks
    assert state.evidence_graph["investigation_id"] == str(investigation_id)
    assert "nodes" in state.evidence_graph
    assert "edges" in state.evidence_graph
    assert len(state.evidence_graph["nodes"]) >= 2
    assert len(state.evidence_graph["edges"]) >= 1

    # Round-trip serialization check
    serialized = state.to_graph_state()
    assert serialized["evidence_correlation"] == state.evidence_correlation
    assert serialized["evidence_graph"] == state.evidence_graph

    restored = InvestigationState.from_graph_state(serialized)
    assert restored.evidence_correlation == state.evidence_correlation
    assert restored.evidence_graph == state.evidence_graph


@pytest.mark.asyncio
async def test_investigator_skips_malformed_evidence_without_crashing() -> None:
    """Verifies that malformed evidence items are safely skipped and recorded into warnings."""
    investigator = VERAInvestigator(llm_provider=MockLLMProvider(mode="clean"))
    builder = investigator.graph_builder

    investigation_id = uuid4()
    state_dict = {
        "investigation_id": str(investigation_id),
        "input_id": None,
        "raw_input_reference": None,
        "raw_input_text": "Sample text",
        "entities": [],
        "claims": [],
        "indicators": [],
        "tool_results": [{"invalid_tool": True}],
        "evidence": [{"invalid_evidence": True}],
        "errors": [],
        "warnings": [],
        "status": AnalysisStatus.PENDING.value,
    }

    result = await builder._collect_evidence_node(state_dict)

    assert result["current_step"] == "collect_evidence"
    assert result["evidence_correlation"] is not None
    assert result["evidence_graph"] is not None
    assert len(result["warnings"]) >= 2
    assert any("malformed evidence" in w for w in result["warnings"])
    assert any("malformed tool result" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_investigator_correlation_and_graph_fail_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that if correlation fails, graph construction still executes and succeeds."""
    import app.investigator.graph as graph_module

    def failing_correlation(*args, **kwargs):
        raise RuntimeError("Simulated correlation crash")

    monkeypatch.setattr(
        graph_module, "build_evidence_correlation", failing_correlation
    )

    investigator = VERAInvestigator(llm_provider=MockLLMProvider(mode="clean"))
    builder = investigator.graph_builder

    investigation_id = uuid4()
    state_dict = {
        "investigation_id": str(investigation_id),
        "input_id": None,
        "raw_input_reference": None,
        "raw_input_text": "Sample text",
        "entities": [],
        "claims": [],
        "indicators": [],
        "tool_results": [],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "status": AnalysisStatus.PENDING.value,
    }

    result = await builder._collect_evidence_node(state_dict)

    assert result["current_step"] == "collect_evidence"
    assert result["evidence_correlation"] is None
    assert result["evidence_graph"] is not None
    assert result["status"] == AnalysisStatus.PARTIAL.value
    assert any("Evidence correlation failure" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_investigator_missing_investigation_id_handled_safely() -> None:
    """Verifies that missing investigation_id is handled safely without raising unhandled errors or generating random IDs."""
    investigator = VERAInvestigator(llm_provider=MockLLMProvider(mode="clean"))
    builder = investigator.graph_builder

    state_dict = {
        "investigation_id": None,
        "input_id": None,
        "raw_input_reference": None,
        "raw_input_text": "Sample text",
        "entities": [],
        "claims": [],
        "indicators": [],
        "tool_results": [],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "status": AnalysisStatus.PENDING.value,
    }

    collect_result = await builder._collect_evidence_node(state_dict)
    assert collect_result["current_step"] == "collect_evidence"
    assert collect_result["evidence_correlation"] is None
    assert collect_result["evidence_graph"] is None
    assert collect_result["status"] == AnalysisStatus.PARTIAL.value
    assert "Investigation ID missing in state" in collect_result["errors"]

    risk_result = await builder._calculate_risk_node(state_dict)
    assert risk_result["current_step"] == "calculate_risk"
    assert risk_result["risk_assessment"] is None
    assert risk_result["status"] == AnalysisStatus.PARTIAL.value
    assert "Investigation ID missing in state" in risk_result["errors"]


@pytest.mark.asyncio
async def test_investigator_malformed_investigation_id_handled_safely() -> None:
    """Verifies that malformed investigation_id uses fixed safe error messages without leaking raw exception text."""
    investigator = VERAInvestigator(llm_provider=MockLLMProvider(mode="clean"))
    builder = investigator.graph_builder

    state_dict = {
        "investigation_id": "malformed-not-a-uuid-sensitive-token",
        "input_id": None,
        "raw_input_reference": None,
        "raw_input_text": "Sample text",
        "entities": [],
        "claims": [],
        "indicators": [],
        "tool_results": [],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "status": AnalysisStatus.PENDING.value,
    }

    collect_result = await builder._collect_evidence_node(state_dict)
    assert collect_result["current_step"] == "collect_evidence"
    assert collect_result["evidence_correlation"] is None
    assert collect_result["evidence_graph"] is None
    assert collect_result["status"] == AnalysisStatus.PARTIAL.value
    assert "Invalid investigation_id in state" in collect_result["errors"]
    # Ensure sensitive raw input or exception text is not leaked into errors
    for err in collect_result["errors"]:
        assert "sensitive-token" not in err
        assert "badly formed hexadecimal" not in err

    risk_result = await builder._calculate_risk_node(state_dict)
    assert risk_result["current_step"] == "calculate_risk"
    assert risk_result["risk_assessment"] is None
    assert risk_result["status"] == AnalysisStatus.PARTIAL.value
    assert "Invalid investigation_id in state" in risk_result["errors"]
    for err in risk_result["errors"]:
        assert "sensitive-token" not in err
        assert "badly formed hexadecimal" not in err
