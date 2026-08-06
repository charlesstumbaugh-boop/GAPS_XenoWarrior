"""Generate ReviewChecklist.md from compiler-owned build context."""

from __future__ import annotations

from typing import Any

GENERATOR_VERSION = "1.0.0"


class ChecklistGeneratorError(RuntimeError):
    """Raised when a review checklist cannot be generated safely."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ChecklistGeneratorError(f"{label} must be a mapping.")
    return value


def _text(value: Any, fallback: str = "Not specified") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _checkbox(label: str, note: str | None = None) -> str:
    suffix = f" — {note}" if note else ""
    return f"- [ ] {label}{suffix}"


def generate(context: dict[str, Any]) -> str:
    """Build and return ReviewChecklist.md text without writing a file."""
    context = _mapping(context, "context")
    build = _mapping(context.get("build"), "context.build")
    ias = _mapping(context.get("ias"), "context.ias")
    identity = _mapping(ias.get("identity"), "IAS.identity")
    validation_cfg = _mapping(context.get("validation"), "context.validation")

    metadata = _mapping(build.get("metadata"), "Build.metadata")
    asset_id = _text(identity.get("asset_id"), "UNKNOWN-ASSET")
    asset_name = _text(identity.get("asset_name"), asset_id)
    build_id = _text(metadata.get("build_id"), "UNKNOWN-BUILD")

    ias_validation = ias.get("validation", {})
    acceptance = []
    automatic_rejection = []
    if isinstance(ias_validation, dict):
        raw_acceptance = ias_validation.get("acceptance_criteria", [])
        if isinstance(raw_acceptance, list):
            acceptance = [str(item) for item in raw_acceptance]
        elif isinstance(raw_acceptance, dict):
            acceptance = [str(key) for key, value in raw_acceptance.items() if value]

        raw_rejection = ias_validation.get("automatic_rejection", [])
        if isinstance(raw_rejection, list):
            automatic_rejection = [str(item) for item in raw_rejection]

    export = ias.get("export", {})
    export = export if isinstance(export, dict) else {}
    references = context.get("references", [])
    if not isinstance(references, list):
        raise ChecklistGeneratorError("context.references must be a list.")

    warnings = validation_cfg.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []

    lines = [
        "# Asset Review Checklist",
        "",
        f"- **Generator version:** {GENERATOR_VERSION}",
        f"- **Build ID:** `{build_id}`",
        f"- **Asset ID:** `{asset_id}`",
        f"- **Asset name:** {asset_name}",
        f"- **Build mode:** {'Draft' if validation_cfg.get('draft_override_used') else 'Production'}",
        f"- **Production authorized:** {'Yes' if validation_cfg.get('production_authorized') else 'No'}",
        "",
        "## Reviewer Instructions",
        "",
        "Review the generated candidate against the compiled Prompt.md, declared references, and this checklist. Do not promote the asset when any required item fails.",
        "",
        "## File and Output Checks",
        "",
        _checkbox("Exactly one production asset is present"),
        _checkbox(f"Canvas is {export.get('width_px', 1024)} × {export.get('height_px', 1024)} pixels"),
        _checkbox("PNG uses real RGBA transparency"),
        _checkbox("No baked checkerboard or opaque background is present"),
        _checkbox("Entire body or asset is visible with no clipping"),
        _checkbox("No title, labels, footer, logo, UI panel, or presentation layout is present"),
        "",
        "## Identity and Visual Checks",
        "",
    ]

    if acceptance:
        for item in acceptance:
            lines.append(_checkbox(_humanize(item)))
    else:
        lines.extend([
            _checkbox("Silhouette matches the IAS"),
            _checkbox("Palette matches approved Core assignments"),
            _checkbox("Rendering and outline treatment match the approved style"),
            _checkbox("Camera orientation and proportions match the IAS"),
        ])

    lines.extend(["", "## Reference Contract Checks", ""])
    if references:
        for ref in references:
            if not isinstance(ref, dict):
                continue
            ref_id = _text(ref.get("reference_id"), "UNKNOWN-REFERENCE")
            relationship = _text(ref.get("relationship"), "unspecified")
            resolved = ref.get("resolved") is True
            lines.append(_checkbox(
                f"Reference `{ref_id}` is resolved",
                "resolved by compiler" if resolved else "UNRESOLVED — do not approve",
            ))
            lines.append(_checkbox(
                f"Reference `{ref_id}` was used only as `{relationship}`",
            ))
            if relationship == "style_only":
                lines.append(_checkbox(
                    f"`{ref_id}` did not transfer silhouette, helmet, armor layout, weapon identity, or proportions",
                ))
    else:
        lines.append(_checkbox("No undeclared reference influenced the asset"))

    lines.extend(["", "## Automatic Rejection Review", ""])
    if automatic_rejection:
        for item in automatic_rejection:
            lines.append(_checkbox(f"Not present: {_humanize(item)}"))
    else:
        lines.extend([
            _checkbox("No unauthorized redesign is present"),
            _checkbox("No unapproved colors or materials are present"),
            _checkbox("No incorrect camera view or dimensionality is present"),
        ])

    lines.extend(["", "## Compiler Warnings", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- [ ] Review warning: {warning}")
    else:
        lines.append("- No compiler warnings were recorded.")

    lines.extend([
        "",
        "## Review Decision",
        "",
        "- [ ] PASS — candidate may proceed to validate_reference.py",
        "- [ ] FAIL — candidate must be rejected or revised",
        "",
        "**Reviewer:** ______________________________",
        "",
        "**Review date:** ___________________________",
        "",
        "**Notes:**",
        "",
        "____________________________________________________________________",
        "",
        "____________________________________________________________________",
        "",
    ])

    return "\n".join(lines)
