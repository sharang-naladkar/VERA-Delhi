"""Deterministic evidence graph builder for VERA."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from app.contracts.evidence import EvidenceContract
from app.contracts.evidence_graph import (
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphEdgeType,
    EvidenceGraphNode,
    EvidenceGraphNodeType,
)

_GRAPH_NAMESPACE = UUID("00000000-0000-0000-0000-000000000002")


def _stable_id(investigation_id: UUID, kind: str, value: str) -> str:
    """Create a deterministic graph node identifier."""
    return str(uuid5(_GRAPH_NAMESPACE, f"{investigation_id}:{kind}:{value}"))


def _add_node(
    nodes: dict[str, EvidenceGraphNode],
    *,
    investigation_id: UUID,
    kind: str,
    node_type: EvidenceGraphNodeType,
    value: str,
    label: str,
    metadata: dict[str, Any] | None = None,
) -> EvidenceGraphNode:
    """Add or reuse a deterministic graph node."""
    node_id = _stable_id(investigation_id, kind, value)

    node = nodes.get(node_id)
    if node is None:
        node = EvidenceGraphNode(
            id=node_id,
            node_type=node_type,
            label=label,
            metadata=metadata or {},
        )
        nodes[node_id] = node

    return node


def _add_edge(
    edges: dict[tuple[str, str, str], EvidenceGraphEdge],
    *,
    source: EvidenceGraphNode,
    relationship: EvidenceGraphEdgeType,
    target: EvidenceGraphNode,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add a deterministic graph edge without duplicates."""
    key = (source.id, relationship.value, target.id)

    if key in edges:
        return

    edges[key] = EvidenceGraphEdge(
        source_id=source.id,
        source_type=source.node_type,
        relationship=relationship,
        target_id=target.id,
        target_type=target.node_type,
        metadata=metadata or {},
    )


