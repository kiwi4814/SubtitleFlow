from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .errors import ValidationError

TranslationProvenance = Literal[
    "official",
    "professional",
    "human-fansub",
    "curated-human",
    "machine",
    "hybrid",
    "transcript",
    "unknown",
]
TranslationTrust = Literal["high", "medium", "low", "unknown"]
EditingPolicy = Literal["preserve", "proofread", "retranslate", "auto"]
PolicyAction = Literal["allow", "review", "block"]

PROVENANCE_VALUES = {
    "official",
    "professional",
    "human-fansub",
    "curated-human",
    "machine",
    "hybrid",
    "transcript",
    "unknown",
}
TRUST_VALUES = {"high", "medium", "low", "unknown"}
POLICY_VALUES = {"preserve", "proofread", "retranslate", "auto"}

# Central policy vocabulary. Callers submit a semantic change type; they do not reproduce
# policy-specific if/else trees. Human review remains a separate gate after this permission.
_CHANGE_ALIASES = {
    "semantic": "mistranslation",
    "semantic-correction": "mistranslation",
    "canon": "canon",
    "terminology": "terminology",
    "fact": "fact-correction",
    "number": "number-unit",
    "unit": "number-unit",
    "omission": "omission",
    "unsupported-addition": "unsupported-addition",
    "fluency": "fluency",
    "style": "fluency",
    "register": "register-voice",
    "voice": "register-voice",
    "segmentation": "segmentation",
    "alignment": "alignment",
    "substantial-rewrite": "substantial-rewrite",
    "full-retranslation": "full-retranslation",
}

_POLICY_MATRIX: dict[str, dict[str, PolicyAction]] = {
    "canon": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "terminology": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "fact-correction": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "mistranslation": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "omission": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "unsupported-addition": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "negation": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "subject-object": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "number-unit": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "name-place-organization": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "fluency": {"preserve": "block", "proofread": "allow", "retranslate": "allow"},
    "register-voice": {"preserve": "block", "proofread": "review", "retranslate": "allow"},
    "segmentation": {"preserve": "review", "proofread": "allow", "retranslate": "allow"},
    "alignment": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
    "substantial-rewrite": {"preserve": "block", "proofread": "review", "retranslate": "allow"},
    "full-retranslation": {"preserve": "block", "proofread": "block", "retranslate": "allow"},
    "layout-only": {"preserve": "allow", "proofread": "allow", "retranslate": "allow"},
}


@dataclass(slots=True)
class TranslationQualityAssessment:
    semantic_accuracy: float
    terminology_consistency: float
    fluency: float
    omission_risk: float
    mistranslation_risk: float
    alignment_risk: float
    recommended_policy: EditingPolicy | None = None
    confidence: float = 0.5
    notes: str | None = None

    def validate(self) -> None:
        for name in (
            "semantic_accuracy",
            "terminology_consistency",
            "fluency",
            "omission_risk",
            "mistranslation_risk",
            "alignment_risk",
            "confidence",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"Translation quality {name} must be between 0 and 1")
        if self.recommended_policy not in {None, "preserve", "proofread", "retranslate"}:
            raise ValidationError("Quality assessment recommended_policy must not be auto")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranslationQualityAssessment":
        item = cls(
            semantic_accuracy=float(data.get("semantic_accuracy", 0.5)),
            terminology_consistency=float(data.get("terminology_consistency", 0.5)),
            fluency=float(data.get("fluency", 0.5)),
            omission_risk=float(data.get("omission_risk", 0.5)),
            mistranslation_risk=float(data.get("mistranslation_risk", 0.5)),
            alignment_risk=float(data.get("alignment_risk", 0.5)),
            recommended_policy=data.get("recommended_policy"),
            confidence=float(data.get("confidence", 0.5)),
            notes=data.get("notes"),
        )
        item.validate()
        if item.recommended_policy is None:
            item.recommended_policy = recommend_policy(item)
        return item


