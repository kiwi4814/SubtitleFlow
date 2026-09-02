from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .alignment import align_cues, editable_cues
from .editorial import editorial_context
from .errors import GateError, ValidationError
from .glossary import apply_glossary, load_glossary
from .io import read_json, write_json
from .models import BranchUnit, BranchWorkfile, Cue
from .normalize import load_normalized
from .reconciliation import reconcile_groups
from .srp.resolver import require_research_ready_for_edit
from .state import invalidate_after_prepare, update_stage
from .text import TraditionalToSimplified, normalize_dialogue_text
from .workflow import active_branches, missing_roles_for_profile
from .workspace import TitlePaths, verify_sources


def _cue_map(cues: Iterable[Cue]) -> dict[str, Cue]:
    return {cue.id: cue for cue in cues}


def _join_text(cues: list[Cue]) -> str:
    return normalize_dialogue_text(
        "\n".join(cue.plain_text for cue in cues if cue.plain_text.strip())
    )


def _alignment_report(result: Any, left_role: str, right_role: str) -> dict[str, Any]:
    report = result.to_dict()
    report["left_role"] = left_role
    report["right_role"] = right_role
    return report


def _make_proxy_cues(units: list[BranchUnit]) -> list[Cue]:
    return [
        Cue(
            id=unit.id,
            index=index,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            text=unit.raw_text,
            plain_text=unit.raw_text,
            semantic_role=unit.semantic_role,
        )
        for index, unit in enumerate(units)
    ]


def _apply_language_normalization(
    text: str,
    *,
    branch: str,
    convert_t2s: bool,
    profile: str,
    allow_no_opencc: bool,
    glossary_rules: list[Any],
) -> tuple[str, list[Any], list[dict[str, str]], str | None]:
    result = text
    converter_backend: str | None = None
    if convert_t2s and result:
        converter = TraditionalToSimplified(profile)
        if not converter.available:
            if not allow_no_opencc:
                raise GateError(
                    "Traditional-to-Simplified conversion is enabled but OpenCC is unavailable. "
                    "Install `opencc` or run with --allow-no-opencc only for diagnostics."
                )
        else:
            result = converter.convert(result)
            converter_backend = converter.backend
    result, changes, review_hits = apply_glossary(result, glossary_rules, branch)
    return result, changes, review_hits, converter_backend


