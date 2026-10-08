from uuid import uuid4

from app.contracts.risk import RiskLevel
from app.services.risk_engine import calculate_risk


def test_risk_engine_scores_canonical_claims_without_double_counting():
    investigation_id = uuid4()

    assessment = calculate_risk(
        investigation_id=investigation_id,
        claims=[
            {"claim_type": "guaranteed_returns"},
            {"claim_type": "urgency_fomo"},
        ],
        indicators=[
            "abnormal_guaranteed_returns",
            "artificial_urgency",
        ],
        evidence=[],
    )

    assert assessment.score == 35
    assert assessment.level == RiskLevel.MEDIUM
    assert len(assessment.signals) == 2


def test_risk_engine_caps_score_at_100():
    investigation_id = uuid4()

    assessment = calculate_risk(
        investigation_id=investigation_id,
        claims=[
            {"claim_type": "guaranteed_returns"},
            {"claim_type": "zero_risk"},
            {"claim_type": "unauthorized_pms"},
            {"claim_type": "urgency_fomo"},
            {"claim_type": "insider_tips"},
            {"claim_type": "institutional_partnership"},
            {"claim_type": "celebrity_endorsement"},
        ],
        indicators=[],
        evidence=[],
    )

    assert assessment.score == 100
    assert assessment.level == RiskLevel.CRITICAL


def test_unavailable_analysis_creates_uncertainty_without_reducing_score():
    investigation_id = uuid4()

    assessment = calculate_risk(
        investigation_id=investigation_id,
        claims=[],
        indicators=[],
        evidence=[],
        tool_results=[
            {
                "tool_name": "url_classifier",
                "status": "UNAVAILABLE",
            }
        ],
    )

    assert assessment.score == 0
    assert assessment.level == RiskLevel.LOW
    assert assessment.uncertainties
    assert assessment.status.value == "PARTIAL"
