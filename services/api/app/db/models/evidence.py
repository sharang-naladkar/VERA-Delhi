"""Evidence Database Model."""

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EvidenceModel(Base):
    """Evidence database table storing forensic artifacts and signals."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="model")
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUCCESS")
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Converts model attributes to dictionary."""
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "input_id": self.input_id,
            "type": self.type,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_version": self.source_version,
            "status": self.status,
            "raw_payload": self.raw_payload,
            "metadata": self.metadata_json,
            "created_at": self.created_at,
        }
