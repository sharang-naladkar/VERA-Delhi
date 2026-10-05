"""Initial investigations table

Revision ID: 0001_initial
Revises: None
Create Date: 2026-10-05 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Use generic sa.UUID/String for cross-db compatibility
    op.create_table(
        "investigations",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="created"),
        sa.Column("vera_version", sa.String(length=20), nullable=False),
        sa.Column("context_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigations_id"), "investigations", ["id"], unique=False)
    op.create_index(op.f("ix_investigations_status"), "investigations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_investigations_status"), table_name="investigations")
    op.drop_index(op.f("ix_investigations_id"), table_name="investigations")
    op.drop_table("investigations")
