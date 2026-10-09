"""Deterministic risk engine for VERA."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from app.contracts.evidence import EvidenceContract
from app.contracts.risk import RiskAssessment, RiskLevel, RiskSignal
from app.contracts.status import AnalysisStatus

_RISK_NAMESPACE = UUID("00000000-0000-0000-0000-000000000003")

_CLAIM_WEIGHTS = {
    "guaranteed_returns": 20,
    "zero_risk": 20,
    "unauthorized_pms": 25,
    "urgency_fomo": 15,
    "insider_tips": 15,
    "institutional_partnership": 10,
    "celebrity_endorsement": 10,
}

_INDICATOR_WEIGHTS = {
    "private_channel_solicitation": 10,
    "abnormal_guaranteed_returns": 20,
    "artificial_urgency": 15,
    "fake_institutional_backing": 10,
}


def _signal_id(investigation_id: UUID, category: str) -> str:
    """Create a deterministic identifier for a canonical risk signal."""
    return str(uuid5(_RISK_NAMESPACE, f"{investigation_id}:{category}"))


def _risk_level(score: int) -> RiskLevel:
    """Map a 0-100 risk index to its deterministic risk level."""
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _normalise(value: Any) -> str:
    """Normalize a rule input for deterministic matching."""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def calculate_risk(
    *,
    investigation_id: UUID,
    claims: list[dict[str, Any]],
    indicators: list[str],
    evidence: list[EvidenceContract],
    tool_results: list[dict[str, Any]] | None = None,
) -> RiskAssessment:
    """Calculate a deterministic 0-100 risk index from structured evidence.

    The score is a risk index, not a probability. Each canonical signal
    category can contribute at most once, preventing double-counting.
    """

    tool_results = tool_results or []
    signals: list[RiskSignal] = []
    uncertainties: list[str] = []
    scored_categories: set[str] = set()
    score = 0

    claim_lookup = {
        _normalise(claim.get("claim_type"))
        for claim in claims
        if claim.get("claim_type")
    }

    for category, points in _CLAIM_WEIGHTS.items():
        if category not in claim_lookup:
            continue

        scored_categories.add(category)
        matching_evidence_ids = [
            item.id
            for item in evidence
            if item.status == AnalysisStatus.SUCCESS
            and _normalise(item.category)
            in {
                f"claim:{category}",
                f"claim_{category}",
                category,
                "claim_extraction",
            }
        ]

        signals.append(
            RiskSignal(
                id=_signal_id(investigation_id, category),
                category=category,
                description=f"Claim category '{category}' was observed.",
                points=points,
                source="claim_extraction",
                evidence_ids=matching_evidence_ids,
            )
        )
        score += points

    normalized_indicators = {_normalise(indicator) for indicator in indicators}

    indicator_aliases = {
        "abnormal_guaranteed_returns": "guaranteed_returns",
        "artificial_urgency": "urgency_fomo",
        "fake_institutional_backing": "institutional_partnership",
    }

    for category, points in _INDICATOR_WEIGHTS.items():
        canonical_category = indicator_aliases.get(category, category)

        if canonical_category in scored_categories:
            continue

        if category not in normalized_indicators:
            continue

        scored_categories.add(category)
        signals.append(
            RiskSignal(
                id=_signal_id(investigation_id, category),
                category=category,
                description=f"Behavioral indicator '{category}' was observed.",
                points=points,
                source="scam_pattern_analysis",
                evidence_ids=[
                    item.id
                    for item in evidence
                    if item.category == "scam_behavioral_patterns"
                ],
            )
        )
        score += points

    for result in tool_results:
        status = _normalise(result.get("status"))

        if status in {
            AnalysisStatus.UNAVAILABLE.value.lower(),
            AnalysisStatus.FAILED.value.lower(),
        }:
            tool_name = result.get("tool_name", "unknown_tool")
            uncertainties.append(
                f"{tool_name} analysis was {status}; no safety inference was made."
            )

    for item in evidence:
        if item.status in {
            AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.FAILED,
            AnalysisStatus.NOT_VERIFIED,
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
        }:
            uncertainties.append(
                f"{item.source_name} evidence status is {item.status.value}; "
                "this does not indicate safety or legitimacy."
            )

    score = min(score, 100)

    status = (
        AnalysisStatus.PARTIAL
        if uncertainties
        else AnalysisStatus.SUCCESS
    )

    return RiskAssessment(
        investigation_id=investigation_id,
        score=score,
        level=_risk_level(score),
        status=status,
        signals=signals,
        uncertainties=uncertainties,
    )

