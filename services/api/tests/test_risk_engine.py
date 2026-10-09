from uuid import uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.risk import RiskLevel
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
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


def test_claim_derived_risk_signal_includes_evidence_id():
    investigation_id = uuid4()
    evidence_id = uuid4()

    evidence = [
        EvidenceContract(
            id=evidence_id,
            investigation_id=investigation_id,
            input_id=None,
            type=EvidenceType.RISK_SIGNAL,
            category="claim:guaranteed_returns",
            severity=SeverityLevel.HIGH,
            confidence=0.95,
            description="Guaranteed 20% monthly returns claim detected.",
            source_type="model",
            source_name="claim_extractor",
            source_version="1.0.0",
            status=AnalysisStatus.SUCCESS,
            raw_payload={
                "claim": "Guaranteed 20% monthly returns",
                "claim_type": "guaranteed_returns",
            },
        ),
        EvidenceContract(
            investigation_id=investigation_id,
            input_id=None,
            type=EvidenceType.RISK_SIGNAL,
            category="claim_extraction",
            severity=SeverityLevel.LOW,
            confidence=0.0,
            description="Failed extractor run should not be linked as claim proof.",
            source_type="model",
            source_name="claim_extractor",
            source_version="1.0.0",
            status=AnalysisStatus.FAILED,
        ),
    ]

    assessment = calculate_risk(
        investigation_id=investigation_id,
        claims=[{"claim_type": "guaranteed_returns"}],
        indicators=[],
        evidence=evidence,
    )

    assert assessment.score == 20
    assert assessment.level == RiskLevel.LOW
    assert len(assessment.signals) == 1
    signal = assessment.signals[0]
    assert signal.category == "guaranteed_returns"
    assert signal.evidence_ids == [evidence_id]
