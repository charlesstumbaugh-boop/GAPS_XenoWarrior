"""Generate the front-page GenerationPackage.md artifact."""

from __future__ import annotations

from typing import Any

GENERATOR_VERSION = "1.0.0"


class PackageGeneratorError(RuntimeError):
    """Raised when generation-package context is incomplete."""


def _mapping(parent: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise PackageGeneratorError(f"Missing or invalid mapping {context}.{key}")
    return value


def _text(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PackageGeneratorError(f"Missing or invalid text {context}.{key}")
    return value.strip()


def _link(label: str, filename: str) -> str:
    return f"- [{label}]({filename})"


def generate(context: dict[str, Any]) -> str:
    """Return GenerationPackage.md text without writing files."""
    build = _mapping(context, "build", "context")
    ias = _mapping(context, "ias", "context")
    validation = _mapping(context, "validation", "context")
    outputs = _mapping(context, "outputs", "context")

    metadata = _mapping(build, "metadata", "Build")
    identity = _mapping(ias, "identity", "IAS")

    build_id = _text(metadata, "build_id", "Build.metadata")
    asset_id = _text(identity, "asset_id", "IAS.identity")
    asset_name = _text(identity, "asset_name", "IAS.identity")

    warnings = validation.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    references = context.get("references", [])
    if not isinstance(references, list):
        references = []

    production_authorized = validation.get("production_authorized") is True
    draft_override = validation.get("draft_override_used") is True
    status = "PRODUCTION AUTHORIZED" if production_authorized else "DRAFT / NOT PRODUCTION AUTHORIZED"

    artifact_rows = [
        ("Build Request", "build_request"),
        ("Compiled Prompt", "prompt"),
        ("Generation Manifest", "manifest"),
        ("Build Report", "build_report"),
        ("Reference List", "reference_list"),
        ("Review Checklist", "review_checklist"),
    ]

    lines = [
        "# GAPS Generation Package",
        "",
        f"- **Generator version:** {GENERATOR_VERSION}",
        f"- **Build ID:** `{build_id}`",
        f"- **Asset:** `{asset_id}` — {asset_name}",
        f"- **Package status:** **{status}**",
        f"- **Draft override used:** {'Yes' if draft_override else 'No'}",
        "",
        "## Purpose",
        "",
        "This file is the front page for the complete compiler-generated asset build package. "
        "Use the artifacts below in order; do not replace the compiled prompt with handwritten instructions.",
        "",
        "## Package Artifacts",
        "",
    ]

    for label, key in artifact_rows:
        filename = outputs.get(key)
        if isinstance(filename, str) and filename.strip():
            lines.append(_link(label, filename.strip()))

    lines.extend([
        "",
        "## Required Workflow",
        "",
        "1. Review the Build Report for warnings and authorization state.",
        "2. Review the Reference List and confirm every reference role is correct.",
        "3. Use Prompt.md exactly as compiled for generation.",
        "4. Save the generated PNG as a candidate, never directly as a Gold Master.",
        "5. Complete ReviewChecklist.md against the candidate.",
        "6. Run reference validation.",
        "7. Promote only through the Gold Master promotion tool after approval.",
        "",
        "## Reference Summary",
        "",
        f"- **References evaluated:** {len(references)}",
    ])

    if references:
        for reference in references:
            if not isinstance(reference, dict):
                continue
            ref_id = reference.get("reference_id", "UNNAMED_REFERENCE")
            role = reference.get("relationship", "undeclared")
            resolved = "Yes" if reference.get("resolved") is True else "No"
            lines.append(f"- `{ref_id}` — role: `{role}`; resolved: **{resolved}**")
    else:
        lines.append("- No reference images declared.")

    lines.extend([
        "",
        "## Compiler Warnings",
        "",
    ])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")

    lines.extend([
        "",
        "## Release Gate",
        "",
    ])
    if production_authorized:
        lines.append("The compiler marked this package production-authorized. Candidate review and promotion are still required.")
    else:
        lines.append("This package is not production-authorized. It may be used only for draft testing and review.")

    lines.extend([
        "",
        "## Human Review",
        "",
        "- [ ] Build package reviewed",
        "- [ ] Reference roles confirmed",
        "- [ ] Candidate generated from compiled prompt",
        "- [ ] Candidate checklist completed",
        "- [ ] Candidate validator passed",
        "- [ ] Project Owner approved promotion",
        "",
    ])
    return "\n".join(lines)
