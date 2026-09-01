from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EvidenceGrade = Literal["A", "B+", "ALIGN", "SOURCE_GAP", "UNRESOLVED"]


@dataclass(slots=True)
class EvidenceItem:
    source_role: str
    cue_ids: list[str] = field(default_factory=list)
    excerpt: str | None = None
    supports: str | None = None
    authority_domain: str | None = None
    status: str = "support"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls(
            source_role=str(data.get("source_role", "unknown")),
            cue_ids=[str(item) for item in data.get("cue_ids", [])],
            excerpt=data.get("excerpt"),
            supports=data.get("supports"),
            authority_domain=data.get("authority_domain"),
            status=str(data.get("status", "support")),
        )


@dataclass(slots=True)
class EvidenceAssessment:
    grade: EvidenceGrade
    primary: EvidenceItem | None = None
    secondary: list[EvidenceItem] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "grade": self.grade,
            "primary": self.primary.to_dict() if self.primary else None,
            "secondary": [item.to_dict() for item in self.secondary],
            "conflicts": list(self.conflicts),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceAssessment":
        primary = data.get("primary")
        return cls(
            grade=str(data.get("grade", "UNRESOLVED")),  # type: ignore[arg-type]
            primary=EvidenceItem.from_dict(primary) if isinstance(primary, dict) else None,
            secondary=[
                EvidenceItem.from_dict(item)
                for item in data.get("secondary", [])
                if isinstance(item, dict)
            ],
            conflicts=[str(item) for item in data.get("conflicts", [])],
            rationale=data.get("rationale"),
        )


def evidence_grade(
    *,
    primary_explicit: bool,
    independent_support: bool = False,
    secondary_conflict: bool = False,
    alignment_only: bool = False,
    source_gap: bool = False,
) -> EvidenceGrade:
    """Grade evidence by authority and agreement, never by raw source count."""
    if source_gap:
        return "SOURCE_GAP"
    if alignment_only:
        return "ALIGN"
    if primary_explicit:
        if independent_support and not secondary_conflict:
            return "A"
        return "B+"
    return "UNRESOLVED"
