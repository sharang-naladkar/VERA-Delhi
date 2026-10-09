"""Validation helpers for regulatory verification results."""

from app.contracts.regulatory import (
    RegulatoryCapability,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_source_registry import RegulatorySourceRegistry


class RegulatoryResultValidator:
    """Validate source attribution and evidence in regulatory results."""

    def __init__(self, registry: RegulatorySourceRegistry) -> None:
        self._registry = registry

    def validate_request(
        self,
        request: RegulatoryVerificationRequest,
    ) -> list[str]:
        """Return validation errors for a verification request."""
        errors: list[str] = []

        if not any(
            value and value.strip()
            for value in (
                request.subject_name,
                request.registration_number,
                request.organization_name,
                request.social_handle,
            )
        ):
            errors.append("At least one non-empty subject identifier is required.")

        if any(not key.strip() or not value.strip() for key, value in request.identifiers.items()):
            errors.append("Additional identifier keys and values must not be blank.")

        return errors

    def validate_result(
        self,
        request: RegulatoryVerificationRequest,
        result: RegulatoryVerificationResult,
    ) -> list[str]:
        """Return validation errors without inferring facts or fraud."""
        errors: list[str] = []

        if result.participant_type != request.participant_type:
            errors.append("Result participant type does not match the request.")

        if (
            result.registration_number
            and request.registration_number
            and result.registration_number.strip().casefold()
            != request.registration_number.strip().casefold()
        ):
            errors.append("Result registration number contradicts the request.")

        source = None
        if result.source_id:
            source = self._registry.get_source(result.source_id)
            if source is None:
                errors.append("Result references an unregistered source.")
            else:
                if not source.enabled:
                    errors.append("Result references a disabled source.")

                if result.source_url != source.url:
                    errors.append("Result source URL does not match the registry.")

                if result.participant_type not in source.participant_types:
                    errors.append("Source does not support this participant type.")

                required_capability = self._required_capability(request)
                if required_capability not in source.capabilities:
                    errors.append(
                        "Source does not advertise the required capability."
                    )

        elif result.status in (AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL):
            errors.append("Conclusive result is missing source attribution.")

        if result.status == AnalysisStatus.SUCCESS:
            if result.matched is None:
                errors.append("Successful result must specify the match outcome.")

            if not result.evidence:
                errors.append("Successful result requires source-attributed evidence.")

            if source is None:
                errors.append("Successful result requires a registered source.")

            for item in result.evidence:
                if source is not None and item.source_id != source.source_id:
                    errors.append("Evidence source ID does not match the result source.")

                evidence_source = self._registry.get_source(item.source_id)
                if evidence_source is None:
                    errors.append("Evidence references an unregistered source.")
                elif item.source_url != evidence_source.url:
                    errors.append("Evidence URL does not match the registry.")

                if item.retrieved_at is None:
                    errors.append("Evidence is missing its retrieval timestamp.")

        if result.status in (
            AnalysisStatus.UNAVAILABLE,
            AnalysisStatus.FAILED,
            AnalysisStatus.NOT_VERIFIED,
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
            AnalysisStatus.PENDING,
        ) and result.matched is not None:
            errors.append(
                "Non-conclusive result must not assert a definitive match outcome."
            )

        return errors

    @staticmethod
    def _required_capability(
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryCapability:
        if request.participant_type.value == "stockbroker":
            return RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP

        if request.participant_type.value == "authorised_person":
            return RegulatoryCapability.AUTHORISED_PERSON_LOOKUP

        if request.registration_number:
            return RegulatoryCapability.REGISTRATION_LOOKUP

        return RegulatoryCapability.IDENTITY_MATCH
