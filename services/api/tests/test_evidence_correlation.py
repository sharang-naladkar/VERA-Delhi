from uuid import uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import ToolResult
from app.services.evidence_correlation import build_evidence_correlation


def test_evidence_correlation_is_deterministic():
    investigation_id = uuid4()

    evidence = EvidenceContract(
        investigation_id=investigation_id,
        input_id=None,
        type=EvidenceType.RISK_SIGNAL,
        category="guaranteed_returns",
        severity=SeverityLevel.HIGH,
        confidence=0.9,
        description="Guaranteed return claim detected",
        source_type="heuristic",
        source_name="test-analyzer",
        status=AnalysisStatus.SUCCESS,
    )

    tool_result = ToolResult(
        tool_name="test-analyzer",
        tool_version="1.0",
        status=AnalysisStatus.SUCCESS,
        evidence=[evidence],
    )

    kwargs = dict(
        investigation_id=investigation_id,
        input_id=None,
        input_reference="input-1",
        entities=[
            {
                "entity_type": "person",
                "name": "Test Advisor",
                "normalized_value": "test advisor",
                "source_text": "Test Advisor",
                "confidence": 0.95,
            }
        ],
        claims=[
            {
                "claim_type": "guaranteed_returns",
                "claim": "Guaranteed 20% monthly returns",
                "source_text": "Guaranteed 20% monthly returns",
                "confidence": 0.91,
            }
        ],
        indicators=["guaranteed_returns", "guaranteed_returns", "urgency_fomo"],
        tool_results=[tool_result],
        evidence=[evidence],
    )

    first = build_evidence_correlation(**kwargs)
    second = build_evidence_correlation(**kwargs)

    assert first.entities[0].id == second.entities[0].id
    assert first.claims[0].id == second.claims[0].id
    assert [item.id for item in first.indicators] == [
        item.id for item in second.indicators
    ]
    assert len(first.indicators) == 2
    assert first.evidence[0] is evidence
    assert first.tool_results[0] is tool_result


def test_evidence_correlation_skips_incomplete_entities_and_claims():
    investigation_id = uuid4()

    result = build_evidence_correlation(
        investigation_id=investigation_id,
        input_id=None,
        input_reference=None,
        entities=[
            {
                "entity_type": "person",
                "name": "",
                "normalized_value": "missing-name",
                "confidence": 0.8,
            }
        ],
        claims=[
            {
                "claim_type": "other",
                "claim": "",
                "confidence": 0.8,
            }
        ],
        indicators=[""],
        tool_results=[],
        evidence=[],
    )

    assert result.entities == []
    assert result.claims == []
    assert result.indicators == []
