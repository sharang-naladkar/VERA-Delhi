"""Database models package."""

from app.db.models.evidence import EvidenceModel
from app.db.models.investigation import InvestigationModel

__all__ = ["InvestigationModel", "EvidenceModel"]
