"""Tests for VERA Investigation Tools and Registry."""

from uuid import uuid4

import pytest

from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.claim_extractor import ClaimExtractorTool
from app.investigator.tools.entity_extractor import EntityExtractorTool
from app.investigator.tools.normalizer import InputNormalizerTool
from app.investigator.tools.pattern_analyzer import ScamPatternAnalyzerTool
from app.investigator.tools.registry import ToolRegistry, create_default_registry
from app.providers.mock_llm import MockLLMProvider


@pytest.mark.asyncio
async def test_input_normalizer_tool_success() -> None:
    """Verifies InputNormalizerTool cleans whitespace and creates baseline forensic artifact."""
    tool = InputNormalizerTool()
    assert tool.name == "input_normalizer"

    state = {
        "investigation_id": str(uuid4()),
        "raw_input_text": "  Join VIP \u200BTrading group \r\nwith guaranteed 100% profit!  ",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.SUCCESS
    assert result.output_data["normalized_text"] == "Join VIP Trading group \nwith guaranteed 100% profit!"
    assert len(result.evidence) == 1
    assert result.evidence[0].type == EvidenceType.FORENSIC_ARTIFACT
    assert result.evidence[0].category == "input_normalization"


@pytest.mark.asyncio
async def test_input_normalizer_empty_input() -> None:
    """Verifies InputNormalizerTool marks empty inputs as INSUFFICIENT_EVIDENCE."""
    tool = InputNormalizerTool()
    state = {"investigation_id": str(uuid4()), "raw_input_text": "   "}
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence[0].status == AnalysisStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_entity_extractor_tool() -> None:
    """Verifies EntityExtractorTool produces typed entity detection evidence."""
    mock_llm = MockLLMProvider(mode="guaranteed_return")
    tool = EntityExtractorTool(llm_provider=mock_llm)

    state = {
        "investigation_id": str(uuid4()),
        "normalized_input": "Send money to wealth@fakeupi and join VIP Wealth Club Telegram.",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) >= 1
    assert all(e.type == EvidenceType.ENTITY_DETECTION for e in result.evidence)
    assert all(e.status == AnalysisStatus.SUCCESS for e in result.evidence)


@pytest.mark.asyncio
async def test_claim_extractor_tool() -> None:
    """Verifies ClaimExtractorTool extracts promises and marks severity without judging guilt."""
    mock_llm = MockLLMProvider(mode="guaranteed_return")
    tool = ClaimExtractorTool(llm_provider=mock_llm)

    state = {
        "investigation_id": str(uuid4()),
        "normalized_input": "Guaranteed 200% monthly returns zero risk!",
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) >= 1
    assert all(e.type == EvidenceType.RISK_SIGNAL for e in result.evidence)
    assert any(e.severity in (SeverityLevel.HIGH, SeverityLevel.MEDIUM) for e in result.evidence)


@pytest.mark.asyncio
async def test_scam_pattern_analyzer_tool() -> None:
    """Verifies ScamPatternAnalyzerTool evaluates behavioral indicators."""
    mock_llm = MockLLMProvider(mode="guaranteed_return")
    tool = ScamPatternAnalyzerTool(llm_provider=mock_llm)

    state = {
        "investigation_id": str(uuid4()),
        "normalized_input": "200% profit guaranteed closing in 1 hour!",
        "entities": [],
        "claims": [],
    }
    result = await tool.execute(state)
    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1
    assert result.evidence[0].category == "scam_behavioral_patterns"
    assert "explanation" in result.output_data


@pytest.mark.asyncio
async def test_tools_offline_llm_fail_safe() -> None:
    """Verifies tools never crash when the LLM is unavailable and emit UNAVAILABLE status evidence."""
    mock_offline = MockLLMProvider(mode="unavailable")

    entity_tool = EntityExtractorTool(llm_provider=mock_offline)
    state = {"investigation_id": str(uuid4()), "normalized_input": "Some text"}
    res_entity = await entity_tool.execute(state)
    assert res_entity.status == AnalysisStatus.UNAVAILABLE
    assert res_entity.evidence[0].status == AnalysisStatus.UNAVAILABLE

    claim_tool = ClaimExtractorTool(llm_provider=mock_offline)
    res_claim = await claim_tool.execute(state)
    assert res_claim.status == AnalysisStatus.UNAVAILABLE
    assert res_claim.evidence[0].status == AnalysisStatus.UNAVAILABLE

    pattern_tool = ScamPatternAnalyzerTool(llm_provider=mock_offline)
    res_pattern = await pattern_tool.execute(state)
    assert res_pattern.status == AnalysisStatus.UNAVAILABLE
    assert res_pattern.evidence[0].status == AnalysisStatus.UNAVAILABLE


def test_tool_registry() -> None:
    """Verifies ToolRegistry registration and lookup."""
    registry = create_default_registry(llm_provider=MockLLMProvider())
    tools = registry.list_names()
    assert "input_normalizer" in tools
    assert "entity_extractor" in tools
    assert "claim_extractor" in tools
    assert "scam_pattern_analyzer" in tools
    assert registry.get("non_existent") is None
