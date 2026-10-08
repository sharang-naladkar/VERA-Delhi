"""Deterministic evidence graph contracts for VERA."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceGraphNodeType(StrEnum):
    """Supported node types in the evidence graph."""

    INVESTIGATION = "investigation"
    INPUT = "input"
    URL = "url"
    DOMAIN = "domain"
    IP = "ip"
    PERSON = "person"
    ORGANIZATION = "organization"
    PHONE = "phone"
    UPI = "upi"
    APK = "apk"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    REGULATORY_RESULT = "regulatory_result"
    RISK_SIGNAL = "risk_signal"


class EvidenceGraphEdgeType(StrEnum):
    """Supported deterministic relationships between graph nodes."""

    INPUT_CONTAINS = "INPUT_CONTAINS"
    CLAIMS = "CLAIMS"
    LINKS_TO = "LINKS_TO"
    RESOLVES_TO = "RESOLVES_TO"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    VERIFIED_BY = "VERIFIED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    SUPPORTED_BY = "SUPPORTED_BY"
    PRODUCES = "PRODUCES"
    INDICATES = "INDICATES"


class EvidenceGraphNode(BaseModel):
    """A typed node in the investigation evidence graph."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    node_type: EvidenceGraphNodeType
    label: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(BaseModel):
    """A deterministic relationship between two graph nodes."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., min_length=1)
    source_type: EvidenceGraphNodeType
    relationship: EvidenceGraphEdgeType
    target_id: str = Field(..., min_length=1)
    target_type: EvidenceGraphNodeType
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraph(BaseModel):
    """Complete deterministic evidence graph for an investigation."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list)
