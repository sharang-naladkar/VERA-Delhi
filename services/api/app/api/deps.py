"""FastAPI route dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.investigation_service import InvestigationService

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_investigation_service(db: DatabaseSession) -> InvestigationService:
    """Dependency injector for investigation service."""
    return InvestigationService(db=db)
