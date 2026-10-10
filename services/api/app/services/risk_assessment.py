"""Deterministic, explainable indicator risk assessment for VERA."""

from typing import Any

ASSESSMENT_VERSION = "1.0.0"

SEVERITY_POINTS = {
    "informational": 0,
    "low": 5,
    "medium": 15,
    "high": 25,
    "critical": 35,
}

EXCLUDED_STATUSES = {
    "FAILED",
    "UNAVAILABLE",
    "NOT_VERIFIED",
    "PENDING",
    "INSUFFICIENT_EVIDENCE",
}

# These are evidence types, not conclusions about fraud.
ELIGIBLE_EVIDENCE_TYPES = {
    "risk_signal",
    "url_analysis",
    "apk_analysis",
    "deepfake_analysis",
}


def assess_risk(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate an uncalibrated indicator score from eligible evidence."""
    factors: list[dict[str, Any]] = []
    excluded_count = 0
    seen: set[tuple[str, str, str]] = set()
    raw_score = 0

    for item in evidence:
        status = str(item.get("status", "SUCCESS")).upper()
        evidence_type = str(item.get("type", "")).lower()
        severity = str(item.get("severity", "informational")).lower()

        if status in EXCLUDED_STATUSES:
            excluded_count += 1
            continue

        if evidence_type not in ELIGIBLE_EVIDENCE_TYPES:
            continue

        points = SEVERITY_POINTS.get(severity, 0)
        if points <= 0:
            continue

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        # Do not count the same finding from the same source twice.
        key = (
            str(item.get("source_name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
        )
        if key in seen:
            continue
        seen.add(key)

        contribution = round(points * confidence)
        if contribution <= 0:
            continue

        raw_score += contribution
        factors.append(
            {
                "evidence_id": str(item.get("id", "")),
                "type": evidence_type,
                "category": str(item.get("category", "general")),
                "severity": severity,
                "confidence": confidence,
                "contribution": contribution,
                "reason": str(item.get("description", "")),
                "source": str(item.get("source_name", "unknown")),
            }
        )

    score = min(100, raw_score)

    if not factors:
        level = "undetermined"
    elif score >= 60:
        level = "high"
    elif score >= 25:
        level = "moderate"
    else:
        level = "low"

    return {
        "assessment_version": ASSESSMENT_VERSION,
        "score": score,
        "level": level,
        "score_type": "uncalibrated_indicator_score",
        "is_fraud_probability": False,
        "eligible_factor_count": len(factors),
        "excluded_check_count": excluded_count,
        "factors": factors,
        "limitations": [
            "This score is not a calibrated probability of fraud.",
            "Unavailable and unverified checks do not establish safety or wrongdoing.",
            "The assessment depends on the quality and coverage of available evidence.",
        ],
    }