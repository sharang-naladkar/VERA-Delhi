from uuid import uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.services.evidence_graph import build_evidence_graph


def test_evidence_graph_builder_is_deterministic_and_correlates_url_evidence():
    investigation_id = uuid4()

    evidence = EvidenceContract(
        investigation_id=investigation_id,
        input_id=None,
        type=EvidenceType.URL_ANALYSIS,
        category="deterministic_url_analysis",
        severity=SeverityLevel.HIGH,
        confidence=1.0,
        description="Deterministic URL analysis detected suspicious indicators.",
        source_type="heuristic",
        source_name="url_intelligence",
        source_version="1.0.0",
        status=AnalysisStatus.SUCCESS,
        raw_payload={
            "hostname": "secure-invest.example.com",
        },
        metadata={
            "normalized_url": "https://secure-invest.example.com/login",
            "indicators": ["suspicious_keywords", "deep_subdomain_structure"],
        },
    )

    kwargs = dict(
        investigation_id=investigation_id,
        input_id=None,
        raw_input_reference="input-1",
        raw_input_text="https://secure-invest.example.com/login",
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
                "claim": "Guaranteed returns",
                "source_text": "Guaranteed returns",
                "confidence": 0.9,
            }
        ],
        indicators=["suspicious_keywords"],
        evidence=[evidence],
    )

    first = build_evidence_graph(**kwargs)
    second = build_evidence_graph(**kwargs)

    assert first.model_dump() == second.model_dump()

    node_types = {node.node_type for node in first.nodes}
    assert "investigation" in node_types
    assert "input" in node_types
    assert "person" in node_types
    assert "claim" in node_types
    assert "risk_signal" in node_types
    assert "evidence" in node_types
    assert "url" in node_types
    assert "domain" in node_types

    relationships = {edge.relationship for edge in first.edges}
    assert "INPUT_CONTAINS" in relationships
    assert "CLAIMS" in relationships
    assert "INDICATES" in relationships
    assert "VERIFIED_BY" in relationships
    assert "LINKS_TO" in relationships

    assert "RESOLVES_TO" not in relationships


def test_evidence_graph_builder_skips_incomplete_entities_and_claims():
    investigation_id = uuid4()

    graph = build_evidence_graph(
        investigation_id=investigation_id,
        input_id=None,
        raw_input_reference=None,
        raw_input_text="test input",
        entities=[
            {
                "entity_type": "person",
                "name": "",
                "normalized_value": "missing-name",
            }
        ],
        claims=[
            {
                "claim_type": "other",
                "claim": "",
            }
        ],
        indicators=["", "indicator_a", "indicator_a"],
        evidence=[],
    )

    assert len(
        [node for node in graph.nodes if node.node_type == "person"]
    ) == 0
    assert len(
        [node for node in graph.nodes if node.node_type == "claim"]
    ) == 0

    indicator_nodes = [
        node for node in graph.nodes if node.node_type == "risk_signal"
    ]
    assert len(indicator_nodes) == 1
