"""Deterministic evidence correlation for VERA."""

from uuid import UUID, uuid5

from app.contracts.evidence import EvidenceContract
from app.contracts.evidence_correlation import (
    CorrelatedClaim,
    CorrelatedEntity,
    CorrelatedIndicator,
    EvidenceCorrelation,
)
from app.investigator.tools.base import ToolResult

_CORRELATION_NAMESPACE = UUID("00000000-0000-0000-0000-000000000001")


def _stable_id(investigation_id: UUID, kind: str, value: str) -> str:
    """Create a deterministic identifier for a correlated item."""
    return str(uuid5(_CORRELATION_NAMESPACE, f"{investigation_id}:{kind}:{value}"))


def build_evidence_correlation(
    *,
    investigation_id: UUID,
    input_id: UUID | None,
    input_reference: str | None,
    entities: list[dict],
    claims: list[dict],
    indicators: list[str],
    tool_results: list[ToolResult],
    evidence: list[EvidenceContract],
) -> EvidenceCorrelation:
    """Build a deterministic correlation view from existing investigation outputs."""

    correlated_entities: list[CorrelatedEntity] = []
    for entity in entities:
        normalized_value = str(entity.get("normalized_value", "")).strip()
        name = str(entity.get("name", "")).strip()

        if not normalized_value or not name:
            continue

        correlated_entities.append(
            CorrelatedEntity(
                id=_stable_id(
                    investigation_id,
                    "entity",
                    f"{entity.get('entity_type', 'other')}:{normalized_value}",
                ),
                entity_type=str(entity.get("entity_type", "other")),
                name=name,
                normalized_value=normalized_value,
                source_text=str(entity.get("source_text", "")),
                confidence=float(entity.get("confidence", 0.0)),
            )
        )

    correlated_claims: list[CorrelatedClaim] = []
    for claim in claims:
        claim_text = str(claim.get("claim", "")).strip()

        if not claim_text:
            continue

        correlated_claims.append(
            CorrelatedClaim(
                id=_stable_id(
                    investigation_id,
                    "claim",
                    f"{claim.get('claim_type', 'other')}:{claim_text}",
                ),
                claim_type=str(claim.get("claim_type", "other")),
                claim=claim_text,
                source_text=str(claim.get("source_text", "")),
                confidence=float(claim.get("confidence", 0.0)),
            )
        )

    correlated_indicators: list[CorrelatedIndicator] = []
    seen_indicators: set[str] = set()

    for indicator in indicators:
        value = str(indicator).strip()

        if not value or value in seen_indicators:
            continue

        seen_indicators.add(value)
        correlated_indicators.append(
            CorrelatedIndicator(
                id=_stable_id(investigation_id, "indicator", value),
                value=value,
            )
        )

    return EvidenceCorrelation(
        investigation_id=investigation_id,
        input_id=input_id,
        input_reference=input_reference,
        entities=correlated_entities,
        claims=correlated_claims,
        indicators=correlated_indicators,
        tool_results=list(tool_results),
        evidence=list(evidence),
    )
