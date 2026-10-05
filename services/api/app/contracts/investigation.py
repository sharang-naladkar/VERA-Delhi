"""Investigation Request and Response Data Contracts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateInvestigationRequest(BaseModel):
    """Payload to initiate a new investigation."""

    title: str | None = Field(None, max_length=255, description="Optional brief title")
    description: str | None = Field(None, description="Optional description of suspicious activity")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Initial context metadata")


class InvestigationResponse(BaseModel):
    """Standardized representation of an investigation record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    description: str | None = None
    status: str
    vera_version: str
    created_at: datetime
    updated_at: datetime
