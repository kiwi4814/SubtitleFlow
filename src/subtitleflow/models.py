from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .errors import ValidationError

SourceRole = Literal["A", "B", "C", "D", "S"]
BranchName = Literal["clean", "tw", "jp"]
ReviewStatus = Literal["pending", "approved", "rejected", "superseded"]


@dataclass(slots=True)
class Cue:
    id: str
    index: int
    start_ms: int
    end_ms: int
    text: str
    plain_text: str
    style: str = "Default"
    event_type: str = "Dialogue"
    protected: bool = False
    protected_reason: str | None = None
    raw_line: str | None = None

    def validate(self) -> None:
        if self.start_ms < 0:
            raise ValidationError(f"Cue {self.id}: negative start time")
        if self.end_ms < self.start_ms:
            raise ValidationError(f"Cue {self.id}: end < start")
        if self.end_ms == self.start_ms and not self.protected:
            raise ValidationError(f"Cue {self.id}: zero-duration editable cue")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Cue":
        cue = cls(**data)
        cue.validate()
        return cue


@dataclass(slots=True)
class NormalizedSubtitle:
    schema_version: int
    role: SourceRole
    source_file: str
    source_sha256: str
    format: str
    encoding: str
    cues: list[Cue]
    protected_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cues"] = [cue.to_dict() for cue in self.cues]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizedSubtitle":
        cues = [Cue.from_dict(item) for item in data.get("cues", [])]
        return cls(
            schema_version=int(data["schema_version"]),
            role=data["role"],
            source_file=data["source_file"],
            source_sha256=data["source_sha256"],
            format=data["format"],
            encoding=data.get("encoding", "utf-8"),
            cues=cues,
            protected_count=int(data.get("protected_count", 0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class AlignmentGroup:
    id: str
    left_ids: list[str]
    right_ids: list[str]
    start_ms: int
    end_ms: int
    cost: float
    confidence: float
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlignmentGroup":
        return cls(**data)


@dataclass(slots=True)
class ChangeRecord:
    kind: str
    before: str
    after: str
    rule_id: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BranchUnit:
    id: str
    start_ms: int
    end_ms: int
    timing_cue_ids: list[str]
    source_cue_ids: list[str]
    raw_text: str
    normalized_text: str
    final_text: str
    source_text: str | None = None
    source_text_cue_ids: list[str] = field(default_factory=list)
    alignment_confidence: float = 1.0
    changes: list[ChangeRecord] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.end_ms <= self.start_ms:
            raise ValidationError(f"Unit {self.id}: invalid timing")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["changes"] = [item.to_dict() for item in self.changes]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BranchUnit":
        changes = [ChangeRecord(**item) for item in data.get("changes", [])]
        unit = cls(
            id=data["id"],
            start_ms=int(data["start_ms"]),
            end_ms=int(data["end_ms"]),
            timing_cue_ids=list(data.get("timing_cue_ids", [])),
            source_cue_ids=list(data.get("source_cue_ids", [])),
            raw_text=data.get("raw_text", ""),
            normalized_text=data.get("normalized_text", ""),
            final_text=data.get("final_text", ""),
            source_text=data.get("source_text"),
            source_text_cue_ids=list(data.get("source_text_cue_ids", [])),
            alignment_confidence=float(data.get("alignment_confidence", 1.0)),
            changes=changes,
            flags=list(data.get("flags", [])),
        )
        unit.validate()
        return unit


@dataclass(slots=True)
class BranchWorkfile:
    schema_version: int
    project_id: str
    title_id: str
    branch: BranchName
    timing_role: SourceRole
    language_source_role: SourceRole
    source_language_role: SourceRole | None
    units: list[BranchUnit]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["units"] = [unit.to_dict() for unit in self.units]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BranchWorkfile":
        return cls(
            schema_version=int(data["schema_version"]),
            project_id=data["project_id"],
            title_id=data["title_id"],
            branch=data["branch"],
            timing_role=data["timing_role"],
            language_source_role=data["language_source_role"],
            source_language_role=data.get("source_language_role"),
            units=[BranchUnit.from_dict(item) for item in data.get("units", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ReviewCandidate:
    schema_version: int
    candidate_id: str
    project_id: str
    title_id: str
    branch: BranchName
    unit_id: str
    change_type: str
    original_text: str
    proposed_text: str
    reason: str
    confidence: float
    severity: str = "medium"
    evidence: dict[str, str] = field(default_factory=dict)
    requires_human: bool = True
    status: ReviewStatus = "pending"
    decision_note: str | None = None
    created_at: str | None = None
    decided_at: str | None = None

    def validate(self) -> None:
        if not self.candidate_id:
            raise ValidationError("Review candidate missing candidate_id")
        if self.branch not in {"clean", "tw", "jp"}:
            raise ValidationError(f"Unknown review branch: {self.branch}")
        if not 0 <= self.confidence <= 1:
            raise ValidationError("Review confidence must be between 0 and 1")
        if self.status not in {"pending", "approved", "rejected", "superseded"}:
            raise ValidationError(f"Invalid review status: {self.status}")
        if not self.proposed_text.strip():
            raise ValidationError("Review proposal cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewCandidate":
        candidate = cls(**data)
        candidate.validate()
        return candidate