def build_evidence_graph(
    *,
    investigation_id: UUID,
    input_id: UUID | None,
    raw_input_reference: str | None,
    raw_input_text: str,
    entities: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    indicators: list[str],
    evidence: list[EvidenceContract],
) -> EvidenceGraph:
    """Build a deterministic evidence graph from investigation outputs."""

    nodes: dict[str, EvidenceGraphNode] = {}
    edges: dict[tuple[str, str, str], EvidenceGraphEdge] = {}

    investigation_node = _add_node(
        nodes,
        investigation_id=investigation_id,
        kind="investigation",
        node_type=EvidenceGraphNodeType.INVESTIGATION,
        value=str(investigation_id),
        label=f"Investigation {investigation_id}",
    )

    input_value = (
        str(input_id)
        if input_id is not None
        else raw_input_reference or raw_input_text.strip()
    )

    input_node: EvidenceGraphNode | None = None

    if input_value:
        input_node = _add_node(
            nodes,
            investigation_id=investigation_id,
            kind="input",
            node_type=EvidenceGraphNodeType.INPUT,
            value=input_value,
            label=raw_input_reference or input_value,
            metadata={
                "input_id": str(input_id) if input_id else None,
                "input_reference": raw_input_reference,
            },
        )

        _add_edge(
            edges,
            source=investigation_node,
            relationship=EvidenceGraphEdgeType.INPUT_CONTAINS,
            target=input_node,
        )

    for entity in entities:
        normalized_value = str(entity.get("normalized_value", "")).strip()
        name = str(entity.get("name", "")).strip()

        if not normalized_value or not name:
            continue

        entity_type = str(entity.get("entity_type", "other")).strip().lower()

        node_type_map = {
            "person": EvidenceGraphNodeType.PERSON,
            "organization": EvidenceGraphNodeType.ORGANIZATION,
            "phone": EvidenceGraphNodeType.PHONE,
            "upi": EvidenceGraphNodeType.UPI,
            "url": EvidenceGraphNodeType.URL,
            "app_package": EvidenceGraphNodeType.APK,
        }

        node_type = node_type_map.get(
            entity_type,
            EvidenceGraphNodeType.EVIDENCE,
        )

        entity_node = _add_node(
            nodes,
            investigation_id=investigation_id,
            kind=f"entity:{entity_type}",
            node_type=node_type,
            value=normalized_value,
            label=name,
            metadata={
                "entity_type": entity_type,
                "confidence": entity.get("confidence", 0.0),
                "source_text": entity.get("source_text", ""),
            },
        )

        if input_node is not None:
            _add_edge(
                edges,
                source=input_node,
                relationship=EvidenceGraphEdgeType.INPUT_CONTAINS,
                target=entity_node,
            )

    for claim in claims:
        claim_text = str(claim.get("claim", "")).strip()

        if not claim_text:
            continue

        claim_type = str(claim.get("claim_type", "other")).strip()

        claim_node = _add_node(
            nodes,
            investigation_id=investigation_id,
            kind=f"claim:{claim_type}",
            node_type=EvidenceGraphNodeType.CLAIM,
            value=f"{claim_type}:{claim_text}",
            label=claim_text,
            metadata={
                "claim_type": claim_type,
                "confidence": claim.get("confidence", 0.0),
                "source_text": claim.get("source_text", ""),
            },
        )

        if input_node is not None:
            _add_edge(
                edges,
                source=input_node,
                relationship=EvidenceGraphEdgeType.CLAIMS,
                target=claim_node,
            )

    for indicator in indicators:
        indicator_value = str(indicator).strip()

        if not indicator_value:
            continue

        indicator_node = _add_node(
            nodes,
            investigation_id=investigation_id,
            kind="indicator",
            node_type=EvidenceGraphNodeType.RISK_SIGNAL,
            value=indicator_value,
            label=indicator_value,
        )

        if input_node is not None:
            _add_edge(
                edges,
                source=input_node,
                relationship=EvidenceGraphEdgeType.INDICATES,
                target=indicator_node,
            )

    for item in evidence:
        evidence_node = _add_node(
            nodes,
            investigation_id=investigation_id,
            kind="evidence",
            node_type=EvidenceGraphNodeType.EVIDENCE,
            value=str(item.id),
            label=item.category,
            metadata={
                "evidence_id": str(item.id),
                "type": item.type.value,
                "severity": item.severity.value,
                "confidence": item.confidence,
                "status": item.status.value,
                "source_name": item.source_name,
            },
        )

        if input_node is not None:
            _add_edge(
                edges,
                source=input_node,
                relationship=EvidenceGraphEdgeType.INDICATES,
                target=evidence_node,
            )

        for indicator in item.metadata.get("indicators", []):
            indicator_value = str(indicator).strip()

            if not indicator_value:
                continue

            indicator_node = _add_node(
                nodes,
                investigation_id=investigation_id,
                kind="indicator",
                node_type=EvidenceGraphNodeType.RISK_SIGNAL,
                value=indicator_value,
                label=indicator_value,
            )

            _add_edge(
                edges,
                source=evidence_node,
                relationship=EvidenceGraphEdgeType.INDICATES,
                target=indicator_node,
            )

        normalized_url = item.metadata.get("normalized_url")

        if normalized_url:
            url_node = _add_node(
                nodes,
                investigation_id=investigation_id,
                kind="url",
                node_type=EvidenceGraphNodeType.URL,
                value=str(normalized_url),
                label=str(normalized_url),
            )

            if input_node is not None:
                _add_edge(
                    edges,
                    source=input_node,
                    relationship=EvidenceGraphEdgeType.INPUT_CONTAINS,
                    target=url_node,
                )

            _add_edge(
                edges,
                source=evidence_node,
                relationship=EvidenceGraphEdgeType.VERIFIED_BY,
                target=url_node,
            )

            hostname = item.raw_payload.get("hostname") if item.raw_payload else None

            if hostname:
                domain_node = _add_node(
                    nodes,
                    investigation_id=investigation_id,
                    kind="domain",
                    node_type=EvidenceGraphNodeType.DOMAIN,
                    value=str(hostname),
                    label=str(hostname),
                )

                _add_edge(
                    edges,
                    source=url_node,
                    relationship=EvidenceGraphEdgeType.LINKS_TO,
                    target=domain_node,
                )

    return EvidenceGraph(
        investigation_id=str(investigation_id),
        nodes=list(nodes.values()),
        edges=list(edges.values()),
    )