def build_clean_workfile(paths: TitlePaths, *, allow_no_opencc: bool = False) -> Path:
    config = read_json(paths.title_config)
    branch_cfg = config.get("clean_branch", {})
    if not branch_cfg.get("enabled", True):
        raise GateError("Clean branch is disabled")
    verify_sources(paths, {"S"})
    subtitle = load_normalized(paths, "S")
    cues = editable_cues(subtitle.cues)
    rules = load_glossary(paths)
    units: list[BranchUnit] = []
    converter_backends: set[str] = set()
    for cue in cues:
        raw = normalize_dialogue_text(cue.plain_text)
        normalized, changes, review_hits, backend = _apply_language_normalization(
            raw,
            branch="clean",
            convert_t2s=bool(branch_cfg.get("traditional_to_simplified", False)),
            profile=str(branch_cfg.get("opencc_profile", "t2s")),
            allow_no_opencc=allow_no_opencc,
            glossary_rules=rules,
        )
        if backend:
            converter_backends.add(backend)
        flags: list[str] = []
        if review_hits:
            flags.append("context-terminology-review")
        units.append(
            BranchUnit(
                id=f"clean-{len(units) + 1:06d}",
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                timing_cue_ids=[cue.id],
                source_cue_ids=[cue.id],
                raw_text=raw,
                normalized_text=normalized,
                final_text=normalized,
                alignment_confidence=1.0,
                changes=changes,
                flags=flags,
                semantic_role=cue.semantic_role,
            )
        )

    manifest = read_json(paths.manifest)
    has_c = "C" in manifest.get("sources", {})
    assisted_setting = branch_cfg.get("source_assisted", "auto")
    workflow_profile = str(config.get("workflow", {}).get("profile", "auto")).lower()
    if workflow_profile == "source-assisted":
        assisted = True
    elif assisted_setting == "auto":
        assisted = has_c if workflow_profile == "auto" else False
    elif isinstance(assisted_setting, bool):
        assisted = assisted_setting
    else:
        raise ValidationError("clean_branch.source_assisted must be true, false, or 'auto'")
    if assisted:
        if not has_c:
            raise GateError("Clean source-assisted mode requires role C, but C is missing")
        c = load_normalized(paths, "C")
        c_cues = editable_cues(c.cues)
        alignment_cfg = config.get("alignment", {})
        proxy = _make_proxy_cues(units)
        result = align_cues(
            proxy,
            c_cues,
            max_group=int(alignment_cfg.get("max_group", 3)),
            unmatched_penalty=float(alignment_cfg.get("unmatched_penalty", 3.0)),
        )
        cmap = _cue_map(c_cues)
        units_by_id = {unit.id: unit for unit in units}
        threshold = float(alignment_cfg.get("review_confidence_below", 0.72))
        for group in result.groups:
            if not group.left_ids:
                continue
            source_cues = [cmap[item] for item in group.right_ids]
            source_text = _join_text(source_cues)
            for index, unit_id in enumerate(group.left_ids):
                unit = units_by_id[unit_id]
                unit.source_text = source_text if source_text else None
                unit.source_text_cue_ids = list(group.right_ids)
                unit.alignment_confidence = min(unit.alignment_confidence, group.confidence)
                if source_cues and group.confidence < threshold:
                    unit.flags.append("low-source-alignment-confidence")
                if len(group.left_ids) > 1 and index > 0 and source_text:
                    unit.flags.append("shared-source-evidence-continuation")
                if not source_cues:
                    unit.flags.append("missing-source-evidence")
        write_json(
            paths.work / "alignment-CLEAN-C.json", _alignment_report(result, "clean-work", "C")
        )

    work = BranchWorkfile(
        schema_version=1,
        project_id=paths.project_id,
        title_id=paths.title_id,
        branch="clean",
        timing_role="S",
        language_source_role="S",
        source_language_role="C" if assisted else None,
        units=units,
        metadata={
            "self_contained_timing": True,
            "source_assisted": assisted,
            "opencc_backends": sorted(converter_backends),
            "minimal_editorial_intervention": True,
            "editorial": editorial_context(config, branch="clean").to_dict(),
        },
    )
    output = paths.work / "clean.json"
    write_json(output, work.to_dict())
    return output


