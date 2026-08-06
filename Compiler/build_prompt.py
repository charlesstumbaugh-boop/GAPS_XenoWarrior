#!/usr/bin/env python3
"""GAPS_XenoWarrior deterministic prompt compiler, Phase 1.

Reads a Build Request YAML and an approved/draft IAS YAML, resolves repository
references without inventing missing values, and writes Prompt.md, GenerationManifest.yaml, and BuildReport.md.

Usage:
    python Compiler/build_prompt.py path/to/Build.yaml
    python Compiler/build_prompt.py path/to/Build.yaml --allow-draft
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install it with: python -m pip install PyYAML"
    ) from exc


class CompilerError(RuntimeError):
    """Raised when compilation must stop instead of guessing."""


@dataclass(frozen=True)
class LoadedYaml:
    path: Path
    data: dict[str, Any]
    sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a deterministic image-generation prompt from GAPS YAML."
    )
    parser.add_argument("build_request", type=Path, help="Path to Build.yaml")
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Permit a DRAFT IAS for testing. The manifest records this override.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root. Auto-detected when omitted.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> LoadedYaml:
    if not path.is_file():
        raise CompilerError(f"YAML file not found: {path}")
    raw = path.read_bytes()
    try:
        parsed = yaml.safe_load(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CompilerError(f"File is not valid UTF-8: {path}") from exc
    except yaml.YAMLError as exc:
        raise CompilerError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CompilerError(f"Top level must be a YAML mapping: {path}")
    return LoadedYaml(path.resolve(), parsed, hashlib.sha256(raw).hexdigest())


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "VERSION.yaml").is_file() and (candidate / "Compiler").is_dir():
            return candidate
    raise CompilerError(
        "Could not locate repository root. Use --repo-root or ensure VERSION.yaml "
        "and Compiler/ exist above the Build Request."
    )


def normalized_parts(path_text: str) -> list[str]:
    return [part for part in path_text.replace("\\", "/").split("/") if part not in ("", ".")]


def resolve_repo_path(repo_root: Path, requested: str) -> Path:
    """Resolve a repository reference safely, with controlled legacy fallbacks."""
    parts = normalized_parts(requested)
    if not parts:
        raise CompilerError("Encountered an empty repository path reference.")

    # References originally used a virtual GameArtBible/ prefix even though the
    # repository stores Core/ and Specifications/ at root.
    if parts[0].casefold() == "gameartbible":
        parts = parts[1:]

    direct = repo_root.joinpath(*parts)
    if direct.is_file():
        return direct.resolve()

    # Case-insensitive traversal handles Core/core without silently choosing
    # between multiple candidates.
    candidates = [repo_root]
    for part in parts:
        next_candidates: list[Path] = []
        for base in candidates:
            if not base.is_dir():
                continue
            matches = [child for child in base.iterdir() if child.name.casefold() == part.casefold()]
            next_candidates.extend(matches)
        candidates = next_candidates
        if not candidates:
            break
    files = [item.resolve() for item in candidates if item.is_file()]
    if len(files) == 1:
        return files[0]
    if len(files) > 1:
        raise CompilerError(f"Ambiguous repository path {requested!r}: {files}")

    # Final fallback by exact basename only; fail if not unique.
    basename = parts[-1].casefold()
    matches = [p.resolve() for p in repo_root.rglob("*") if p.is_file() and p.name.casefold() == basename]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise CompilerError(f"Ambiguous fallback for {requested!r}: {matches}")
    raise CompilerError(f"Referenced repository file does not exist: {requested}")


def require_mapping(parent: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CompilerError(f"Missing or invalid mapping {context}.{key}")
    return value


def require_text(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CompilerError(f"Missing or invalid text {context}.{key}")
    return value.strip()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def text_list(values: Iterable[Any]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def bullets(items: Iterable[str], fallback: str = "No additional requirements declared.") -> str:
    values = unique(item for item in items if item)
    return "\n".join(f"- {item}" for item in values) if values else f"- {fallback}"


def collect_referenced_yaml(repo_root: Path, ias: dict[str, Any]) -> list[LoadedYaml]:
    source_versions = require_mapping(ias, "source_versions", "IAS")
    references: list[str] = []

    core = source_versions.get("core_contracts", {})
    if isinstance(core, dict):
        for entry in core.values():
            if isinstance(entry, dict) and isinstance(entry.get("file"), str):
                references.append(entry["file"])

    for entry in as_list(source_versions.get("asset_specifications")):
        if isinstance(entry, dict) and isinstance(entry.get("file"), str):
            references.append(entry["file"])

    inheritance = ias.get("inheritance", {})
    if isinstance(inheritance, dict):
        for entry in as_list(inheritance.get("parents")):
            if isinstance(entry, dict) and isinstance(entry.get("file"), str):
                references.append(entry["file"])

    materials = ias.get("materials", {})
    if isinstance(materials, dict):
        for entry in as_list(materials.get("assignments")):
            if isinstance(entry, dict) and isinstance(entry.get("material_file"), str):
                references.append(entry["material_file"])

    loaded: list[LoadedYaml] = []
    seen: set[Path] = set()
    for reference in references:
        path = resolve_repo_path(repo_root, reference)
        if path not in seen:
            loaded.append(load_yaml(path))
            seen.add(path)
    return loaded


def validate_build(build: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if "prompt" in build or "free_form_prompt" in build:
        raise CompilerError(
            "Build Request contains a free-form prompt field. Phase 1 forbids handwritten prompts."
        )
    metadata = require_mapping(build, "metadata", "Build")
    asset = require_mapping(build, "asset", "Build")
    output = require_mapping(build, "output", "Build")
    require_text(metadata, "build_id", "Build.metadata")
    require_text(asset, "ias_file", "Build.asset")
    require_text(output, "prompt_file", "Build.output")
    require_text(output, "manifest_file", "Build.output")
    report_file = output.get("report_file", "BuildReport.md")
    if not isinstance(report_file, str) or not report_file.strip():
        raise CompilerError("Missing or invalid text Build.output.report_file")
    output["report_file"] = report_file.strip()
    return metadata, asset, output


def validate_ias(ias: dict[str, Any], allow_draft: bool) -> None:
    metadata = require_mapping(ias, "metadata", "IAS")
    document = require_mapping(metadata, "document", "IAS.metadata")
    identity = require_mapping(ias, "identity", "IAS")
    require_text(identity, "asset_id", "IAS.identity")
    require_text(identity, "asset_name", "IAS.identity")

    status = str(document.get("status", "")).upper()
    if status != "APPROVED" and not allow_draft:
        raise CompilerError(
            f"IAS status is {status or 'MISSING'}, not APPROVED. "
            "Use --allow-draft only for compiler testing."
        )

    unresolved = ias.get("unresolved_requirements", {})
    blocking: list[str] = []
    if isinstance(unresolved, dict):
        for item in as_list(unresolved.get("items")):
            if isinstance(item, dict) and item.get("blocks_generation") is True:
                blocking.append(str(item.get("path", "unknown path")))
    if blocking and not allow_draft:
        raise CompilerError(
            "IAS has unresolved requirements that block generation: " + ", ".join(blocking)
        )


def compile_prompt(build: dict[str, Any], ias: dict[str, Any]) -> str:
    identity = require_mapping(ias, "identity", "IAS")
    visual = require_mapping(ias, "visual_contract", "IAS")
    construction = require_mapping(ias, "construction", "IAS")
    palette = require_mapping(ias, "palette", "IAS")
    camera = require_mapping(ias, "camera", "IAS")
    lighting = require_mapping(ias, "lighting", "IAS")
    export = require_mapping(ias, "export", "IAS")
    restrictions = require_mapping(ias, "restrictions", "IAS")
    guidance = ias.get("generation_guidance", {})
    if not isinstance(guidance, dict):
        guidance = {}

    asset_id = require_text(identity, "asset_id", "IAS.identity")
    asset_name = require_text(identity, "asset_name", "IAS.identity")
    build_meta = require_mapping(build, "metadata", "Build")
    build_id = require_text(build_meta, "build_id", "Build.metadata")
    objective = str(build.get("objective") or f"Generate the canonical production image for {asset_name}.").strip()

    style = visual.get("visual_style", {}) if isinstance(visual.get("visual_style"), dict) else {}
    silhouette = visual.get("silhouette", {}) if isinstance(visual.get("silhouette"), dict) else {}
    outline = visual.get("outline", {}) if isinstance(visual.get("outline"), dict) else {}
    render = visual.get("rendering", {}) if isinstance(visual.get("rendering"), dict) else {}

    positive = text_list(as_list(guidance.get("positive_requirements")))
    positive += text_list(as_list(silhouette.get("primary_readability_features")))

    prohibited: list[str] = []
    prohibited += text_list(as_list(guidance.get("negative_requirements")))
    for key in (
        "prohibited_changes",
        "prohibited_styles",
        "prohibited_camera_views",
        "prohibited_rendering_features",
        "prohibited_export_conditions",
    ):
        prohibited += text_list(as_list(restrictions.get(key)))

    # Mandatory output safeguards learned from failed generations.
    prohibited += [
        "no presentation sheet",
        "no infographic",
        "no title, caption, label, footer, frame number, watermark, or interface panel",
        "no checkerboard pattern rendered into the image",
        "no scenery, floor, platform, cast shadow, or decorative background",
        "no cropping of the body, equipment, or effects",
        "do not redesign or substitute unspecified components",
    ]

    palette_assignments: list[str] = []
    for item in as_list(palette.get("assignments")):
        if isinstance(item, dict):
            component = item.get("component")
            palette_id = item.get("palette_id")
            role = item.get("usage_role")
            if component and palette_id:
                palette_assignments.append(f"{component}: {palette_id}" + (f" ({role})" if role else ""))

    material_assignments: list[str] = []
    materials = ias.get("materials", {})
    if isinstance(materials, dict):
        for item in as_list(materials.get("assignments")):
            if isinstance(item, dict) and item.get("component") and item.get("material_id"):
                material_assignments.append(f"{item['component']}: {item['material_id']}")

    framing = camera.get("framing", {}) if isinstance(camera.get("framing"), dict) else {}
    pivot = camera.get("pivot", {}) if isinstance(camera.get("pivot"), dict) else {}
    primary_light = lighting.get("primary_light", {}) if isinstance(lighting.get("primary_light"), dict) else {}
    shadow = lighting.get("shadow", {}) if isinstance(lighting.get("shadow"), dict) else {}

    provider_neutral = str(guidance.get("provider_neutral_description", "")).strip()
    silhouette_description = str(silhouette.get("description", "")).strip()

    lines = [
        "# GAPS_XenoWarrior Compiled Generation Prompt",
        "",
        "> GENERATED FILE — DO NOT HAND-EDIT.",
        "> If this prompt is wrong, correct the YAML source or compiler and rebuild it.",
        "",
        "## Build Identity",
        f"- Build ID: {build_id}",
        f"- Asset ID: {asset_id}",
        f"- Asset name: {asset_name}",
        f"- Asset type: {identity.get('asset_type', 'unspecified')}",
        "",
        "## Objective",
        objective,
        "",
        "## Provider-Neutral Asset Definition",
        provider_neutral or silhouette_description or "No approved description supplied; compilation should have been blocked.",
        "",
        "## Rendering Contract",
        f"- Style: {style.get('style_name', 'Military Retro Sci-Fi')}",
        f"- Realism level: {style.get('realism_level', 'low')}",
        f"- Arcade readability: {style.get('arcade_readability', 'maximum')}",
        f"- Shading method: {render.get('shading_method', 'two_tone_cel')}",
        f"- Shading levels: {render.get('shading_levels', 2)}",
        f"- Shadow multiplier: {render.get('shadow_brightness_multiplier', palette.get('shadow_multiplier', 0.65))}",
        f"- Outline: {outline.get('width_px', 4)} px, {outline.get('color_reference', 'PALETTE_SHADOW_BLACK')}, uniform={outline.get('uniform', True)}",
        "",
        "## Silhouette and Construction",
        silhouette_description or "Use the approved construction specification without reinterpretation.",
        bullets(positive),
        "",
        "## Palette Assignments",
        bullets(palette_assignments),
        "",
        "## Material Assignments",
        bullets(material_assignments),
        "",
        "## Camera and Framing",
        f"- Projection: {camera.get('projection')}",
        f"- Orientation: {camera.get('orientation')}",
        f"- Rotation: pitch {camera.get('pitch_degrees')}°, yaw {camera.get('yaw_degrees')}°, roll {camera.get('roll_degrees')}°",
        f"- Field of view: {camera.get('field_of_view_degrees')}°",
        f"- Entire asset visible: {framing.get('full_asset_visible')}",
        f"- Clipping allowed: {framing.get('clipping_allowed')}",
        f"- Pivot: x={pivot.get('x')}, y={pivot.get('y')} ({pivot.get('units')})",
        "",
        "## Lighting",
        f"- Primary light: {primary_light.get('horizontal_direction')} and {primary_light.get('vertical_direction')}, {primary_light.get('angle_degrees')}°, intensity {primary_light.get('intensity')}",
        f"- Fill light enabled: {lighting.get('fill_light_enabled')}",
        f"- Ambient light enabled: {lighting.get('ambient_light_enabled')}",
        f"- Shadow edge: {shadow.get('edge')}; blur allowed: {shadow.get('blur_allowed')}",
        "",
        "## Output Contract",
        f"- Output type: {export.get('output_type')}",
        f"- File format: {export.get('image_format')}",
        f"- Canvas: {export.get('width_px')} × {export.get('height_px')} pixels",
        f"- Color space: {export.get('color_space')}",
        f"- Alpha: {export.get('alpha')}",
        f"- Transparent background: {export.get('transparent_background')}",
        f"- Safe transparent padding: {export.get('safe_padding_px')} px",
        f"- Trim transparency: {export.get('trim_transparency')}",
        "",
        "## Absolute Prohibitions",
        bullets(prohibited),
        "",
        "## Execution Instruction",
        "Generate only the requested production artwork. Return no poster, explanation, labels, UI, metadata panel, or alternate design. The repository specification outranks model creativity.",
        "",
    ]
    return "\n".join(lines)


def write_manifest(
    destination: Path,
    repo_root: Path,
    build_yaml: LoadedYaml,
    ias_yaml: LoadedYaml,
    dependencies: list[LoadedYaml],
    prompt_path: Path,
    allow_draft: bool,
) -> None:
    all_sources = [build_yaml, ias_yaml, *dependencies]
    manifest = {
        "metadata": {
            "type": "generation_manifest",
            "compiler": "GAPS build_prompt.py",
            "compiler_version": "0.1.1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "draft_override_used": allow_draft,
        },
        "output": {
            "prompt_file": prompt_path.relative_to(repo_root).as_posix(),
            "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        },
        "sources": [
            {
                "file": source.path.relative_to(repo_root).as_posix(),
                "sha256": source.sha256,
            }
            for source in all_sources
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")



def write_build_report(
    destination: Path,
    repo_root: Path,
    build_yaml: LoadedYaml,
    ias_yaml: LoadedYaml,
    dependencies: list[LoadedYaml],
    prompt_path: Path,
    manifest_path: Path,
    allow_draft: bool,
) -> None:
    """Write a human-readable, permanent record of one compiler execution."""
    build_meta = require_mapping(build_yaml.data, "metadata", "Build")
    identity = require_mapping(ias_yaml.data, "identity", "IAS")
    ias_meta = require_mapping(ias_yaml.data, "metadata", "IAS")
    ias_doc = require_mapping(ias_meta, "document", "IAS.metadata")

    status = str(ias_doc.get("status", "MISSING")).upper()
    authorization = "TEST BUILD — NOT PRODUCTION AUTHORIZED" if allow_draft else "PRODUCTION-AUTHORIZED COMPILATION"
    warnings: list[str] = []
    if allow_draft:
        warnings.append("The --allow-draft override was used. Generated outputs are for compiler testing only.")
    if status != "APPROVED":
        warnings.append(f"IAS status is {status}, not APPROVED.")

    unresolved = ias_yaml.data.get("unresolved_requirements", {})
    if isinstance(unresolved, dict):
        blocking = [
            str(item.get("path", "unknown path"))
            for item in as_list(unresolved.get("items"))
            if isinstance(item, dict) and item.get("blocks_generation") is True
        ]
        if blocking:
            warnings.append("Generation-blocking IAS requirements remain: " + ", ".join(blocking))

    generated_at = datetime.now(timezone.utc).isoformat()
    source_rows = [build_yaml, ias_yaml, *dependencies]
    source_lines = [
        f"| `{source.path.relative_to(repo_root).as_posix()}` | `{source.sha256}` |"
        for source in source_rows
    ]

    lines = [
        "# GAPS_XenoWarrior Build Report",
        "",
        f"**Build ID:** `{build_meta.get('build_id', 'UNKNOWN')}`  ",
        f"**Asset:** `{identity.get('asset_id', 'UNKNOWN')}` — {identity.get('asset_name', 'Unnamed asset')}  ",
        f"**Compiler version:** `0.1.1`  ",
        f"**Generated at (UTC):** `{generated_at}`  ",
        f"**Authorization:** **{authorization}**",
        "",
        "## Outputs",
        "",
        f"- Prompt: `{prompt_path.relative_to(repo_root).as_posix()}`",
        f"- Manifest: `{manifest_path.relative_to(repo_root).as_posix()}`",
        f"- Build report: `{destination.relative_to(repo_root).as_posix()}`",
        "",
        "## Source State",
        "",
        f"- IAS status: `{status}`",
        f"- Draft override used: `{allow_draft}`",
        f"- Dependency files loaded: `{len(dependencies)}`",
        "",
        "## Warnings",
        "",
        *( [f"- {warning}" for warning in warnings] if warnings else ["- None."] ),
        "",
        "## Reproducibility Sources",
        "",
        "| Repository file | SHA-256 |",
        "|---|---|",
        *source_lines,
        "",
        "## Operating Rule",
        "",
        "`Prompt.md` is a generated build artifact. Do not hand-edit it. Correct the approved YAML source or compiler, then rebuild.",
        "",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    build_path = args.build_request.resolve()
    repo_root = args.repo_root.resolve() if args.repo_root else find_repo_root(build_path)
    build_yaml = load_yaml(build_path)
    _, asset_cfg, output_cfg = validate_build(build_yaml.data)

    ias_path = resolve_repo_path(repo_root, require_text(asset_cfg, "ias_file", "Build.asset"))
    ias_yaml = load_yaml(ias_path)
    validate_ias(ias_yaml.data, args.allow_draft)
    dependencies = collect_referenced_yaml(repo_root, ias_yaml.data)

    prompt_path = resolve_output_path(repo_root, build_path.parent, output_cfg["prompt_file"])
    manifest_path = resolve_output_path(repo_root, build_path.parent, output_cfg["manifest_file"])
    report_path = resolve_output_path(repo_root, build_path.parent, output_cfg["report_file"])

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(compile_prompt(build_yaml.data, ias_yaml.data), encoding="utf-8")
    write_manifest(
        manifest_path,
        repo_root,
        build_yaml,
        ias_yaml,
        dependencies,
        prompt_path,
        args.allow_draft,
    )
    write_build_report(
        report_path,
        repo_root,
        build_yaml,
        ias_yaml,
        dependencies,
        prompt_path,
        manifest_path,
        args.allow_draft,
    )

    print(f"Compiled prompt: {prompt_path}")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Wrote build report: {report_path}")
    if args.allow_draft:
        print("WARNING: --allow-draft was used; output is not production-authorized.")
    return 0


def resolve_output_path(repo_root: Path, build_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise CompilerError("Output paths must be relative, not absolute.")
    # Simple filenames live beside Build.yaml. Paths containing folders are repo-relative.
    destination = build_dir / candidate if len(candidate.parts) == 1 else repo_root / candidate
    resolved_parent = destination.parent.resolve()
    try:
        resolved_parent.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise CompilerError(f"Output path escapes repository root: {value}") from exc
    return destination.resolve()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompilerError as exc:
        print(f"COMPILER ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
