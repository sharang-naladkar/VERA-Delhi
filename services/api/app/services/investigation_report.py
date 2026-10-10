"""Structured, evidence-grounded investigation report generation for VERA."""

from datetime import UTC, datetime
from typing import Any


REPORT_VERSION = "1.0.0"


def generate_investigation_report(
    *,
    investigation_id: str,
    status: str,
    evidence: list[dict[str, Any]],
    risk_assessment: dict[str, Any],
    claims: list[dict[str, Any]] | None = None,
    entities: list[dict[str, Any]] | None = None,
    indicators: list[str] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a structured report from recorded findings and assessment."""

    claims = claims or []
    entities = entities or []
    indicators = indicators or []
    errors = errors or []
    warnings = warnings or []

    evidence_items = []

    for item in evidence:
        evidence_items.append(
            {
                "evidence_id": str(item.get("id", "")),
                "type": str(item.get("type", "unknown")),
                "category": str(item.get("category", "general")),
                "severity": str(item.get("severity", "informational")),
                "status": str(item.get("status", "UNKNOWN")),
                "confidence": item.get("confidence", 0.0),
                "source": str(item.get("source_name", "unknown")),
                "description": str(item.get("description", "")),
            }
        )

    if not evidence_items:
        findings_summary = (
            "No evidence items were recorded. The available information "
            "is insufficient to draw a risk conclusion."
        )
    else:
        findings_summary = (
            f"The investigation recorded {len(evidence_items)} evidence "
            f"item(s). The assessment contains "
            f"{risk_assessment.get('eligible_factor_count', 0)} eligible "
            "risk factor(s). Review the evidence and limitations before "
            "drawing conclusions."
        )

    score_level = risk_assessment.get("level", "undetermined")
    score = risk_assessment.get("score", 0)

    if score_level == "undetermined":
        assessment_summary = (
            "Risk could not be determined from eligible evidence. "
            "This must not be interpreted as evidence that the subject "
            "is safe or that wrongdoing occurred."
        )
    else:
        assessment_summary = (
            f"The deterministic indicator assessment returned a score "
            f"of {score}/100 ({score_level}). This is an uncalibrated "
            "indicator score, not a probability of fraud."
        )

    next_steps = []

    if not evidence_items:
        next_steps.append(
            "Collect relevant source material and rerun the investigation."
        )

    if risk_assessment.get("excluded_check_count", 0):
        next_steps.append(
            "Review unavailable, failed, or unverified checks and retry "
            "them where appropriate."
        )

    if risk_assessment.get("eligible_factor_count", 0):
        next_steps.append(
            "Review each contributing evidence item and verify its "
            "underlying source before making a decision."
        )

    if errors or warnings:
        next_steps.append(
            "Review execution errors and warnings before relying on "
            "the investigation results."
        )

    if not next_steps:
        next_steps.append(
            "Review the evidence coverage and obtain independent "
            "verification where necessary."
        )

    return {
        "report_version": REPORT_VERSION,
        "investigation_id": investigation_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "investigation_status": status,
        "executive_summary": findings_summary,
        "assessment_summary": assessment_summary,
        "risk_assessment": risk_assessment,
        "findings": evidence_items,
        "claims": claims,
        "entities": entities,
        "indicators": indicators,
        "execution_errors": errors,
        "warnings": warnings,
        "limitations": [
            "This report summarizes the evidence available to VERA.",
            "An indicator score is not a calibrated probability of fraud.",
            "Automated findings require appropriate source verification.",
            "Unavailable checks do not establish safety or wrongdoing.",
            "The absence of detected indicators does not prove the absence "
            "of fraud.",
        ],
        "recommended_next_steps": next_steps,
    }