def build_tw_workfile(paths: TitlePaths, *, allow_no_opencc: bool = False) -> Path:
    config = read_json(paths.title_config)
    branch_cfg = config.get("tw_branch", {})
    if not branch_cfg.get("enabled", True):
        raise GateError("TW branch is disabled")
    verify_sources(paths, {"A", "D"})
    a = load_normalized(paths, "A")
    d = load_normalized(paths, "D")
    a_cues = editable_cues(a.cues)
    d_cues = editable_cues(d.cues)
    alignment_cfg = config.get("alignment", {})
    result = align_cues(
        a_cues,
        d_cues,
        max_group=int(alignment_cfg.get("max_group", 3)),
        unmatched_penalty=float(alignment_cfg.get("unmatched_penalty", 3.0)),
    )
    amap, dmap = _cue_map(a_cues), _cue_map(d_cues)
    rules = load_glossary(paths)
    threshold = float(alignment_cfg.get("review_confidence_below", 0.72))
    units: list[BranchUnit] = []
    converter_backends: set[str] = set()
    for group in result.groups:
        if not group.left_ids:
            continue
        left = [amap[item] for item in group.left_ids]
        right = [dmap[item] for item in group.right_ids]
        raw = _join_text(right)
        normalized, changes, review_hits, backend = _apply_language_normalization(
            raw,
            branch="tw",
            convert_t2s=bool(branch_cfg.get("traditional_to_simplified", True)),
            profile=str(branch_cfg.get("opencc_profile", "t2s")),
            allow_no_opencc=allow_no_opencc,
            glossary_rules=rules,
        )
        if backend:
            converter_backends.add(backend)
        flags: list[str] = []
        if not right:
            flags.append("missing-language-source")
        if group.confidence < threshold and right:
            flags.append("low-alignment-confidence")
        if review_hits:
            flags.append("context-terminology-review")
        units.append(
            BranchUnit(
                id=f"tw-{len(units) + 1:06d}",
                start_ms=left[0].start_ms,
                end_ms=left[-1].end_ms,
                timing_cue_ids=group.left_ids,
                source_cue_ids=group.right_ids,
                raw_text=raw,
                normalized_text=normalized,
                final_text=normalized,
                alignment_confidence=group.confidence,
                changes=changes,
                flags=flags,
                semantic_role=(right[0].semantic_role if right else left[0].semantic_role),
            )
        )
    work = BranchWorkfile(
        schema_version=1,
        project_id=paths.project_id,
        title_id=paths.title_id,
        branch="tw",
        timing_role="A",
        language_source_role="D",
        source_language_role=None,
        units=units,
        metadata={
            "alignment_offset_ms": result.estimated_offset_ms,
            "opencc_backends": sorted(converter_backends),
            "minimal_editorial_intervention": True,
            "editorial": editorial_context(config, branch="tw").to_dict(),
        },
    )
    output = paths.work / "tw.json"
    write_json(output, work.to_dict())
    write_json(paths.work / "alignment-A-D.json", _alignment_report(result, "A", "D"))
    return output


