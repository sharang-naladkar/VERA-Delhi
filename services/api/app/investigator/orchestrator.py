"""Central VERA Investigator Orchestrator."""

import time
from uuid import UUID, uuid4

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger, investigation_id_ctx
from app.investigator.graph import InvestigatorGraphBuilder
from app.investigator.state import InvestigationState
from app.investigator.tools.registry import ToolRegistry, create_default_registry
from app.providers.llm import LLMProvider

logger = get_logger("app.investigator.orchestrator")


class VERAInvestigator:
    """
    The Single Central VERA Investigator orchestrating multi-step forensics
    through LangGraph and registered specialized tools.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        if llm_provider is None:
            from app.providers.factory import get_llm_provider
            llm_provider = get_llm_provider()
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry or create_default_registry(self.llm_provider)
        self.graph_builder = InvestigatorGraphBuilder(
            llm_provider=self.llm_provider,
            tool_registry=self.tool_registry,
        )
        self._compiled_graph = self.graph_builder.build()

    async def run_investigation(
        self,
        investigation_id: UUID,
        raw_input_text: str = "",
        input_type: str = "text",
        input_id: UUID | None = None,
        raw_input_reference: str | None = None,
        image_bytes: bytes | None = None,
        audio_bytes: bytes | None = None,
        video_bytes: bytes | None = None,
        media_bytes: bytes | None = None,
        regulatory_verification_request: dict[str, object] | None = None,
    ) -> InvestigationState:
        """
        Executes a controlled, deterministic multi-step investigation over LangGraph.
        """
        token = investigation_id_ctx.set(str(investigation_id))
        start_time = time.perf_counter()

        initial_state = InvestigationState(
            investigation_id=investigation_id,
            input_id=input_id or uuid4(),
            input_type=input_type,
            regulatory_verification_request=regulatory_verification_request,
            raw_input_reference=raw_input_reference,
            raw_input_text=raw_input_text or "",
            status=AnalysisStatus.PENDING,
            llm_metadata={
                "provider": self.llm_provider.provider_name,
                "model": getattr(self.llm_provider, "model", "default"),
            },
        )

        logger.info(
            f"Starting VERA investigation {investigation_id} with input length {len(raw_input_text)} chars",
            extra={"extra_fields": {"investigation_id": str(investigation_id), "input_type": input_type}},
        )

        try:
            graph_input = initial_state.to_graph_state()
            if image_bytes is not None:
                graph_input["image_bytes"] = image_bytes
            if audio_bytes is not None:
                graph_input["audio_bytes"] = audio_bytes
            if video_bytes is not None:
                graph_input["video_bytes"] = video_bytes
            if media_bytes is not None:
                graph_input["media_bytes"] = media_bytes

            result_state_dict = await self._compiled_graph.ainvoke(graph_input)
            final_state = InvestigationState.from_graph_state(result_state_dict)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception in VERA Investigator graph: {exc}",
                exc_info=True,
                extra={"extra_fields": {"investigation_id": str(investigation_id), "duration_ms": duration_ms}},
            )
            initial_state.add_error(f"Investigator execution failure: {exc}")
            initial_state.status = AnalysisStatus.FAILED
            initial_state.current_step = "failed"
            final_state = initial_state
        finally:
            investigation_id_ctx.reset(token)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"Completed investigation {investigation_id} in {duration_ms}ms with status {final_state.status.value}",
            extra={
                "extra_fields": {
                    "investigation_id": str(investigation_id),
                    "status": final_state.status.value,
                    "duration_ms": duration_ms,
                    "evidence_count": len(final_state.evidence),
                }
            },
        )
        return final_state
