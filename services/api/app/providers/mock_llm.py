"""Deterministic Mock LLM Provider for Isolated Testing."""

from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.contracts.status import AnalysisStatus
from app.core.errors import LLMGenerationError, ProviderUnavailableError
from app.investigator.schemas import (
    ClaimExtraction,
    ClaimType,
    EntityExtraction,
    EntityType,
    ExtractedClaim,
    ExtractedEntity,
    InvestigationPlan,
    InvestigatorDecision,
    ScamPatternAnalysis,
)
from app.providers.llm import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic, offline LLM Provider for unit and integration testing."""

    def __init__(
        self,
        mode: str = "auto",
        model_name: str = "mock-qwen3",
    ) -> None:
        """
        Args:
            mode: 'auto' (inspect prompt/input text), 'clean', 'suspicious', 'guaranteed_return',
                  'impersonation', 'malformed', 'unavailable', 'insufficient_evidence'
            model_name: Identifier name for mock provider
        """
        self.mode = mode
        self.model_name = model_name
        self._provider_name = f"mock_llm:{self.model_name}"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def is_available(self) -> bool:
        return self.mode != "unavailable"

    async def health_check(self) -> dict[str, Any]:
        if self.mode == "unavailable":
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": "Mock LLM is configured in unavailable mode.",
            }
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "Mock LLM is ready.",
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if self.mode == "unavailable":
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "error": "Mock LLM is unavailable.",
                "response": None,
            }

        last_content = messages[-1].get("content", "") if messages else ""
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "response": f"Mock analysis for: {last_content[:60]}",
        }

    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> T:
        mode = self._resolve_mode(prompt)

        if mode == "unavailable":
            raise ProviderUnavailableError(
                self.provider_name,
                details={"reason": "Mock LLM is set to unavailable mode."},
            )

        if mode == "malformed":
            raise LLMGenerationError(
                "Mock LLM generated malformed JSON that failed schema validation.",
                details={"schema": schema.__name__},
            )

        # Dispatch based on target schema
        if schema == EntityExtraction:
            return self._build_entity_extraction(mode, prompt)  # type: ignore[return-value]
        if schema == ClaimExtraction:
            return self._build_claim_extraction(mode, prompt)  # type: ignore[return-value]
        if schema == ScamPatternAnalysis:
            return self._build_scam_pattern_analysis(mode, prompt)  # type: ignore[return-value]
        if schema == InvestigationPlan:
            return self._build_investigation_plan(mode, prompt)  # type: ignore[return-value]
        if schema == InvestigatorDecision:
            return self._build_investigator_decision(mode, prompt)  # type: ignore[return-value]

        # Generic fallback instance if any other model is requested
        try:
            return schema.model_validate({})
        except Exception as exc:
            raise LLMGenerationError(
                f"Mock LLM cannot instantiate schema {schema.__name__}: {exc}"
            ) from exc

    def _resolve_mode(self, text: str) -> str:
        """Determines active test mode from configured mode or explicit text triggers."""
        lower = text.lower()
        if "[test_mode:unavailable]" in lower or self.mode == "unavailable":
            return "unavailable"
        if "[test_mode:malformed]" in lower or self.mode == "malformed":
            return "malformed"
        if "[test_mode:insufficient]" in lower or self.mode == "insufficient_evidence":
            return "insufficient_evidence"
        if "[test_mode:impersonation]" in lower or self.mode == "impersonation":
            return "impersonation"
        if "[test_mode:guaranteed]" in lower or self.mode == "guaranteed_return":
            return "guaranteed_return"
        if "[test_mode:clean]" in lower or self.mode == "clean":
            return "clean"

        if self.mode != "auto":
            return self.mode

        # Auto detection from text content
        if "guaranteed" in lower or "daily return" in lower or "500%" in lower or "100% profit" in lower:
            return "guaranteed_return"
        if "sebi" in lower or "official advisor" in lower or "certif" in lower or "government" in lower:
            return "impersonation"
        if len(text.strip()) < 15 or "hello" in lower and len(text.strip()) < 25:
            return "insufficient_evidence"
        if "quarterly earnings" in lower or "investor presentation" in lower or "market closed" in lower:
            return "clean"
        if "crypto" in lower or "whatsapp" in lower or "telegram" in lower or "invest" in lower:
            return "suspicious"

        return "clean"

    def _build_entity_extraction(self, mode: str, prompt: str) -> EntityExtraction:
        if mode == "insufficient_evidence":
            return EntityExtraction(
                entities=[],
                summary="Insufficient content to extract financial entities.",
            )

        if mode == "guaranteed_return":
            return EntityExtraction(
                entities=[
                    ExtractedEntity(
                        entity_type=EntityType.CHANNEL,
                        name="VIP Wealth Club",
                        normalized_value="@vip_wealth_club",
                        source_text="VIP Wealth Club Telegram",
                        confidence=0.95,
                    ),
                    ExtractedEntity(
                        entity_type=EntityType.UPI,
                        name="Payment Handle",
                        normalized_value="wealth@fakeupi",
                        source_text="wealth@fakeupi",
                        confidence=0.90,
                    ),
                ],
                summary="Detected VIP Telegram channel and unverified UPI handle.",
            )

        if mode == "impersonation":
            return EntityExtraction(
                entities=[
                    ExtractedEntity(
                        entity_type=EntityType.ADVISOR,
                        name="Rajesh Sharma",
                        normalized_value="rajesh_sharma",
                        source_text="Rajesh Sharma SEBI Analyst",
                        confidence=0.88,
                    ),
                    ExtractedEntity(
                        entity_type=EntityType.REGISTRATION_NUMBER,
                        name="SEBI Reg No",
                        normalized_value="INA000099999",
                        source_text="INA000099999",
                        confidence=0.92,
                    ),
                ],
                summary="Detected individual claiming SEBI Research Analyst registration INA000099999.",
            )

        if mode == "clean":
            return EntityExtraction(
                entities=[
                    ExtractedEntity(
                        entity_type=EntityType.ORGANIZATION,
                        name="Tata Consultancy Services",
                        normalized_value="tcs",
                        source_text="Tata Consultancy Services",
                        confidence=0.96,
                    )
                ],
                summary="Detected legitimate publicly traded company reference.",
            )

        # Default suspicious
        return EntityExtraction(
            entities=[
                ExtractedEntity(
                    entity_type=EntityType.CHANNEL,
                    name="Fast Profit Tips",
                    normalized_value="@fast_profit_tips",
                    source_text="@fast_profit_tips",
                    confidence=0.85,
                )
            ],
            summary="Extracted social trading channel handle.",
        )

    def _build_claim_extraction(self, mode: str, prompt: str) -> ClaimExtraction:
        if mode == "insufficient_evidence" or mode == "clean":
            return ClaimExtraction(
                claims=[],
                summary="No suspicious or promotional investment claims detected.",
            )

        if mode == "guaranteed_return":
            return ClaimExtraction(
                claims=[
                    ExtractedClaim(
                        claim="Guaranteed 200% monthly returns with zero risk",
                        claim_type=ClaimType.GUARANTEED_RETURNS,
                        source_text="200% monthly returns guaranteed zero risk",
                        confidence=0.98,
                    ),
                    ExtractedClaim(
                        claim="Urgent limited seats closing in 1 hour",
                        claim_type=ClaimType.URGENCY_FOMO,
                        source_text="limited seats closing in 1 hour",
                        confidence=0.91,
                    ),
                ],
                summary="Extracted promises of guaranteed high returns and artificial urgency.",
            )

        if mode == "impersonation":
            return ClaimExtraction(
                claims=[
                    ExtractedClaim(
                        claim="Authorized SEBI registered Research Analyst providing insider tips",
                        claim_type=ClaimType.SEBI_REGISTRATION,
                        source_text="authorized SEBI registered Research Analyst",
                        confidence=0.94,
                    )
                ],
                summary="Extracted regulatory registration claims requiring independent verification.",
            )

        return ClaimExtraction(
            claims=[
                ExtractedClaim(
                    claim="High profit trading advisory service",
                    claim_type=ClaimType.OTHER,
                    source_text="high profit trading advisory",
                    confidence=0.80,
                )
            ],
            summary="Extracted generalized trading performance claims.",
        )

    def _build_scam_pattern_analysis(self, mode: str, prompt: str) -> ScamPatternAnalysis:
        if mode == "insufficient_evidence":
            return ScamPatternAnalysis(
                patterns=[],
                indicators=["insufficient_text_length"],
                explanation="The input text contains insufficient evidence to evaluate for structured scam patterns.",
                confidence=0.20,
            )

        if mode == "clean":
            return ScamPatternAnalysis(
                patterns=[],
                indicators=[],
                explanation="No recognized investment scam or predatory solicitation patterns observed.",
                confidence=0.95,
            )

        if mode == "guaranteed_return":
            return ScamPatternAnalysis(
                patterns=[
                    "guaranteed_unrealistic_yield",
                    "artificial_urgency_pressure",
                    "private_channel_redirection",
                ],
                indicators=[
                    "promises 200% return",
                    "zero risk claim",
                    "closing in 1 hour urgency",
                ],
                explanation="Observed classic high-yield investment fraud indicators promising fixed returns without market downside.",
                confidence=0.96,
            )

        if mode == "impersonation":
            return ScamPatternAnalysis(
                patterns=[
                    "unverified_regulatory_credential_claim",
                    "insider_information_promise",
                ],
                indicators=[
                    "claims SEBI registration without verifiable broker affiliation",
                    "promises non-public tips",
                ],
                explanation="Observed potential advisor impersonation or unauthorized advisory signaling.",
                confidence=0.90,
            )

        return ScamPatternAnalysis(
            patterns=["unsolicited_investment_solicitation"],
            indicators=["external group invitation"],
            explanation="Unsolicited investment recommendation detected.",
            confidence=0.75,
        )

    def _build_investigation_plan(self, mode: str, prompt: str) -> InvestigationPlan:
        return InvestigationPlan(
            objectives=[
                "Extract communicative handles and monetary destinations",
                "Isolate claims regarding regulatory registration or guaranteed return",
                "Evaluate against known securities scam behavioral patterns",
            ],
            entities_to_extract=["advisors", "channels", "upi_handles", "registration_numbers"],
            claims_to_verify=["guaranteed_return", "sebi_registration"],
            tools_to_consider=["input_normalizer", "entity_extractor", "claim_extractor", "scam_pattern_analyzer"],
            reasoning_summary=f"Proceeding with structured textual investigation in mode '{mode}'.",
        )

    def _build_investigator_decision(self, mode: str, prompt: str) -> InvestigatorDecision:
        return InvestigatorDecision(
            next_action="execute_available_tools",
            rationale="Initial input analysis completed; executing specialized extractors.",
            evidence_required=["entity_detection", "claim_extraction", "pattern_analysis"],
            status=AnalysisStatus.SUCCESS.value,
        )

    async def analyze_fraud_claim(
        self,
        investigation_id: UUID,
        claim_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.mode == "unavailable":
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "error": "Mock LLM is unavailable.",
                "evidence": None,
            }
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "claim": claim_text,
            "analysis": "Mock evaluated claim indicators.",
        }
