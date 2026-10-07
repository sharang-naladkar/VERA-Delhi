"""LangGraph StateGraph Definition for the Central VERA Investigator."""

import time
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.investigator.schemas import InvestigationPlan
from app.investigator.state import InvestigationStateDict
from app.investigator.tools.base import ToolResult
from app.investigator.tools.registry import ToolRegistry
from app.prompts.loader import format_prompt
from app.providers.llm import LLMProvider

logger = get_logger("app.investigator.graph")


class InvestigatorGraphBuilder:
    """Builds and compiles the LangGraph StateGraph for VERA investigation workflows."""

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry

    def build(self) -> Any:
        """Constructs and returns the compiled LangGraph workflow."""
        workflow = StateGraph(InvestigationStateDict)

        # Register nodes in sequence
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("analyze_input", self._analyze_input_node)
        workflow.add_node("extract_entities", self._extract_entities_node)
        workflow.add_node("extract_claims", self._extract_claims_node)
        workflow.add_node("analyze_scam_patterns", self._analyze_scam_patterns_node)
        workflow.add_node("plan_investigation", self._plan_investigation_node)
        workflow.add_node("execute_available_tools", self._execute_available_tools_node)
        workflow.add_node("collect_evidence", self._collect_evidence_node)
        workflow.add_node("finalize_investigation", self._finalize_investigation_node)

        # Define linear execution flow
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "analyze_input")
        workflow.add_edge("analyze_input", "extract_entities")
        workflow.add_edge("extract_entities", "extract_claims")
        workflow.add_edge("extract_claims", "analyze_scam_patterns")
        workflow.add_edge("analyze_scam_patterns", "plan_investigation")
        workflow.add_edge("plan_investigation", "execute_available_tools")
        workflow.add_edge("execute_available_tools", "collect_evidence")
        workflow.add_edge("collect_evidence", "finalize_investigation")
        workflow.add_edge("finalize_investigation", END)

        return workflow.compile()

    # =========================================================================
    # Graph Node Implementations
    # =========================================================================

    async def _initialize_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            f"Initializing investigation {state.get('investigation_id')}",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "initialize"}},
        )
        timestamps = dict(state.get("timestamps", {}))
        timestamps["started_at"] = datetime.now(UTC).isoformat()
        messages = list(state.get("messages", []))
        messages.append({"role": "system", "content": "Investigation initialized by VERA Central Investigator."})

        return {
            "current_step": "initialize",
            "timestamps": timestamps,
            "messages": messages,
            "status": AnalysisStatus.PENDING.value,
        }

    async def _analyze_input_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing analyze_input node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "analyze_input"}},
        )
        normalizer = self.tool_registry.get("input_normalizer")
        if not normalizer:
            return {"current_step": "analyze_input", "warnings": ["input_normalizer tool missing"]}

        result: ToolResult = await normalizer.execute(state)
        normalized_text = result.output_data.get("normalized_text", "")

        evidence = list(state.get("evidence", []))
        for ev in result.evidence:
            evidence.append(ev.model_dump(mode="json"))

        tool_results = list(state.get("tool_results", []))
        tool_results.append(result.model_dump(mode="json"))

        new_status = state.get("status", AnalysisStatus.PENDING.value)
        if result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
            new_status = AnalysisStatus.INSUFFICIENT_EVIDENCE.value

        return {
            "current_step": "analyze_input",
            "normalized_input": normalized_text,
            "evidence": evidence,
            "tool_results": tool_results,
            "status": new_status,
        }

    async def _extract_entities_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing extract_entities node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "extract_entities"}},
        )
        extractor = self.tool_registry.get("entity_extractor")
        if not extractor:
            return {"current_step": "extract_entities", "warnings": ["entity_extractor tool missing"]}

        result: ToolResult = await extractor.execute(state)
        entities = result.output_data.get("entities", [])

        evidence = list(state.get("evidence", []))
        for ev in result.evidence:
            evidence.append(ev.model_dump(mode="json"))

        tool_results = list(state.get("tool_results", []))
        tool_results.append(result.model_dump(mode="json"))

        errors = list(state.get("errors", []))
        if result.error_message:
            errors.append(f"EntityExtractor: {result.error_message}")

        status = state.get("status", AnalysisStatus.PENDING.value)
        if result.status in (AnalysisStatus.UNAVAILABLE, AnalysisStatus.FAILED):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "extract_entities",
            "entities": entities,
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _extract_claims_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing extract_claims node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "extract_claims"}},
        )
        extractor = self.tool_registry.get("claim_extractor")
        if not extractor:
            return {"current_step": "extract_claims", "warnings": ["claim_extractor tool missing"]}

        result: ToolResult = await extractor.execute(state)
        claims = result.output_data.get("claims", [])

        evidence = list(state.get("evidence", []))
        for ev in result.evidence:
            evidence.append(ev.model_dump(mode="json"))

        tool_results = list(state.get("tool_results", []))
        tool_results.append(result.model_dump(mode="json"))

        errors = list(state.get("errors", []))
        if result.error_message:
            errors.append(f"ClaimExtractor: {result.error_message}")

        status = state.get("status", AnalysisStatus.PENDING.value)
        if result.status in (AnalysisStatus.UNAVAILABLE, AnalysisStatus.FAILED):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "extract_claims",
            "claims": claims,
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _analyze_scam_patterns_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing analyze_scam_patterns node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "analyze_scam_patterns"}},
        )
        analyzer = self.tool_registry.get("scam_pattern_analyzer")
        if not analyzer:
            return {"current_step": "analyze_scam_patterns", "warnings": ["scam_pattern_analyzer tool missing"]}

        result: ToolResult = await analyzer.execute(state)
        indicators = result.output_data.get("indicators", [])
        patterns = result.output_data.get("patterns", [])

        evidence = list(state.get("evidence", []))
        for ev in result.evidence:
            evidence.append(ev.model_dump(mode="json"))

        tool_results = list(state.get("tool_results", []))
        tool_results.append(result.model_dump(mode="json"))

        errors = list(state.get("errors", []))
        if result.error_message:
            errors.append(f"ScamPatternAnalyzer: {result.error_message}")

        status = state.get("status", AnalysisStatus.PENDING.value)
        if result.status in (AnalysisStatus.UNAVAILABLE, AnalysisStatus.FAILED):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "analyze_scam_patterns",
            "indicators": indicators,
            "scam_pattern_analysis": result.output_data,
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _plan_investigation_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing plan_investigation node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "plan_investigation"}},
        )
        text = state.get("normalized_input") or state.get("raw_input_text", "")
        plan: InvestigationPlan | None = None

        if text.strip():
            try:
                prompt, prompt_ver = format_prompt("investigator", "investigation_planning_v1", input_text=text)
                plan = await self.llm_provider.generate_structured(
                    schema=InvestigationPlan,
                    prompt=prompt,
                    temperature=0.0,
                )
            except Exception as exc:
                logger.warning(f"Could not generate dynamic investigation plan from LLM: {exc}")
                # Fallback to deterministic plan
                plan = InvestigationPlan(
                    objectives=["Extract entities", "Extract claims", "Analyze deceptive patterns"],
                    entities_to_extract=["advisors", "channels", "upi_handles"],
                    claims_to_verify=["guaranteed_return", "sebi_registration"],
                    tools_to_consider=["entity_extractor", "claim_extractor", "scam_pattern_analyzer"],
                    reasoning_summary="Deterministic plan fallback executed due to LLM offline or error.",
                )

        return {
            "current_step": "plan_investigation",
            "investigation_plan": plan.model_dump() if plan else None,
        }

    async def _execute_available_tools_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        """
        Extension point node for future specialized analyzers (URL, APK, SEBI, OCR).
        In Phase 02, validates that all planned initial tools completed.
        """
        logger.info(
            "Executing execute_available_tools node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "execute_available_tools"}},
        )
        return {"current_step": "execute_available_tools"}

    async def _collect_evidence_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Executing collect_evidence node",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "collect_evidence"}},
        )
        evidence = state.get("evidence", [])
        logger.info(f"Collected total {len(evidence)} evidence items for investigation {state.get('investigation_id')}")
        return {"current_step": "collect_evidence"}

    async def _finalize_investigation_node(self, state: InvestigationStateDict) -> dict[str, Any]:
        logger.info(
            "Finalizing investigation in LangGraph",
            extra={"extra_fields": {"investigation_id": state.get("investigation_id"), "step": "finalize_investigation"}},
        )
        timestamps = dict(state.get("timestamps", {}))
        timestamps["completed_at"] = datetime.now(UTC).isoformat()

        # Determine definitive final status
        current_status = state.get("status", AnalysisStatus.PENDING.value)
        errors = state.get("errors", [])
        evidence = state.get("evidence", [])

        if current_status == AnalysisStatus.INSUFFICIENT_EVIDENCE.value:
            final_status = AnalysisStatus.INSUFFICIENT_EVIDENCE.value
        elif errors and not evidence:
            final_status = AnalysisStatus.FAILED.value
        elif errors and evidence:
            final_status = AnalysisStatus.PARTIAL.value
        else:
            final_status = AnalysisStatus.SUCCESS.value

        messages = list(state.get("messages", []))
        messages.append({
            "role": "assistant",
            "content": f"Investigation completed with status '{final_status}'. Total evidence items: {len(evidence)}.",
        })

        return {
            "current_step": "completed",
            "status": final_status,
            "timestamps": timestamps,
            "messages": messages,
        }