@dataclass(slots=True)
class EditorialContext:
    translation_provenance: TranslationProvenance = "unknown"
    translation_trust: TranslationTrust = "unknown"
    requested_policy: EditingPolicy = "auto"
    effective_policy: EditingPolicy | None = None
    policy_source: str = "default"
    assessment: TranslationQualityAssessment | None = None

    @property
    def assessment_required(self) -> bool:
        return self.requested_policy == "auto" and self.assessment is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "translation_provenance": self.translation_provenance,
            "translation_trust": self.translation_trust,
            "requested_policy": self.requested_policy,
            "effective_policy": self.effective_policy,
            "policy_source": self.policy_source,
            "assessment_required": self.assessment_required,
            "assessment": self.assessment.to_dict() if self.assessment else None,
        }


def recommend_policy(assessment: TranslationQualityAssessment) -> EditingPolicy:
    """Turn an explicit AI/human assessment into a policy recommendation.

    SubtitleFlow never infers quality from provenance. The assessment metrics are the input;
    this deterministic reducer only chooses the broad editing envelope.
    """
    assessment.validate()
    severe_risk = max(
        assessment.omission_risk,
        assessment.mistranslation_risk,
        assessment.alignment_risk,
    )
    quality = (
        0.50 * assessment.semantic_accuracy
        + 0.20 * assessment.terminology_consistency
        + 0.30 * assessment.fluency
    )
    if assessment.semantic_accuracy >= 0.93 and severe_risk <= 0.12 and quality >= 0.90:
        return "preserve"
    if assessment.semantic_accuracy < 0.68 or assessment.mistranslation_risk >= 0.55:
        return "retranslate"
    return "proofread"


def editorial_context(config: dict[str, Any], *, branch: str = "jp") -> EditorialContext:
    root = config.get("editorial", {})
    if not isinstance(root, dict):
        raise ValidationError("editorial must be an object")
    branch_cfg = root.get(branch, {})
    if branch_cfg and not isinstance(branch_cfg, dict):
        raise ValidationError(f"editorial.{branch} must be an object")
    merged = {**root, **branch_cfg}
    provenance = str(merged.get("translation_provenance", "unknown")).lower()
    trust = str(merged.get("translation_trust", "unknown")).lower()
    requested = str(merged.get("editing_policy", "auto")).lower()
    if provenance not in PROVENANCE_VALUES:
        raise ValidationError(f"Unknown translation provenance: {provenance}")
    if trust not in TRUST_VALUES:
        raise ValidationError(f"Unknown translation trust: {trust}")
    if requested not in POLICY_VALUES:
        raise ValidationError(f"Unknown editing policy: {requested}")

    assessment_raw = merged.get("quality_assessment")
    assessment = (
        TranslationQualityAssessment.from_dict(assessment_raw)
        if isinstance(assessment_raw, dict)
        else None
    )
    if requested == "auto":
        effective = assessment.recommended_policy if assessment else None
        source = "quality-assessment" if assessment else "assessment-required"
    else:
        effective = requested
        source = "user-config"
    return EditorialContext(
        translation_provenance=provenance,  # type: ignore[arg-type]
        translation_trust=trust,  # type: ignore[arg-type]
        requested_policy=requested,  # type: ignore[arg-type]
        effective_policy=effective,
        policy_source=source,
        assessment=assessment,
    )


def normalize_change_type(change_type: str) -> str:
    value = change_type.strip().lower().replace("_", "-") or "mistranslation"
    return _CHANGE_ALIASES.get(value, value)


def policy_action(context: EditorialContext, change_type: str) -> PolicyAction:
    if context.effective_policy is None:
        return "block"
    normalized = normalize_change_type(change_type)
    row = _POLICY_MATRIX.get(normalized)
    if row is None:
        # Unknown semantic change types never gain broader rights by accident.
        return "review" if context.effective_policy != "preserve" else "block"
    return row[context.effective_policy]


def policy_matrix() -> dict[str, dict[str, PolicyAction]]:
    return {key: dict(value) for key, value in _POLICY_MATRIX.items()}
