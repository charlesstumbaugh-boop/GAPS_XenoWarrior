#!/usr/bin/env python3
"""Generate Prompt.md text from a validated GAPS build context.

This module does not read or write files. The compiler orchestrator owns paths,
validation, and output writes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class PromptGeneratorError(ValueError):
    """Raised when the prompt context is structurally incomplete."""


def _require_context_mapping(context: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = context.get(key)
    if not isinstance(value, dict):
        raise PromptGeneratorError(f"Missing or invalid context mapping: {key}")
    return value


def require_mapping(parent: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise PromptGeneratorError(f"Missing or invalid mapping {context}.{key}")
    return value


def require_text(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PromptGeneratorError(f"Missing or invalid text {context}.{key}")
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


def generate(context: Mapping[str, Any]) -> str:
    """Build and return the compiled Prompt.md text."""
    build = _require_context_mapping(context, "build")
    ias = _require_context_mapping(context, "ias")
    references = context.get("references", [])
    if not isinstance(references, list):
        raise PromptGeneratorError("context.references must be a list")
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

    immutable_features = text_list(as_list(restrictions.get("immutable_features")))
    prohibited_silhouette = text_list(as_list(silhouette.get("prohibited_silhouette_changes")))
    component_design = ias.get("component_design", {})
    component_names = list(component_design.keys()) if isinstance(component_design, dict) else []

    identity_refs = [r for r in references if r.relationship == "identity"]
    style_refs = [r for r in references if r.relationship == "style_only"]
    unclassified_refs = [r for r in references if r.relationship == "unclassified"]

    reference_lines: list[str] = []
    for ref in references:
        path_text = (
            ref.resolved_path.as_posix() if ref.resolved_path is not None else ref.requested_path or "UNRESOLVED"
        )
        reference_lines.append(
            f"{ref.reference_id}: {path_text} — relationship={ref.relationship}; "
            f"authority={ref.authority_level}; purpose={ref.purpose or 'not stated'}"
        )

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
        "## Reference Image Contract",
        bullets(reference_lines, "No resolved visual references are available in this draft build."),
        "",
        "### Reference Relationship Rules",
        f"- Identity references: {', '.join(r.reference_id for r in identity_refs) or 'none declared'}",
        f"- Style-only references: {', '.join(r.reference_id for r in style_refs) or 'none declared'}",
        f"- Unclassified references: {', '.join(r.reference_id for r in unclassified_refs) or 'none'}",
        "- Identity references define this asset's own approved geometry and component design.",
        "- Style-only references may transfer rendering language, line treatment, palette discipline, lighting, and finish only.",
        "- Never copy helmet geometry, armor layout, silhouette, weapon design, proportions, markings, or component arrangement from a style-only reference.",
        "- A new asset must remain immediately distinguishable from every style-only reference.",
        "",
        "## Asset Identity Lock",
        f"- Immutable features: {', '.join(immutable_features) or 'none declared'}",
        f"- Named component groups: {', '.join(component_names) or 'none declared'}",
        bullets(prohibited_silhouette, "No additional silhouette prohibitions declared."),
        "- Do not reduce this asset to a recolor, reskin, mirrored version, or equipment swap of another character.",
        "- Preserve the asset-specific silhouette, helmet language, torso construction, limb proportions, weapon silhouette, and gameplay read defined by its IAS.",
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
