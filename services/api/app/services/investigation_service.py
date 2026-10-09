"""Investigation Business Logic Service orchestrating VERA Investigator and persistence."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.investigation import CreateInvestigationRequest, InvestigationResponse
from app.contracts.status import AnalysisStatus
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.models.evidence import EvidenceModel
from app.db.models.investigation import InvestigationModel
from app.investigator.orchestrator import VERAInvestigator
from app.providers.llm import LLMProvider

logger = get_logger("app.investigation_service")


class InvestigationService:
    """Service layer coordinating persistence and central agentic investigations."""

    def __init__(
        self,
        db: AsyncSession,
        investigator: VERAInvestigator | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.investigator = investigator or VERAInvestigator(llm_provider=llm_provider)

    async def create_investigation(
        self, payload: CreateInvestigationRequest | None = None
    ) -> InvestigationResponse:
        """
        Creates and executes a new forensic investigation workflow record.
        If text or description is provided, runs the central VERA Investigator over LangGraph.
        """
        investigation_id = uuid.uuid4()
        title = payload.title if payload else None
        description = payload.description if payload else None
        input_type = payload.input_type if payload else "text"
        metadata = dict(payload.metadata) if payload and payload.metadata else {}

        # Determine target text to investigate
        text_to_investigate = payload.text if (payload and payload.text is not None) else None

        # If no text provided, create initial 'created' placeholder (Phase 01 compat)
        if (
            text_to_investigate is None
            and not (
                payload
                and payload.regulatory_verification_request is not None
            )
        ):
            investigation = InvestigationModel(
                id=investigation_id,
                title=title,
                description=description,
                status="created",
                vera_version=settings.APP_VERSION,
                context_metadata=metadata,
            )
            self.db.add(investigation)
            await self.db.commit()
            await self.db.refresh(investigation)
            logger.info(f"Created empty investigation stub {investigation.id}")
            return InvestigationResponse.model_validate(investigation.to_dict())

        # Execute Central VERA Investigator over LangGraph
        final_state = await self.investigator.run_investigation(
            investigation_id=investigation_id,
            raw_input_text=text_to_investigate or "",
            input_type=input_type,
            regulatory_verification_request=(
                payload.regulatory_verification_request.model_dump(mode="json")
                if payload and payload.regulatory_verification_request
                else None
            ),
        )

        # Prepare summary from messages
        result_summary = None
        for msg in reversed(final_state.messages):
            if msg.get("role") == "assistant":
                result_summary = msg.get("content")
                break

        # Persist evidence to relational table
        for ev in final_state.evidence:
            ev_id = uuid.UUID(ev["id"]) if isinstance(ev["id"], str) else ev["id"]
            inp_id = uuid.UUID(ev["input_id"]) if ev.get("input_id") else None
            db_ev = EvidenceModel(
                id=ev_id,
                investigation_id=investigation_id,
                input_id=inp_id,
                type=ev.get("type", "risk_signal"),
                category=ev.get("category", "general"),
                severity=ev.get("severity", "low"),
                confidence=float(ev.get("confidence", 0.0)),
                description=ev.get("description", ""),
                source_type=ev.get("source_type", "model"),
                source_name=ev.get("source_name", "investigator"),
                source_version=ev.get("source_version"),
                status=ev.get("status", "SUCCESS"),
                raw_payload=ev.get("raw_payload"),
                metadata_json=ev.get("metadata", {}),
            )
            self.db.add(db_ev)

        # Update context metadata with state snapshot
        metadata["input_text"] = text_to_investigate
        metadata["evidence_count"] = len(final_state.evidence)
        metadata["evidence"] = final_state.evidence
        metadata["result_summary"] = result_summary
        metadata["state"] = final_state.to_graph_state()

        investigation = InvestigationModel(
            id=investigation_id,
            title=title or f"Investigation {str(investigation_id)[:8]}",
            description=description,
            status=final_state.status.value,
            vera_version=settings.APP_VERSION,
            context_metadata=metadata,
        )

        self.db.add(investigation)
        await self.db.commit()
        await self.db.refresh(investigation)

        logger.info(
            f"Persisted investigation {investigation.id} with status {investigation.status} and {len(final_state.evidence)} evidence records"
        )
        return InvestigationResponse.model_validate(investigation.to_dict())

    async def get_investigation_by_id(self, investigation_id: UUID) -> InvestigationResponse:
        """Fetch investigation and associated evidence by primary key UUID."""
        stmt = select(InvestigationModel).where(InvestigationModel.id == investigation_id)
        result = await self.db.execute(stmt)
        investigation = result.scalar_one_or_none()

        if not investigation:
            raise NotFoundError(f"Investigation with ID '{investigation_id}' not found.")

        # Also retrieve evidence items if not populated in context_metadata
        if "evidence" not in investigation.context_metadata:
            ev_stmt = select(EvidenceModel).where(EvidenceModel.investigation_id == investigation_id)
            ev_result = await self.db.execute(ev_stmt)
            evidence_models = ev_result.scalars().all()
            investigation.context_metadata["evidence"] = [e.to_dict() for e in evidence_models]
            investigation.context_metadata["evidence_count"] = len(evidence_models)

        return InvestigationResponse.model_validate(investigation.to_dict())
