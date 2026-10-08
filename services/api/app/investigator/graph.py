"""LangGraph StateGraph Definition for the Central VERA Investigator."""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.investigator.schemas import InvestigationPlan
from app.investigator.state import InvestigationStateDict
from app.investigator.tools.base import ToolResult
from app.investigator.tools.registry import ToolRegistry
from app.prompts.loader import format_prompt
from app.providers.llm import LLMProvider
from app.services.risk_engine import calculate_risk

logger = get_logger("app.investigator.graph")


class InvestigatorGraphBuilder:
    """Builds and compiles the LangGraph StateGraph for VERA investigation workflows."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ) -> None:
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
        workflow.add_node(
            "analyze_scam_patterns",
            self._analyze_scam_patterns_node,
        )
        workflow.add_node("plan_investigation", self._plan_investigation_node)
        workflow.add_node(
            "execute_available_tools",
            self._execute_available_tools_node,
        )
        workflow.add_node("collect_evidence", self._collect_evidence_node)
        workflow.add_node("calculate_risk", self._calculate_risk_node)
        workflow.add_node(
            "finalize_investigation",
            self._finalize_investigation_node,
        )

        # Define linear execution flow
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "analyze_input")
        workflow.add_edge("analyze_input", "extract_entities")
        workflow.add_edge("extract_entities", "extract_claims")
        workflow.add_edge("extract_claims", "analyze_scam_patterns")
        workflow.add_edge("analyze_scam_patterns", "plan_investigation")
        workflow.add_edge("plan_investigation", "execute_available_tools")
        workflow.add_edge("execute_available_tools", "collect_evidence")
        workflow.add_edge("collect_evidence", "calculate_risk")
        workflow.add_edge("calculate_risk", "finalize_investigation")
        workflow.add_edge("finalize_investigation", END)

        return workflow.compile()

    # =========================================================================
    # Graph Node Implementations
    # =========================================================================

    async def _initialize_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            f"Initializing investigation {state.get('investigation_id')}",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "initialize",
                }
            },
        )

        timestamps = dict(state.get("timestamps", {}))
        timestamps["started_at"] = datetime.now(UTC).isoformat()

        messages = list(state.get("messages", []))
        messages.append(
            {
                "role": "system",
                "content": "Investigation initialized by VERA Central Investigator.",
            }
        )

        return {
            "current_step": "initialize",
            "timestamps": timestamps,
            "messages": messages,
            "status": AnalysisStatus.PENDING.value,
        }

    async def _analyze_input_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing analyze_input node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "analyze_input",
                }
            },
        )

        normalizer = self.tool_registry.get("input_normalizer")

        if not normalizer:
            return {
                "current_step": "analyze_input",
                "warnings": ["input_normalizer tool missing"],
            }

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

    async def _extract_entities_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing extract_entities node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "extract_entities",
                }
            },
        )

        extractor = self.tool_registry.get("entity_extractor")

        if not extractor:
            return {
                "current_step": "extract_entities",
                "warnings": ["entity_extractor tool missing"],
            }

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

        if result.status in (
            AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.FAILED,
        ):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "extract_entities",
            "entities": entities,
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _extract_claims_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing extract_claims node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "extract_claims",
                }
            },
        )

        extractor = self.tool_registry.get("claim_extractor")

        if not extractor:
            return {
                "current_step": "extract_claims",
                "warnings": ["claim_extractor tool missing"],
            }

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

        if result.status in (
            AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.FAILED,
        ):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "extract_claims",
            "claims": claims,
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _analyze_scam_patterns_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing analyze_scam_patterns node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "analyze_scam_patterns",
                }
            },
        )

        analyzer = self.tool_registry.get("scam_pattern_analyzer")

        if not analyzer:
            return {
                "current_step": "analyze_scam_patterns",
                "warnings": ["scam_pattern_analyzer tool missing"],
            }

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

        if result.status in (
            AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.FAILED,
        ):
            status = AnalysisStatus.PARTIAL.value

        return {
            "current_step": "analyze_scam_patterns",
            "indicators": indicators,
            "scam_pattern_analysis": {
                **result.output_data,
                "patterns": patterns,
            },
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    async def _plan_investigation_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing plan_investigation node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "plan_investigation",
                }
            },
        )

        text = state.get("normalized_input") or state.get("raw_input_text", "")
        plan: InvestigationPlan | None = None

        if text.strip():
            try:
                prompt, _prompt_ver = format_prompt(
                    "investigator",
                    "investigation_planning_v1",
                    input_text=text,
                )

                plan = await self.llm_provider.generate_structured(
                    schema=InvestigationPlan,
                    prompt=prompt,
                    temperature=0.0,
                )

            except Exception as exc:
                logger.warning(
                    f"Could not generate dynamic investigation plan from LLM: {exc}"
                )

                # Fallback to deterministic plan
                plan = InvestigationPlan(
                    objectives=[
                        "Extract entities",
                        "Extract claims",
                        "Analyze deceptive patterns",
                    ],
                    entities_to_extract=[
                        "advisors",
                        "channels",
                        "upi_handles",
                    ],
                    claims_to_verify=[
                        "guaranteed_return",
                        "sebi_registration",
                    ],
                    tools_to_consider=[
                        "entity_extractor",
                        "claim_extractor",
                        "scam_pattern_analyzer",
                    ],
                    reasoning_summary=(
                        "Deterministic plan fallback executed due to "
                        "LLM offline or error."
                    ),
                )

        return {
            "current_step": "plan_investigation",
            "investigation_plan": plan.model_dump() if plan else None,
        }

    async def _execute_available_tools_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        """
        Execute specialized forensic analyzers for the current investigation.

        Supported specialized paths:

        - URL: deterministic URL intelligence.
        - Image: OCR, face detection, deepfake detection.
        - Audio: speech-to-text.
        - Video: bounded frame sampling followed by frame-level deepfake
          analysis.
        - Multimodal: OCR, face detection, deepfake detection, transcription.

        URL routing is intentionally independent of ``input_type`` because
        URLs may currently arrive through the text-input path.

        Raw sampled video frame bytes are used only inside this node and are
        not returned into persistent investigation state.
        """

        logger.info(
            "Executing execute_available_tools node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "execute_available_tools",
                }
            },
        )

        input_type = str(state.get("input_type", "text")).lower()

        evidence = list(state.get("evidence", []))
        tool_results = list(state.get("tool_results", []))
        errors = list(state.get("errors", []))
        status = state.get("status", AnalysisStatus.PENDING.value)

        async def execute_tool(
            tool_name: str,
            tool_state: InvestigationStateDict,
            error_label: str | None = None,
        ) -> ToolResult | None:
            nonlocal status

            tool = self.tool_registry.get(tool_name)

            if not tool:
                message = f"{tool_name} tool missing"
                errors.append(message)
                status = AnalysisStatus.PARTIAL.value
                logger.warning(message)
                return None

            try:
                result: ToolResult = await tool.execute(dict(tool_state))

                for ev in result.evidence:
                    evidence.append(ev.model_dump(mode="json"))

                # Tool results are persisted in investigation state. Some
                # analyzers, especially video analysis, may carry internal
                # binary execution payloads that must never enter state.
                result_data = result.model_dump(mode="json")

                if tool_name == "video_analyzer":
                    output_data = result_data.get("output_data")

                    if isinstance(output_data, dict):
                        output_data.pop("_sampled_frames", None)

                tool_results.append(result_data)

                label = error_label or tool_name

                if result.error_message:
                    errors.append(f"{label}: {result.error_message}")

                if result.status in (
                    AnalysisStatus.UNAVAILABLE,
                    AnalysisStatus.FAILED,
                ):
                    status = AnalysisStatus.PARTIAL.value

                return result

            except Exception as exc:
                label = error_label or tool_name

                logger.error(
                    f"Error executing tool {tool_name} in graph: {exc}",
                    exc_info=True,
                )

                errors.append(f"{label} execution error: {exc}")
                status = AnalysisStatus.PARTIAL.value

                return None

        # ---------------------------------------------------------------------
        # URL
        # ---------------------------------------------------------------------
        #
        # URL input can arrive as:
        #   1. input_type == "url"
        #   2. raw_input_text containing a complete HTTP(S) URL
        #   3. normalized_input containing a complete HTTP(S) URL
        #
        # We only route to URL intelligence when the complete input itself is
        # a URL. A URL embedded inside a longer message remains a text
        # investigation and will be handled later by entity/claim intelligence.
        # ---------------------------------------------------------------------
        if self._is_url_input(state):
            await execute_tool(
                "url_intelligence",
                state,
                "URLIntelligence",
            )

        # ---------------------------------------------------------------------
        # IMAGE
        # ---------------------------------------------------------------------
        elif input_type == "image" or state.get("image_bytes"):
            await execute_tool(
                "ocr_analyzer",
                state,
                "OCR",
            )
            await execute_tool(
                "face_detector",
                state,
                "FaceDetector",
            )
            await execute_tool(
                "deepfake_detector",
                state,
                "DeepfakeDetector",
            )

        # ---------------------------------------------------------------------
        # AUDIO
        # ---------------------------------------------------------------------
        elif input_type == "audio" or state.get("audio_bytes"):
            await execute_tool(
                "audio_transcriber",
                state,
                "AudioTranscriber",
            )

        # ---------------------------------------------------------------------
        # VIDEO
        # ---------------------------------------------------------------------
        elif input_type == "video" or state.get("video_bytes"):
            video_result = await execute_tool(
                "video_analyzer",
                state,
                "VideoAnalyzer",
            )

            if video_result is not None:
                sampled_frames = video_result.output_data.get(
                    "_sampled_frames",
                    [],
                )

                for frame_number, frame in enumerate(sampled_frames):
                    frame_bytes = frame.get("frame_bytes")

                    if not frame_bytes:
                        errors.append(
                            "DeepfakeDetector: sampled frame "
                            f"{frame_number} has no image bytes"
                        )
                        status = AnalysisStatus.PARTIAL.value
                        continue

                    frame_state = dict(state)

                    # The deepfake tool expects image/media bytes.
                    # We deliberately analyze each sampled video frame
                    # as an image instead of passing the original MP4 bytes.
                    frame_state["input_type"] = "image"
                    frame_state["image_bytes"] = frame_bytes
                    frame_state["media_bytes"] = frame_bytes
                    frame_state["video_bytes"] = None

                    await execute_tool(
                        "deepfake_detector",
                        frame_state,
                        f"DeepfakeDetector frame {frame_number}",
                    )

        # ---------------------------------------------------------------------
        # MULTIMODAL
        # ---------------------------------------------------------------------
        elif input_type == "multimodal" or state.get("media_bytes"):
            await execute_tool(
                "ocr_analyzer",
                state,
                "OCR",
            )
            await execute_tool(
                "face_detector",
                state,
                "FaceDetector",
            )
            await execute_tool(
                "deepfake_detector",
                state,
                "DeepfakeDetector",
            )
            await execute_tool(
                "audio_transcriber",
                state,
                "AudioTranscriber",
            )

        else:
            logger.info(
                "No specialized URL or media analyzer selected for input",
                extra={
                    "extra_fields": {
                        "investigation_id": state.get("investigation_id"),
                        "input_type": input_type,
                    }
                },
            )

        return {
            "current_step": "execute_available_tools",
            "evidence": evidence,
            "tool_results": tool_results,
            "errors": errors,
            "status": status,
        }

    @staticmethod
    def _is_url_input(state: InvestigationStateDict) -> bool:
        """
        Determine whether the complete investigation input is an HTTP(S) URL.

        This deliberately avoids substring matching. For example:

            "Is this URL safe: https://example.com"

        remains a text investigation rather than being incorrectly routed to
        URLIntelligenceTool.

        A complete URL is accepted when:
        - input_type explicitly says "url", or
        - normalized/raw input is itself an HTTP(S) URL.
        """

        input_type = str(state.get("input_type", "")).lower()

        if input_type == "url":
            return True

        candidates = (
            state.get("normalized_input"),
            state.get("raw_input_text"),
        )

        for candidate in candidates:
            if not isinstance(candidate, str):
                continue

            value = candidate.strip()

            if not value:
                continue

            try:
                parsed = urlsplit(value)
            except ValueError:
                continue

            if parsed.scheme.lower() not in {"http", "https"}:
                continue

            if not parsed.netloc:
                continue

            return True

        return False

    async def _collect_evidence_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Executing collect_evidence node",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "collect_evidence",
                }
            },
        )

        evidence = state.get("evidence", [])

        logger.info(
            f"Collected total {len(evidence)} evidence items "
            f"for investigation {state.get('investigation_id')}"
        )

        return {
            "current_step": "collect_evidence",
        }

    async def _calculate_risk_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        """Calculate deterministic risk from structured investigation evidence."""
        logger.info(
            "Calculating deterministic risk assessment",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "calculate_risk",
                }
            },
        )

        try:
            investigation_id = UUID(state["investigation_id"])

            evidence = [
                EvidenceContract.model_validate(item)
                for item in state.get("evidence", [])
            ]

            assessment = calculate_risk(
                investigation_id=investigation_id,
                claims=state.get("claims", []),
                indicators=state.get("indicators", []),
                evidence=evidence,
                tool_results=state.get("tool_results", []),
            )

            return {
                "risk_assessment": assessment.model_dump(mode="json"),
                "current_step": "calculate_risk",
            }

        except Exception as exc:
            logger.error(
                f"Risk calculation failed: {exc}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "investigation_id": state.get("investigation_id"),
                        "step": "calculate_risk",
                    }
                },
            )

            errors = list(state.get("errors", []))
            errors.append(f"Risk calculation failure: {exc}")

            return {
                "risk_assessment": None,
                "current_step": "calculate_risk",
                "status": AnalysisStatus.PARTIAL.value,
                "errors": errors,
            }

    async def _finalize_investigation_node(
        self,
        state: InvestigationStateDict,
    ) -> dict[str, Any]:
        logger.info(
            "Finalizing investigation in LangGraph",
            extra={
                "extra_fields": {
                    "investigation_id": state.get("investigation_id"),
                    "step": "finalize_investigation",
                }
            },
        )

        timestamps = dict(state.get("timestamps", {}))
        timestamps["completed_at"] = datetime.now(UTC).isoformat()

        # Determine definitive final status
        current_status = state.get(
            "status",
            AnalysisStatus.PENDING.value,
        )

        errors = state.get("errors", [])
        evidence = state.get("evidence", [])

        if current_status == AnalysisStatus.INSUFFICIENT_EVIDENCE.value:
            final_status = AnalysisStatus.INSUFFICIENT_EVIDENCE.value

        elif errors and not evidence:
            final_status = AnalysisStatus.FAILED.value

        elif errors and evidence:
            final_status = AnalysisStatus.PARTIAL.value

        elif current_status == AnalysisStatus.PARTIAL.value:
            final_status = AnalysisStatus.PARTIAL.value

        else:
            final_status = AnalysisStatus.SUCCESS.value

        messages = list(state.get("messages", []))

        messages.append(
            {
                "role": "assistant",
                "content": (
                    f"Investigation completed with status "
                    f"'{final_status}'. Total evidence items: "
                    f"{len(evidence)}."
                ),
            }
        )

        return {
            "current_step": "completed",
            "status": final_status,
            "timestamps": timestamps,
            "messages": messages,
        }