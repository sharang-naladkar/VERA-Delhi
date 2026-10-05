"""Tests for JSON Schemas and Contract Validation."""

import json
import uuid
from pathlib import Path

import jsonschema

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel


def get_contracts_dir() -> Path:
    # Walk up to find contracts directory
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = curr / "contracts" / "schemas"
        if candidate.exists():
            return candidate
        curr = curr.parent
    raise FileNotFoundError("Contracts directory not found")


def test_evidence_pydantic_contract() -> None:
    """Verify EvidenceContract instantiates and validates correctly."""
    inv_id = uuid.uuid4()
    evidence = EvidenceContract(
        investigation_id=inv_id,
        type=EvidenceType.RISK_SIGNAL,
        category="unregistered_advisor",
        severity=SeverityLevel.HIGH,
        confidence=0.92,
        description="Advisor is not registered in the SEBI database.",
        source_type="database",
        source_name="sebi_registry_checker",
        source_version="1.0.0",
        status=AnalysisStatus.SUCCESS,
        raw_payload={"registration_number_claimed": "INZ00012345"},
    )

    assert evidence.investigation_id == inv_id
    assert evidence.confidence == 0.92
    assert evidence.severity == SeverityLevel.HIGH
    assert evidence.status == AnalysisStatus.SUCCESS

    # Convert to dict and verify serializability
    dumped = evidence.model_dump(mode="json")
    assert dumped["type"] == "risk_signal"
    assert dumped["status"] == "SUCCESS"


def test_json_schemas_validation() -> None:
    """Verify contracts/schemas/*.json can validate valid payloads."""
    schemas_dir = get_contracts_dir()

    # 1. Test investigation.json
    inv_schema = json.loads((schemas_dir / "investigation.json").read_text(encoding="utf-8"))
    valid_inv = {
        "id": str(uuid.uuid4()),
        "title": "Test Investigation",
        "description": "Details",
        "status": "created",
        "vera_version": "0.1.0",
        "metadata": {},
        "created_at": "2026-10-05T12:00:00Z",
        "updated_at": "2026-10-05T12:00:00Z",
    }
    jsonschema.validate(instance=valid_inv, schema=inv_schema)

    # 2. Test evidence.json
    evidence_schema = json.loads((schemas_dir / "evidence.json").read_text(encoding="utf-8"))
    valid_evidence = {
        "id": str(uuid.uuid4()),
        "investigation_id": str(uuid.uuid4()),
        "input_id": None,
        "type": "risk_signal",
        "category": "urgency_tactic",
        "severity": "medium",
        "confidence": 0.85,
        "description": "Artificial urgency created with timer.",
        "source_type": "heuristic",
        "source_name": "claim_parser",
        "source_version": "0.1.0",
        "status": "SUCCESS",
        "raw_payload": None,
        "metadata": {},
        "created_at": "2026-10-05T12:00:00Z",
    }
    jsonschema.validate(instance=valid_evidence, schema=evidence_schema)
