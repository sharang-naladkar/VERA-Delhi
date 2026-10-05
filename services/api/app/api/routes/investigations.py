"""Investigation Management Endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_investigation_service
from app.contracts.investigation import CreateInvestigationRequest, InvestigationResponse
from app.core.logging import investigation_id_ctx
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/v1/investigations", tags=["Investigations"])


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new investigation",
)
async def create_investigation(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    payload: CreateInvestigationRequest | None = None,
) -> InvestigationResponse:
    """Initialize a new fraud investigation workflow."""
    return await service.create_investigation(payload)


@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get investigation by ID",
)
async def get_investigation(
    investigation_id: UUID,
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationResponse:
    """Retrieve details and status of an existing investigation."""
    investigation_id_ctx.set(str(investigation_id))
    return await service.get_investigation_by_id(investigation_id)
