"""Contracts for regulatory knowledge retrieval and citation."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RegulatoryDocument(BaseModel):
    """Metadata describing an authoritative regulatory document."""

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    source_url: str | None = None
    document_reference: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    document_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegulatoryChunk(BaseModel):
    """A retrievable section of a regulatory document."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    text: str = Field(..., min_length=1)
    section: str | None = None
    page: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegulatorySearchResult(BaseModel):
    """A regulatory retrieval result with provenance."""

    chunk: RegulatoryChunk
    document: RegulatoryDocument
    score: float = Field(default=0.0, ge=0.0)
    matched_terms: list[str] = Field(default_factory=list)


class RegulatorySearchResponse(BaseModel):
    """Response from regulatory knowledge retrieval."""

    query: str = Field(..., min_length=1)
    results: list[RegulatorySearchResult] = Field(default_factory=list)
    source_available: bool = False
    status: str = "UNAVAILABLE"
    metadata: dict[str, Any] = Field(default_factory=dict)