#!/usr/bin/env python3
"""GAPS_XenoWarrior deterministic prompt compiler, Phase 2.

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


@dataclass(frozen=True)
class ValidationResult:
    checks: tuple[str, ...]
    warnings: tuple[str, ...]
    production_authorized: bool


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


def find_forbidden_keys(value: Any, path: str = "Build") -> list[str]:
    """Return forbidden handwritten prompt fields found anywhere in Build.yaml."""
    forbidden = {
        "prompt",
        "free_form_prompt",
        "provider_prompt",
        "positive_prompt",
        "negative_prompt",
        "system_prompt",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).casefold() in forbidden:
                found.append(child_path)
            found.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def validate_build(build: dict[str, Any], allow_draft: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    checks: list[str] = []
    forbidden_fields = find_forbidden_keys(build)
    if forbidden_fields:
        raise CompilerError(
            "Build Request contains forbidden handwritten prompt fields: "
            + ", ".join(forbidden_fields)
        )
    checks.append("No handwritten prompt fields are present.")

    metadata = require_mapping(build, "metadata", "Build")
    asset = require_mapping(build, "asset", "Build")
    output = require_mapping(build, "output", "Build")
    execution = require_mapping(build, "execution", "Build")

    build_id = require_text(metadata, "build_id", "Build.metadata")
    build_type = require_text(metadata, "build_type", "Build.metadata")
    ias_file = require_text(asset, "ias_file", "Build.asset")
    prompt_file = require_text(output, "prompt_file", "Build.output")
    manifest_file = require_text(output, "manifest_file", "Build.output")
    report_file = output.get("report_file", "BuildReport.md")
    if not isinstance(report_file, str) or not report_file.strip():
        raise CompilerError("Missing or invalid text Build.output.report_file")
    output["report_file"] = report_file.strip()

    expected_extensions = {
        "prompt_file": ".md",
        "manifest_file": ".yaml",
        "report_file": ".md",
    }
    for key, extension in expected_extensions.items():
        value = str(output[key])
        if Path(value).suffix.casefold() != extension:
            raise CompilerError(f"Build.output.{key} must end with {extension}: {value}")
    if len({prompt_file.casefold(), manifest_file.casefold(), report_file.strip().casefold()}) != 3:
        raise CompilerError("Prompt, manifest, and report outputs must use distinct file names.")
    checks.append("Output file names and extensions are valid and distinct.")

    if execution.get("handwritten_prompt_allowed") is not False:
        raise CompilerError("Build.execution.handwritten_prompt_allowed must be false.")
    if execution.get("repository_is_source_of_truth") is not True:
        raise CompilerError("Build.execution.repository_is_source_of_truth must be true.")
    production_requested = execution.get("production_authorized") is True
    if not allow_draft and not production_requested:
        raise CompilerError(
            "Production compilation requires Build.execution.production_authorized: true. "
            "Use --allow-draft only for compiler testing."
        )
    checks.append("Execution policy requires repository authority and forbids handwritten prompts.")

    objective = str(build.get("objective", "")).casefold()
    prohibited_objective_terms = (
        "presentation sheet", "infographic", "poster", "character sheet",
        "label bar", "footer", "checkerboard background", "opaque background",
        "crop the", "cropped character",
    )
    violations = [term for term in prohibited_objective_terms if term in objective]
    if violations:
        raise CompilerError(
            "Build objective requests prohibited output behavior: " + ", ".join(violations)
        )
    checks.append("Build objective contains no prohibited presentation or background request.")

    if not build_id or not build_type or not ias_file:
        raise CompilerError("Build identity is incomplete.")
    checks.append("Build identity and IAS reference are present.")
    return metadata, asset, output, checks


def validate_ias(ias: dict[str, Any], allow_draft: bool, production_requested: bool) -> ValidationResult:
    checks: list[str] = []
    warnings: list[str] = []

    required_sections = (
        "metadata", "identity", "source_versions", "inheritance",
        "visual_contract", "construction", "materials", "palette", "camera",
        "lighting", "animation", "export", "restrictions", "validation",
        "approval", "history",
    )
    missing = [section for section in required_sections if not isinstance(ias.get(section), dict)]
    if missing:
        raise CompilerError("IAS is missing required mappings: " + ", ".join(missing))
    checks.append("All mandatory IAS sections are present.")

    metadata = require_mapping(ias, "metadata", "IAS")
    document = require_mapping(metadata, "document", "IAS.metadata")
    identity = require_mapping(ias, "identity", "IAS")
    approval = require_mapping(ias, "approval", "IAS")
    require_text(identity, "asset_id", "IAS.identity")
    require_text(identity, "asset_name", "IAS.identity")

    status = str(document.get("status", "")).upper()
    approval_status = str(approval.get("status", "")).upper()
    if status != "APPROVED":
        if allow_draft:
            warnings.append(f"IAS document status is {status or 'MISSING'}, not APPROVED.")
        else:
            raise CompilerError(f"IAS document status is {status or 'MISSING'}, not APPROVED.")
    if production_requested:
        production_failures: list[str] = []
        if status != "APPROVED":
            production_failures.append("metadata.document.status is not APPROVED")
        if approval_status != "APPROVED":
            production_failures.append("approval.status is not APPROVED")
        if approval.get("generation_authorized") is not True:
            production_failures.append("approval.generation_authorized is not true")
        if approval.get("locked") is not True:
            production_failures.append("approval.locked is not true")
        if production_failures:
            raise CompilerError("Production authorization failed: " + "; ".join(production_failures))
    checks.append("IAS approval state is compatible with requested build mode.")

    unresolved = ias.get("unresolved_requirements", {})
    blocking: list[str] = []
    if isinstance(unresolved, dict):
        for item in as_list(unresolved.get("items")):
            if isinstance(item, dict) and item.get("blocks_generation") is True:
                blocking.append(str(item.get("path", "unknown path")))
    if blocking:
        if allow_draft:
            warnings.append("Generation blockers remain: " + ", ".join(blocking))
        else:
            raise CompilerError(
                "IAS has unresolved requirements that block generation: " + ", ".join(blocking)
            )
    checks.append("Generation-blocking unresolved requirements were evaluated.")

    export = require_mapping(ias, "export", "IAS")
    if str(export.get("image_format", "")).casefold() != "png":
        raise CompilerError("IAS.export.image_format must be png for production artwork.")
    if export.get("transparent_background") is not True:
        raise CompilerError("IAS.export.transparent_background must be true.")
    if export.get("trim_transparency") is not False:
        raise CompilerError("IAS.export.trim_transparency must be false to preserve frame alignment.")
    for key in ("width_px", "height_px"):
        value = export.get(key)
        if not isinstance(value, int) or value <= 0:
            raise CompilerError(f"IAS.export.{key} must be a positive integer.")
    checks.append("PNG, transparency, canvas dimensions, and untrimmed alignment are valid.")

    camera = require_mapping(ias, "camera", "IAS")
    framing = require_mapping(camera, "framing", "IAS.camera")
    if camera.get("orientation") not in {"forward_facing", "camera_facing", "gameplay_facing"}:
        raise CompilerError("IAS.camera.orientation is not an approved front/gameplay-facing value.")
    if framing.get("full_asset_visible") is not True:
        raise CompilerError("IAS.camera.framing.full_asset_visible must be true.")
    if framing.get("clipping_allowed") is not False:
        raise CompilerError("IAS.camera.framing.clipping_allowed must be false.")
    checks.append("Camera orientation, full visibility, and no-clipping rules are valid.")

    palette = require_mapping(ias, "palette", "IAS")
    if palette.get("raw_color_values_present") is not False:
        raise CompilerError("IAS.palette.raw_color_values_present must be false.")
    if not as_list(palette.get("assignments")):
        raise CompilerError("IAS.palette.assignments must contain at least one approved palette assignment.")
    checks.append("Palette uses approved references rather than raw colors.")

    restrictions = require_mapping(ias, "restrictions", "IAS")
    if restrictions.get("redesign_allowed") is not False:
        raise CompilerError("IAS.restrictions.redesign_allowed must be false.")
    if restrictions.get("change_requires_approval") is not True:
        raise CompilerError("IAS.restrictions.change_requires_approval must be true.")
    checks.append("Redesign is forbidden and changes require approval.")

    visual = require_mapping(ias, "visual_contract", "IAS")
    outline = require_mapping(visual, "outline", "IAS.visual_contract")
    if outline.get("uniform") is not True:
        raise CompilerError("IAS.visual_contract.outline.uniform must be true.")
    if not isinstance(outline.get("width_px"), (int, float)) or outline.get("width_px") <= 0:
        raise CompilerError("IAS.visual_contract.outline.width_px must be positive.")
    checks.append("Outline contract is explicit and valid.")

    return ValidationResult(tuple(checks), tuple(warnings), production_requested and not allow_draft)


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
        "## Locked Production Output",
        "- Deliver exactly one production asset image.",
        "- Do not create a poster, infographic, character sheet, contact sheet, comparison board, or documentation panel.",
        "- Do not add titles, captions, labels, footers, frame numbers, logos, watermarks, borders, UI, or metadata inside the image.",
        "- Background must be true alpha transparency; do not draw or bake a checkerboard pattern.",
        f"- Canvas must remain exactly {export.get('width_px')} × {export.get('height_px')} pixels.",
        f"- Entire asset visible: {framing.get('full_asset_visible')}; clipping allowed: {framing.get('clipping_allowed')}.",
        f"- Orientation is locked to {camera.get('orientation')}.",
        "- Do not add scenery, floors, pedestals, cast shadows, atmosphere, or decorative elements.",
        "- Do not redesign, restyle, recolor, mirror, crop, or substitute components.",
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
        "Generate exactly one clean production asset and nothing else. Apply every locked requirement above literally. Do not improvise outside the repository-defined design. The repository specification outranks model creativity.",
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
    validation: ValidationResult,
) -> None:
    all_sources = [build_yaml, ias_yaml, *dependencies]
    manifest = {
        "metadata": {
            "type": "generation_manifest",
            "compiler": "GAPS build_prompt.py",
            "compiler_version": "0.3.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "draft_override_used": allow_draft,
            "validation_passed": True,
            "validation_check_count": len(validation.checks),
            "production_authorized": validation.production_authorized,
        },
        "output": {
            "prompt_file": prompt_path.relative_to(repo_root).as_posix(),
            "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        },
        "validation": {
            "checks": list(validation.checks),
            "warnings": list(validation.warnings),
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
    validation: ValidationResult,
) -> None:
    """Write a human-readable, permanent record of one compiler execution."""
    build_meta = require_mapping(build_yaml.data, "metadata", "Build")
    identity = require_mapping(ias_yaml.data, "identity", "IAS")
    ias_meta = require_mapping(ias_yaml.data, "metadata", "IAS")
    ias_doc = require_mapping(ias_meta, "document", "IAS.metadata")

    status = str(ias_doc.get("status", "MISSING")).upper()
    authorization = "TEST BUILD — NOT PRODUCTION AUTHORIZED" if allow_draft else "PRODUCTION-AUTHORIZED COMPILATION"
    warnings: list[str] = list(validation.warnings)
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
        f"**Compiler version:** `0.3.0`  ",
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
        "## Preflight Validation",
        "",
        f"- Checks passed: `{len(validation.checks)}`",
        f"- Production authorized: `{validation.production_authorized}`",
        *[f"- PASS — {check}" for check in validation.checks],
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
    _, asset_cfg, output_cfg, build_checks = validate_build(build_yaml.data, args.allow_draft)

    ias_path = resolve_repo_path(repo_root, require_text(asset_cfg, "ias_file", "Build.asset"))
    ias_yaml = load_yaml(ias_path)
    execution_cfg = require_mapping(build_yaml.data, "execution", "Build")
    validation = validate_ias(
        ias_yaml.data,
        args.allow_draft,
        execution_cfg.get("production_authorized") is True,
    )
    validation = ValidationResult(
        tuple(build_checks) + validation.checks,
        validation.warnings,
        validation.production_authorized,
    )
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
        validation,
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
        validation,
    )

    print(f"Validation passed: {len(validation.checks)} checks")
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
