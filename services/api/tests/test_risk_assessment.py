"""Tests for VERA's deterministic risk assessment."""

from app.services.risk_assessment import assess_risk


def make_evidence(
    *,
    evidence_type="risk_signal",
    severity="high",
    confidence=1.0,
    status="SUCCESS",
    source_name="test_analyzer",
    category="investment_scam",
    description="Promises guaranteed investment returns",
    evidence_id="evidence-1",
):
    return {
        "id": evidence_id,
        "type": evidence_type,
        "severity": severity,
        "confidence": confidence,
        "status": status,
        "source_name": source_name,
        "category": category,
        "description": description,
    }


def test_high_severity_finding_contributes_expected_points():
    result = assess_risk([make_evidence()])

    assert result["score"] == 25
    assert result["level"] == "moderate"
    assert result["eligible_factor_count"] == 1
    assert result["factors"][0]["contribution"] == 25


def test_confidence_scales_contribution():
    result = assess_risk([make_evidence(confidence=0.5)])

    assert result["score"] == 12
    assert result["factors"][0]["confidence"] == 0.5


def test_unavailable_check_does_not_contribute():
    result = assess_risk([make_evidence(status="UNAVAILABLE")])

    assert result["score"] == 0
    assert result["level"] == "undetermined"
    assert result["eligible_factor_count"] == 0
    assert result["excluded_check_count"] == 1


def test_non_eligible_evidence_type_does_not_contribute():
    evidence = make_evidence(evidence_type="regulatory_check")

    result = assess_risk([evidence])

    assert result["score"] == 0
    assert result["level"] == "undetermined"


def test_duplicate_finding_from_same_source_is_counted_once():
    first = make_evidence(evidence_id="evidence-1")
    duplicate = make_evidence(evidence_id="evidence-2")

    result = assess_risk([first, duplicate])

    assert result["score"] == 25
    assert result["eligible_factor_count"] == 1


def test_distinct_findings_are_accumulated_and_score_is_capped():
    evidence = [
        make_evidence(
            severity="critical",
            description=f"Distinct indicator {index}",
            evidence_id=f"evidence-{index}",
        )
        for index in range(4)
    ]

    result = assess_risk(evidence)

    assert result["score"] == 100
    assert result["level"] == "high"
    assert result["eligible_factor_count"] == 4


def test_empty_evidence_is_undetermined():
    result = assess_risk([])

    assert result["score"] == 0
    assert result["level"] == "undetermined"
    assert result["factors"] == []


def test_invalid_confidence_does_not_raise():
    result = assess_risk([make_evidence(confidence="invalid")])

    assert result["score"] == 0
    assert result["level"] == "undetermined"


def test_score_is_not_fraud_probability():
    result = assess_risk([make_evidence()])

    assert result["is_fraud_probability"] is False
    assert result["score_type"] == "uncalibrated_indicator_score"
    assert result["limitations"]