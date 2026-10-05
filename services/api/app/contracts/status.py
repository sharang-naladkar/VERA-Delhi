"""Common Status Model for VERA Analyzers & Evidence."""

from enum import StrEnum


class AnalysisStatus(StrEnum):
    """Fail-safe status enum for all analyzers, providers, and verification services."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_VERIFIED = "NOT_VERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PENDING = "PENDING"

    def is_conclusive(self) -> bool:
        """Returns True if the analysis produced a definite conclusive output."""
        return self in (AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL)

    def is_failing(self) -> bool:
        """Returns True if the analysis encountered an error or unavailability."""
        return self in (AnalysisStatus.FAILED, AnalysisStatus.UNAVAILABLE)


class SeverityLevel(StrEnum):
    """Risk severity categorization."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(StrEnum):
    """Categorization of evidence produced across multi-modal pipelines."""

    RISK_SIGNAL = "risk_signal"
    FORENSIC_ARTIFACT = "forensic_artifact"
    ENTITY_DETECTION = "entity_detection"
    REGULATORY_CHECK = "regulatory_check"
    URL_ANALYSIS = "url_analysis"
    APK_ANALYSIS = "apk_analysis"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    OCR_EXTRACTION = "ocr_extraction"
    DEEPFAKE_ANALYSIS = "deepfake_analysis"
