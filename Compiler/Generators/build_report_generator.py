"""Generate deterministic GAPS BuildReport.md text.

This module returns Markdown text. It does not read repository files, resolve
paths, create directories, or write output files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

GENERATOR_VERSION = "1.0.0"
COMPILER_VERSION = "0.4.0"


class BuildReportGeneratorError(RuntimeError):
    """Raised when build-report context is incomplete or invalid."""


def _mapping(context: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = context.get(key)
    if not isinstance(value, Mapping):
        raise BuildReportGeneratorError(f"Missing or invalid report context mapping: {key}")
    return value


def _list(context: Mapping[str, Any], key: str) -> list[Any]:
    value = context.get(key)
    if not isinstance(value, list):
        raise BuildReportGeneratorError(f"Missing or invalid report context list: {key}")
    return value


def generate(context: Mapping[str, Any]) -> str:
    """Build and return BuildReport.md text without writing a file."""
    build = _mapping(context, "build")
    ias = _mapping(context, "ias")
    validation = _mapping(context, "validation")
    outputs = _mapping(context, "outputs")
    sources = _list(context, "sources")
    references = _list(context, "reference_images")

    build_meta = _mapping(build, "metadata")
    identity = _mapping(ias, "identity")
    ias_meta = _mapping(ias, "metadata")
    ias_doc = _mapping(ias_meta, "document")

    checks = validation.get("checks")
    warnings = validation.get("warnings")
    if not isinstance(checks, list) or not all(isinstance(x, str) for x in checks):
        raise BuildReportGeneratorError("validation.checks must be a list of strings")
    if not isinstance(warnings, list) or not all(isinstance(x, str) for x in warnings):
        raise BuildReportGeneratorError("validation.warnings must be a list of strings")

    draft = context.get("draft_override_used")
    production = context.get("production_authorized")
    dependency_count = context.get("dependencies_loaded")
    if not isinstance(draft, bool) or not isinstance(production, bool):
        raise BuildReportGeneratorError("authorization flags must be boolean")
    if not isinstance(dependency_count, int):
        raise BuildReportGeneratorError("dependencies_loaded must be an integer")

    status = str(ias_doc.get("status", "MISSING")).upper()
    report_warnings = list(warnings)
    if draft:
        report_warnings.append("The --allow-draft override was used. Generated outputs are for compiler testing only.")
    if status != "APPROVED":
        report_warnings.append(f"IAS status is {status}, not APPROVED.")

    unresolved = ias.get("unresolved_requirements")
    if isinstance(unresolved, Mapping):
        items = unresolved.get("items")
        if isinstance(items, list):
            blocking = [
                str(item.get("path", "unknown path"))
                for item in items
                if isinstance(item, Mapping) and item.get("blocks_generation") is True
            ]
            if blocking:
                report_warnings.append("Generation-blocking IAS requirements remain: " + ", ".join(blocking))

    authorization = (
        "TEST BUILD — NOT PRODUCTION AUTHORIZED"
        if draft else "PRODUCTION-AUTHORIZED COMPILATION"
    )

    source_lines = []
    for source in sources:
        if not isinstance(source, Mapping):
            raise BuildReportGeneratorError("Each source must be a mapping")
        source_lines.append(f"| `{source.get('file', 'UNKNOWN')}` | `{source.get('sha256', 'UNKNOWN')}` |")

    reference_lines = []
    for reference in references:
        if not isinstance(reference, Mapping):
            raise BuildReportGeneratorError("Each reference image must be a mapping")
        location = f"`{reference.get('file', 'UNKNOWN')}`" if reference.get("resolved") else "**UNRESOLVED**"
        reference_lines.append(
            f"- `{reference.get('reference_id', 'UNKNOWN')}` — "
            f"`{reference.get('relationship', 'unknown')}` — {location}"
        )

    lines = [
        "# GAPS_XenoWarrior Build Report",
        "",
        f"**Build ID:** `{build_meta.get('build_id', 'UNKNOWN')}`  ",
        f"**Asset:** `{identity.get('asset_id', 'UNKNOWN')}` — {identity.get('asset_name', 'Unnamed asset')}  ",
        f"**Compiler version:** `{COMPILER_VERSION}`  ",
        f"**Build report generator version:** `{GENERATOR_VERSION}`  ",
        f"**Generated at (UTC):** `{datetime.now(timezone.utc).isoformat()}`  ",
        f"**Authorization:** **{authorization}**",
        "",
        "## Outputs",
        "",
        f"- Prompt: `{outputs.get('prompt', 'UNKNOWN')}`",
        f"- Manifest: `{outputs.get('manifest', 'UNKNOWN')}`",
        f"- Build report: `{outputs.get('build_report', 'UNKNOWN')}`",
        "",
        "## Source State",
        "",
        f"- IAS status: `{status}`",
        f"- Draft override used: `{draft}`",
        f"- Dependency files loaded: `{dependency_count}`",
        "",
        "## Preflight Validation",
        "",
        f"- Checks passed: `{len(checks)}`",
        f"- Production authorized: `{production}`",
        *[f"- PASS — {check}" for check in checks],
        "",
        "## Warnings",
        "",
        *([f"- {warning}" for warning in report_warnings] if report_warnings else ["- None."]),
        "",
        "## Visual Reference Enforcement",
        "",
        f"- Declared references: `{len(references)}`",
        *(reference_lines if reference_lines else ["- No references declared."]),
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
    return "\n".join(lines)
