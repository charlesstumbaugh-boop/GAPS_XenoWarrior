#!/usr/bin/env python3
"""GAPS_XenoWarrior deterministic prompt compiler v0.1.0.

Reads an approved/draft IAS YAML plus a build request YAML and produces a
provider-neutral Prompt.md and a machine-readable GenerationManifest.yaml.
The compiler does not invent missing artistic decisions. Blocking unresolved
requirements stop compilation unless --allow-draft is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: python -m pip install PyYAML") from exc

COMPILER_VERSION = "0.1.0"


class CompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedFile:
    declared: str
    actual: Path
    sha256: str


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompileError(f"Missing YAML file: {path}") from exc
    except yaml.YAMLError as exc:
        raise CompileError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CompileError(f"Expected a YAML mapping in {path}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_name(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def resolve_repo_file(repo_root: Path, declared: str) -> Path:
    """Resolve legacy path/case differences without silently choosing ambiguity."""
    direct = repo_root / declared
    if direct.is_file():
        return direct

    normalized = normalize_name(declared)
    candidates: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        relative = normalize_name(str(path.relative_to(repo_root)))
        if relative == normalized or path.name.lower() == Path(declared).name.lower():
            candidates.append(path)

    unique = sorted(set(candidates))
    if len(unique) == 1:
        return unique[0]
    if not unique:
        raise CompileError(f"Referenced file not found: {declared}")
    choices = "\n  - ".join(str(p.relative_to(repo_root)) for p in unique)
    raise CompileError(f"Ambiguous reference '{declared}'. Candidates:\n  - {choices}")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def compact(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value).replace("_", " ")


def bullet_lines(items: Iterable[Any], prefix: str = "- ") -> list[str]:
    return [f"{prefix}{compact(item)}" for item in items if item not in (None, "")]


def get_path(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def blocking_requirements(asset: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    items = get_path(asset, "unresolved_requirements", "items", default=[])
    for item in as_list(items):
        if isinstance(item, dict) and item.get("blocks_generation") is True:
            path = item.get("path", "unknown")
            question = item.get("question", "Unresolved generation requirement")
            blocked.append(f"{path}: {' '.join(str(question).split())}")
    return blocked


def collect_dependencies(repo_root: Path, asset: dict[str, Any]) -> list[ResolvedFile]:
    declared_paths: list[str] = []
    core = get_path(asset, "source_versions", "core_contracts", default={})
    if isinstance(core, dict):
        for entry in core.values():
            if isinstance(entry, dict) and entry.get("file"):
                declared_paths.append(str(entry["file"]))
    specs = get_path(asset, "source_versions", "asset_specifications", default=[])
    for entry in as_list(specs):
        if isinstance(entry, dict) and entry.get("file"):
            declared_paths.append(str(entry["file"]))
    construction_file = get_path(asset, "construction", "construction_specification", "file")
    if construction_file:
        declared_paths.append(str(construction_file))
    for assignment in as_list(get_path(asset, "materials", "assignments", default=[])):
        if isinstance(assignment, dict) and assignment.get("material_file"):
            declared_paths.append(str(assignment["material_file"]))

    resolved: list[ResolvedFile] = []
    seen: set[Path] = set()
    for declared in declared_paths:
        actual = resolve_repo_file(repo_root, declared)
        if actual in seen:
            continue
        seen.add(actual)
        resolved.append(ResolvedFile(declared, actual, sha256_file(actual)))
    return resolved


def require_build_fields(build: dict[str, Any]) -> None:
    required = [
        ("build", "id"),
        ("build", "version"),
        ("asset", "ias_file"),
        ("request", "deliverable"),
        ("request", "purpose"),
    ]
    missing = [".".join(path) for path in required if get_path(build, *path) in (None, "")]
    if missing:
        raise CompileError("Build request is missing required fields: " + ", ".join(missing))


def validate_no_prompt_overrides(build: dict[str, Any]) -> None:
    forbidden = {"prompt", "freeform_prompt", "art_prompt", "positive_prompt", "negative_prompt"}
    found: list[str] = []

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key).lower() in forbidden:
                    found.append(child_path)
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(build)
    if found:
        raise CompileError(
            "Build YAML contains free-form prompt fields, which are forbidden: " + ", ".join(found)
        )


def compile_prompt(asset: dict[str, Any], build: dict[str, Any]) -> str:
    identity = get_path(asset, "identity", default={})
    visual = get_path(asset, "visual_contract", default={})
    camera = get_path(asset, "camera", default={})
    lighting = get_path(asset, "lighting", default={})
    export = get_path(asset, "export", default={})
    build_output = get_path(build, "request", "output", default={})
    guidance = get_path(asset, "generation_guidance", default={})
    restrictions = get_path(asset, "restrictions", default={})
    palette = get_path(asset, "palette", default={})
    construction = get_path(asset, "construction", default={})

    asset_id = identity.get("asset_id", "UNKNOWN_ASSET")
    asset_name = identity.get("asset_name", asset_id)
    deliverable = get_path(build, "request", "deliverable")
    purpose = get_path(build, "request", "purpose")

    positive = as_list(guidance.get("positive_requirements"))
    negative = as_list(guidance.get("negative_requirements"))
    immutable = as_list(restrictions.get("immutable_features"))
    prohibited = (
        as_list(restrictions.get("prohibited_changes"))
        + as_list(restrictions.get("prohibited_styles"))
        + as_list(restrictions.get("prohibited_camera_views"))
        + as_list(restrictions.get("prohibited_rendering_features"))
        + as_list(restrictions.get("prohibited_export_conditions"))
    )

    prompt: list[str] = [
        "# GAPS_XenoWarrior Generated Production Prompt",
        "",
        "> GENERATED FILE — DO NOT HAND-EDIT.",
        "> The repository specifications are authoritative. Reject output that violates them.",
        "",
        "## Build Identity",
        f"- Build ID: {get_path(build, 'build', 'id')}",
        f"- Build version: {get_path(build, 'build', 'version')}",
        f"- Asset ID: {asset_id}",
        f"- Asset name: {asset_name}",
        f"- Deliverable: {deliverable}",
        "",
        "## Production Objective",
        str(purpose).strip(),
        "",
        "## Canonical Asset Description",
        str(guidance.get("provider_neutral_description", "")).strip(),
        "",
        "## Required Visual Features",
        *bullet_lines(positive),
        "",
        "## Immutable Features",
        *bullet_lines(immutable),
        "",
        "## Rendering Contract",
        f"- Style: {compact(get_path(visual, 'visual_style', 'style_name'))}",
        f"- Shading: {compact(get_path(visual, 'rendering', 'shading_method'))}",
        f"- Shading levels: {compact(get_path(visual, 'rendering', 'shading_levels'))}",
        f"- Shadow multiplier: {compact(get_path(visual, 'rendering', 'shadow_brightness_multiplier'))}",
        f"- Outline width: {compact(get_path(visual, 'outline', 'width_px'))} px",
        f"- Outline color token: {compact(get_path(visual, 'outline', 'color_reference'))}",
        "",
        "## Construction and Silhouette",
        str(get_path(visual, "silhouette", "description", default="")).strip(),
        *bullet_lines(get_path(visual, "silhouette", "primary_readability_features", default=[])),
        f"- Reference height: {compact(construction.get('reference_height'))} {compact(construction.get('measurement_system'))}",
        "",
        "## Camera and Framing",
        f"- Projection: {compact(camera.get('projection'))}",
        f"- Orientation: {compact(camera.get('orientation'))}",
        f"- Pitch/Yaw/Roll: {compact(camera.get('pitch_degrees'))}/{compact(camera.get('yaw_degrees'))}/{compact(camera.get('roll_degrees'))} degrees",
        f"- Full asset visible: {compact(get_path(camera, 'framing', 'full_asset_visible'))}",
        f"- Clipping allowed: {compact(get_path(camera, 'framing', 'clipping_allowed'))}",
        f"- Pivot: ({compact(get_path(camera, 'pivot', 'x'))}, {compact(get_path(camera, 'pivot', 'y'))}) normalized",
        "",
        "## Lighting",
        f"- Primary direction: {compact(get_path(lighting, 'primary_light', 'horizontal_direction'))} and {compact(get_path(lighting, 'primary_light', 'vertical_direction'))}",
        f"- Primary angle: {compact(get_path(lighting, 'primary_light', 'angle_degrees'))} degrees",
        f"- Fill light enabled: {compact(lighting.get('fill_light_enabled'))}",
        f"- Ambient light enabled: {compact(lighting.get('ambient_light_enabled'))}",
        f"- Shadow edge: {compact(get_path(lighting, 'shadow', 'edge'))}",
        "",
        "## Palette Contract",
        "Use only approved palette tokens assigned by the IAS. Do not introduce unapproved colors.",
    ]

    for assignment in as_list(palette.get("assignments")):
        if isinstance(assignment, dict):
            prompt.append(
                f"- {compact(assignment.get('component'))}: {compact(assignment.get('palette_id'))} "
                f"({compact(assignment.get('usage_role'))})"
            )

    prompt.extend([
        "",
        "## Export Contract",
        f"- Output type: {compact(build_output.get('output_type', export.get('output_type')))}",
        f"- Format: {compact(build_output.get('image_format', export.get('image_format')))}",
        f"- Canvas: {compact(build_output.get('width_px', export.get('width_px')))} x {compact(build_output.get('height_px', export.get('height_px')))} px",
        f"- Transparent background: {compact(build_output.get('transparent_background', export.get('transparent_background')))}",
        f"- Alpha: {compact(export.get('alpha'))}",
        f"- Safe padding: {compact(export.get('safe_padding_px'))} px",
        f"- Trim transparency: {compact(export.get('trim_transparency'))}",
        "- No labels, captions, UI panels, poster layouts, documentation boards, or checkerboard pixels.",
        "",
        "## Prohibited Output",
        *bullet_lines(negative + prohibited),
        "",
        "## Build-Specific Constraints",
        *bullet_lines(get_path(build, "request", "required", default=[])),
        *bullet_lines([f"FORBIDDEN: {item}" for item in as_list(get_path(build, 'request', 'forbidden', default=[]))]),
        "",
        "## Final Instruction",
        "Generate only the requested production artwork. Do not generate a presentation sheet, labels, explanatory text, metadata, borders, frames, or a background. The output must remain inside the approved specification boxes above.",
        "",
    ])
    return "\n".join(line for line in prompt if line is not None)


def write_manifest(
    output: Path,
    repo_root: Path,
    asset_file: Path,
    build_file: Path,
    dependencies: list[ResolvedFile],
    prompt_file: Path,
    asset: dict[str, Any],
    build: dict[str, Any],
    draft_override: bool,
) -> None:
    manifest = {
        "metadata": {
            "type": "generation_manifest",
            "compiler": "GAPS_XenoWarrior build_prompt.py",
            "compiler_version": COMPILER_VERSION,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        },
        "build": {
            "id": get_path(build, "build", "id"),
            "version": str(get_path(build, "build", "version")),
            "draft_override_used": draft_override,
        },
        "asset": {
            "id": get_path(asset, "identity", "asset_id"),
            "ias_version": str(get_path(asset, "metadata", "document", "version")),
            "ias_status": get_path(asset, "metadata", "document", "status"),
            "ias_file": str(asset_file.relative_to(repo_root)),
            "ias_sha256": sha256_file(asset_file),
        },
        "inputs": [
            {
                "declared_file": item.declared,
                "resolved_file": str(item.actual.relative_to(repo_root)),
                "sha256": item.sha256,
            }
            for item in dependencies
        ],
        "outputs": {
            "prompt_file": prompt_file.name,
            "prompt_sha256": sha256_file(prompt_file),
            "expected_artifact": get_path(build, "request", "deliverable"),
        },
    }
    output.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a deterministic GAPS production prompt.")
    parser.add_argument("build", type=Path, help="Path to the build request YAML")
    parser.add_argument("--repo", type=Path, default=None, help="Repository root; auto-detected by default")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory; defaults to build file folder")
    parser.add_argument("--allow-draft", action="store_true", help="Allow unresolved generation blockers for testing only")
    args = parser.parse_args()

    build_file = args.build.resolve()
    if not build_file.is_file():
        raise CompileError(f"Build file does not exist: {build_file}")

    repo_root = args.repo.resolve() if args.repo else build_file
    if not args.repo:
        while repo_root.parent != repo_root and not (repo_root / "VERSION.yaml").is_file():
            repo_root = repo_root.parent
        if not (repo_root / "VERSION.yaml").is_file():
            raise CompileError("Could not auto-detect repository root containing VERSION.yaml")

    build = load_yaml(build_file)
    require_build_fields(build)
    validate_no_prompt_overrides(build)

    asset_declared = str(get_path(build, "asset", "ias_file"))
    asset_file = resolve_repo_file(repo_root, asset_declared)
    asset = load_yaml(asset_file)

    requested_id = get_path(build, "asset", "id")
    actual_id = get_path(asset, "identity", "asset_id")
    if requested_id and requested_id != actual_id:
        raise CompileError(f"Build asset ID '{requested_id}' does not match IAS asset ID '{actual_id}'")

    blockers = blocking_requirements(asset)
    approval_status = get_path(asset, "approval", "status")
    generation_authorized = get_path(asset, "approval", "generation_authorized")
    if (blockers or approval_status != "APPROVED" or generation_authorized is not True) and not args.allow_draft:
        details = []
        if approval_status != "APPROVED":
            details.append(f"approval.status is {approval_status!r}, expected 'APPROVED'")
        if generation_authorized is not True:
            details.append("approval.generation_authorized is not true")
        details.extend(blockers)
        raise CompileError("Build is blocked:\n- " + "\n- ".join(details))

    dependencies = collect_dependencies(repo_root, asset)
    output_dir = (args.output_dir.resolve() if args.output_dir else build_file.parent)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = output_dir / "Prompt.md"
    manifest_file = output_dir / "GenerationManifest.yaml"

    prompt_file.write_text(compile_prompt(asset, build), encoding="utf-8")
    write_manifest(
        manifest_file,
        repo_root,
        asset_file,
        build_file,
        dependencies,
        prompt_file,
        asset,
        build,
        args.allow_draft,
    )

    print(f"Compiled: {prompt_file}")
    print(f"Manifest: {manifest_file}")
    if args.allow_draft:
        print("WARNING: --allow-draft was used. Output is not production-authorized.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
