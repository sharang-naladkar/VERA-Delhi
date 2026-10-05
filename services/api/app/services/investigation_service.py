"""Investigation Business Logic Service."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.investigation import CreateInvestigationRequest, InvestigationResponse
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.models.investigation import InvestigationModel

logger = get_logger("app.investigation_service")


class InvestigationService:
    """Service layer for managing investigation records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_investigation(
        self, payload: CreateInvestigationRequest | None = None
    ) -> InvestigationResponse:
        """Create and persist a new investigation entity."""
        title = payload.title if payload else None
        description = payload.description if payload else None
        metadata = payload.metadata if payload else {}

        investigation = InvestigationModel(
            id=uuid.uuid4(),
            title=title,
            description=description,
            status="created",
            vera_version=settings.APP_VERSION,
            context_metadata=metadata,
        )

        self.db.add(investigation)
        await self.db.commit()
        await self.db.refresh(investigation)

        logger.info(
            f"Created investigation {investigation.id}",
            extra={
                "extra_fields": {
                    "investigation_id": str(investigation.id),
                    "status": investigation.status,
                }
            },
        )

        return InvestigationResponse.model_validate(investigation.to_dict())

    async def get_investigation_by_id(self, investigation_id: UUID) -> InvestigationResponse:
        """Fetch investigation by its primary key UUID."""
        stmt = select(InvestigationModel).where(InvestigationModel.id == investigation_id)
        result = await self.db.execute(stmt)
        investigation = result.scalar_one_or_none()

        if not investigation:
            raise NotFoundError(f"Investigation with ID '{investigation_id}' not found.")

        return InvestigationResponse.model_validate(investigation.to_dict())
