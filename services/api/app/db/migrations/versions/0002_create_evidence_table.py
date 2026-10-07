"""Create evidence table

Revision ID: 0002_evidence
Revises: 0001_initial
Create Date: 2026-10-07 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002_evidence"
down_revision: str | None = "0001_initial"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "investigation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="model"),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="SUCCESS"),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_evidence_id"), "evidence", ["id"], unique=False)
    op.create_index(op.f("ix_evidence_investigation_id"), "evidence", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_evidence_type"), "evidence", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_type"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_investigation_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_id"), table_name="evidence")
    op.drop_table("evidence")
