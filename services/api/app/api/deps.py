"""FastAPI route dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.providers.factory import get_llm_provider
from app.providers.llm import LLMProvider
from app.services.investigation_service import InvestigationService

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_llm_provider_dep() -> LLMProvider:
    """Dependency injector for LLM provider."""
    return get_llm_provider()


def get_investigation_service(
    db: DatabaseSession,
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider_dep)],
) -> InvestigationService:
    """Dependency injector for investigation service."""
    return InvestigationService(db=db, llm_provider=llm_provider)