def build_jp_workfile(paths: TitlePaths, *, allow_no_opencc: bool = False) -> Path:
    config = read_json(paths.title_config)
    branch_cfg = config.get("jp_branch", {})
    if not branch_cfg.get("enabled", True):
        raise GateError("JP branch is disabled")
    verify_sources(paths, {"A", "B", "C"})
    a = load_normalized(paths, "A")
    b = load_normalized(paths, "B")
    c = load_normalized(paths, "C")
    a_cues = editable_cues(a.cues)
    b_cues = editable_cues(b.cues)
    c_cues = editable_cues(c.cues)
    alignment_cfg = config.get("alignment", {})
    max_group = int(alignment_cfg.get("max_group", 3))
    unmatched_penalty = float(alignment_cfg.get("unmatched_penalty", 3.0))
    threshold = float(alignment_cfg.get("review_confidence_below", 0.72))

    ab = align_cues(a_cues, b_cues, max_group=max_group, unmatched_penalty=unmatched_penalty)
    amap, bmap = _cue_map(a_cues), _cue_map(b_cues)
    rules = load_glossary(paths)
    units: list[BranchUnit] = []
    for group in ab.groups:
        if not group.left_ids:
            continue
        left = [amap[item] for item in group.left_ids]
        right = [bmap[item] for item in group.right_ids]
        raw = _join_text(right)
        normalized, changes, review_hits, _backend = _apply_language_normalization(
            raw,
            branch="jp",
            convert_t2s=bool(branch_cfg.get("traditional_to_simplified", False)),
            profile=str(branch_cfg.get("opencc_profile", "t2s")),
            allow_no_opencc=allow_no_opencc,
            glossary_rules=rules,
        )
        flags: list[str] = []
        if not right:
            flags.append("missing-translation-source")
        if group.confidence < threshold and right:
            flags.append("low-alignment-confidence")
        if review_hits:
            flags.append("context-terminology-review")
        units.append(
            BranchUnit(
                id=f"jp-{len(units) + 1:06d}",
                start_ms=left[0].start_ms,
                end_ms=left[-1].end_ms,
                timing_cue_ids=group.left_ids,
                source_cue_ids=group.right_ids,
                raw_text=raw,
                normalized_text=normalized,
                final_text=normalized,
                alignment_confidence=group.confidence,
                changes=changes,
                flags=flags,
                semantic_role=(right[0].semantic_role if right else left[0].semantic_role),
            )
        )

    proxy = _make_proxy_cues(units)
    pc = align_cues(proxy, c_cues, max_group=max_group, unmatched_penalty=unmatched_penalty)
    split_raw = branch_cfg.get("source_split_decisions", {})
    if split_raw and not isinstance(split_raw, dict):
        raise ValidationError("jp_branch.source_split_decisions must be an object")
    split_decisions = {str(key): str(value) for key, value in dict(split_raw).items()}
    reconciliation = reconcile_groups(
        units,
        c_cues,
        pc.groups,
        split_decisions=split_decisions,
    )
    units_by_id = {unit.id: unit for unit in units}
    for pair in reconciliation.pairs:
        unit = units_by_id[pair.target_unit_id]
        unit.source_text = pair.source_text
        unit.source_text_cue_ids = list(pair.source_text_cue_ids)
        unit.parent_source_cue_ids = list(pair.parent_source_cue_ids)
        unit.source_operation = pair.operation
        unit.alignment_confidence = min(unit.alignment_confidence, pair.confidence)
        for flag in pair.flags:
            if flag not in unit.flags:
                unit.flags.append(flag)
        if pair.confidence < threshold and pair.source_text:
            unit.flags.append("low-japanese-alignment-confidence")
        if pair.operation == "source-gap":
            unit.flags.append("SOURCE_GAP")

    work = BranchWorkfile(
        schema_version=1,
        project_id=paths.project_id,
        title_id=paths.title_id,
        branch="jp",
        timing_role="A",
        language_source_role="B",
        source_language_role="C",
        units=units,
        metadata={
            "alignment_ab_offset_ms": ab.estimated_offset_ms,
            "alignment_japanese_offset_ms": pc.estimated_offset_ms,
            "minimal_editorial_intervention": True,
            "editorial": editorial_context(config, branch="jp").to_dict(),
            "reconciliation_schema": 1,
        },
    )
    output = paths.work / "jp.json"
    write_json(output, work.to_dict())
    write_json(paths.work / "alignment-A-B.json", _alignment_report(ab, "A", "B"))
    write_json(paths.work / "alignment-JP-C.json", _alignment_report(pc, "JP-work", "C"))
    write_json(paths.work / "bilingual-reconciliation.json", reconciliation.to_dict())
    write_json(paths.work / "bilingual-coverage.json", reconciliation.coverage())
    return output


def build_all_workfiles(paths: TitlePaths, *, allow_no_opencc: bool = False) -> dict[str, str]:
    require_research_ready_for_edit(paths)
    invalidate_after_prepare(paths)
    branches = active_branches(paths)
    missing = missing_roles_for_profile(paths)
    if missing:
        detail = "; ".join(f"{branch}: {', '.join(roles)}" for branch, roles in missing.items())
        raise GateError(f"Workflow profile cannot start; missing source roles: {detail}")
    if not branches:
        raise GateError("No active subtitle branch can be derived from the imported evidence")
    outputs: dict[str, str] = {}
    for branch in branches:
        if branch == "clean":
            path = build_clean_workfile(paths, allow_no_opencc=allow_no_opencc)
        elif branch == "tw":
            path = build_tw_workfile(paths, allow_no_opencc=allow_no_opencc)
        elif branch == "jp":
            path = build_jp_workfile(paths, allow_no_opencc=allow_no_opencc)
        else:  # pragma: no cover
            raise GateError(f"Unknown active branch: {branch}")
        outputs[branch] = str(path.relative_to(paths.title))
    update_stage(paths, "alignment_and_seed", "passed", outputs=outputs, branches=branches)
    return outputs


def load_workfile(paths: TitlePaths, branch: str) -> BranchWorkfile:
    return BranchWorkfile.from_dict(read_json(paths.work / f"{branch}.json"))


def save_workfile(paths: TitlePaths, workfile: BranchWorkfile) -> None:
    write_json(paths.work / f"{workfile.branch}.json", workfile.to_dict())
