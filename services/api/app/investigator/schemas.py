"""Structured Pydantic Schemas for VERA Investigator LLM Outputs."""

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class EntityType(StrEnum):
    """Categorization of entities identified in suspicious messages."""
    PERSON = "person"
    ORGANIZATION = "organization"
    ADVISOR = "advisor"
    BROKER = "broker"
    CHANNEL = "channel"
    GROUP = "group"
    URL = "url"
    PHONE = "phone"
    UPI = "upi"
    BANK_ACCOUNT = "bank_account"
    APP_PACKAGE = "app_package"
    REGISTRATION_NUMBER = "registration_number"
    OTHER = "other"


class ClaimType(StrEnum):
    """Categorization of claims made in investment messages."""
    GUARANTEED_RETURNS = "guaranteed_returns"
    SEBI_REGISTRATION = "sebi_registration"
    INSIDER_TIPS = "insider_tips"
    CELEBRITY_ENDORSEMENT = "celebrity_endorsement"
    INSTITUTIONAL_PARTNERSHIP = "institutional_partnership"
    URGENCY_FOMO = "urgency_fomo"
    ZERO_RISK = "zero_risk"
    UNAUTHORIZED_PMS = "unauthorized_pms"
    OTHER = "other"


class ExtractedEntity(BaseModel):
    """Single extracted entity candidate."""
    model_config = ConfigDict(extra="forbid")

    entity_type: EntityType = Field(..., description="Type of entity")
    name: str = Field(..., description="Entity name or label as mentioned")
    normalized_value: str = Field(..., description="Normalized identifier or text")
    source_text: str = Field(..., description="Exact substring from input")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model extraction confidence (0.0 to 1.0). NOT a fraud probability.",
    )


class EntityExtraction(BaseModel):
    """Structured entity extraction result from LLM."""
    model_config = ConfigDict(extra="forbid")

    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="List of detected financial or communicative entities",
    )
    summary: str = Field(..., description="Brief summary of entities identified")


class ExtractedClaim(BaseModel):
    """Single extracted investment claim."""
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(..., description="Normalized claim statement")
    claim_type: ClaimType = Field(..., description="Taxonomy type of claim")
    source_text: str = Field(..., description="Direct quotation from source text")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model extraction confidence (0.0 to 1.0). NOT a fraud probability.",
    )


class ClaimExtraction(BaseModel):
    """Structured claim extraction result from LLM."""
    model_config = ConfigDict(extra="forbid")

    claims: list[ExtractedClaim] = Field(
        default_factory=list,
        description="List of extracted investment/regulatory claims",
    )
    summary: str = Field(..., description="Summary of claims made")


class ScamPatternAnalysis(BaseModel):
    """Identified scam patterns and linguistic indicators."""
    model_config = ConfigDict(extra="forbid")

    patterns: list[str] = Field(
        default_factory=list,
        description="Identified suspicious patterns (e.g. 'unrealistic guaranteed daily returns')",
    )
    indicators: list[str] = Field(
        default_factory=list,
        description="Specific behavioral/linguistic indicators found in text",
    )
    explanation: str = Field(
        ...,
        description="Objective explanation of observed patterns without declaring legal guilt",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model pattern identification confidence (0.0 to 1.0). NOT fraud probability.",
    )


class InvestigationPlan(BaseModel):
    """Plan of action determined by the central investigator."""
    model_config = ConfigDict(extra="forbid")

    objectives: list[str] = Field(
        default_factory=list,
        description="Key investigation goals for this input",
    )
    entities_to_extract: list[str] = Field(
        default_factory=list,
        description="Types or specifics of entities to focus on",
    )
    claims_to_verify: list[str] = Field(
        default_factory=list,
        description="Claims requiring investigation and evidence",
    )
    tools_to_consider: list[str] = Field(
        default_factory=list,
        description="Names of tools to invoke",
    )
    reasoning_summary: str = Field(
        ...,
        description="Synthesized reasoning explaining the investigation path",
    )


class InvestigatorDecision(BaseModel):
    """Investigator decision node evaluation."""
    model_config = ConfigDict(extra="forbid")

    next_action: str = Field(..., description="Next step or tool in graph")
    rationale: str = Field(..., description="Why this action is taken")
    evidence_required: list[str] = Field(
        default_factory=list,
        description="Types of evidence needed to conclude",
    )
    status: str = Field(..., description="Status assessment of current step")
