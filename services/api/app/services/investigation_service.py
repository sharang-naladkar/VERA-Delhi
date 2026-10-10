"""Investigation Business Logic Service orchestrating VERA Investigator and persistence."""

import uuid
from uuid import UUID
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.investigation import (
    CreateInvestigationRequest,
    InvestigationResponse,
)
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
        self.investigator = investigator or VERAInvestigator(
            llm_provider=llm_provider
        )

    async def create_investigation(
        self,
        payload: CreateInvestigationRequest | None = None,
    ) -> InvestigationResponse:
        """
        Create and execute an investigation.

        If text or a regulatory verification request is provided,
        execute the central VERA Investigator over LangGraph.
        """

        investigation_id = uuid.uuid4()

        title = payload.title if payload else None
        description = payload.description if payload else None
        input_type = payload.input_type if payload else "text"

        metadata: dict[str, Any] = (
            dict(payload.metadata)
            if payload and payload.metadata
            else {}
        )

        text_to_investigate = (
            payload.text
            if payload and payload.text is not None
            else None
        )

        # Preserve support for creating an empty investigation stub.
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

            try:
                self.db.add(investigation)
                await self.db.commit()
                await self.db.refresh(investigation)
            except Exception:
                await self.db.rollback()
                logger.exception(
                    "Failed to persist empty investigation %s",
                    investigation_id,
                )
                raise

            logger.info(
                "Created empty investigation stub %s",
                investigation.id,
            )

            return InvestigationResponse.model_validate(
                investigation.to_dict()
            )

        # Execute the investigator graph.
        final_state = await self.investigator.run_investigation(
            investigation_id=investigation_id,
            raw_input_text=text_to_investigate or "",
            input_type=input_type,
            regulatory_verification_request=(
                payload.regulatory_verification_request.model_dump(
                    mode="json"
                )
                if payload
                and payload.regulatory_verification_request
                else None
            ),
        )

        # Extract the latest assistant summary.
        result_summary = None

        for msg in reversed(final_state.messages):
            if msg.get("role") == "assistant":
                result_summary = msg.get("content")
                break

        # Read the assessment and report produced by the graph.
        risk_assessment = getattr(
            final_state,
            "risk_assessment",
            None,
        )

        investigation_report = getattr(
            final_state,
            "investigation_report",
            None,
        )

        # Preserve the graph state and outputs in context metadata.
        metadata["input_text"] = text_to_investigate
        metadata["evidence_count"] = len(final_state.evidence)
        metadata["evidence"] = final_state.evidence
        metadata["result_summary"] = result_summary
        metadata["state"] = final_state.to_graph_state()
        metadata["risk_assessment"] = risk_assessment
        metadata["investigation_report"] = investigation_report

        # IMPORTANT:
        # Insert and flush the parent investigation before adding evidence.
        # Evidence rows have a foreign key to investigations.id.
        investigation = InvestigationModel(
            id=investigation_id,
            title=title or f"Investigation {str(investigation_id)[:8]}",
            description=description,
            status=final_state.status.value,
            vera_version=settings.APP_VERSION,
            context_metadata=metadata,
        )

        try:
            self.db.add(investigation)

            # Insert the parent row without committing the transaction.
            await self.db.flush()

            # Now persist evidence referencing the existing parent row.
            for ev in final_state.evidence:
                raw_ev_id = ev.get("id")

                ev_id = (
                    uuid.UUID(raw_ev_id)
                    if isinstance(raw_ev_id, str)
                    else raw_ev_id
                )

                if ev_id is None:
                    ev_id = uuid.uuid4()

                raw_input_id = ev.get("input_id")

                inp_id = (
                    uuid.UUID(raw_input_id)
                    if isinstance(raw_input_id, str)
                    else raw_input_id
                )

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

            # Commit parent and evidence atomically.
            await self.db.commit()
            await self.db.refresh(investigation)

        except Exception:
            await self.db.rollback()
            logger.exception(
                "Failed to persist investigation %s and its evidence",
                investigation_id,
            )
            raise

        logger.info(
            "Persisted investigation %s with status %s and %s evidence records",
            investigation.id,
            investigation.status,
            len(final_state.evidence),
        )

        return InvestigationResponse.model_validate(
            investigation.to_dict()
        )

    async def get_investigation_by_id(
        self,
        investigation_id: UUID,
    ) -> InvestigationResponse:
        """Fetch an investigation and its associated evidence."""

        stmt = select(InvestigationModel).where(
            InvestigationModel.id == investigation_id
        )

        result = await self.db.execute(stmt)
        investigation = result.scalar_one_or_none()

        if not investigation:
            raise NotFoundError(
                f"Investigation with ID '{investigation_id}' not found."
            )

        metadata = dict(investigation.context_metadata or {})

        # Recover evidence from the relational table for older records
        # that do not contain an evidence snapshot in context metadata.
        if "evidence" not in metadata:
            ev_stmt = select(EvidenceModel).where(
                EvidenceModel.investigation_id == investigation_id
            )

            ev_result = await self.db.execute(ev_stmt)
            evidence_models = ev_result.scalars().all()

            metadata["evidence"] = [
                evidence.to_dict()
                for evidence in evidence_models
            ]

            metadata["evidence_count"] = len(evidence_models)

        # Recover report fields from graph state for older records.
        graph_state = metadata.get("state") or {}

        if isinstance(graph_state, dict):
            if not metadata.get("risk_assessment"):
                metadata["risk_assessment"] = graph_state.get(
                    "risk_assessment"
                )

            if not metadata.get("investigation_report"):
                metadata["investigation_report"] = graph_state.get(
                    "investigation_report"
                )

        # Assign a new dictionary so SQLAlchemy sees the metadata update.
        # This is used for response serialization; it does not commit changes.
        investigation.context_metadata = metadata

        return InvestigationResponse.model_validate(
            investigation.to_dict()
        )