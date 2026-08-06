"""Generate deterministic GAPS GenerationManifest.yaml data.

This module returns a plain Python dictionary. It does not write files and does
not resolve repository paths. The compiler orchestrator owns those operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


GENERATOR_VERSION = "1.0.0"
COMPILER_VERSION = "0.4.0"


class ManifestGeneratorError(RuntimeError):
    """Raised when the manifest context is incomplete or invalid."""


def _require_mapping(context: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = context.get(key)
    if not isinstance(value, Mapping):
        raise ManifestGeneratorError(f"Missing or invalid manifest context mapping: {key}")
    return value


def _require_list(context: Mapping[str, Any], key: str) -> list[Any]:
    value = context.get(key)
    if not isinstance(value, list):
        raise ManifestGeneratorError(f"Missing or invalid manifest context list: {key}")
    return value


def _require_text(context: Mapping[str, Any], key: str) -> str:
    value = context.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestGeneratorError(f"Missing or invalid manifest context text: {key}")
    return value.strip()


def generate(context: Mapping[str, Any]) -> dict[str, Any]:
    """Build and return GenerationManifest.yaml data without writing a file."""
    output = _require_mapping(context, "output")
    validation = _require_mapping(context, "validation")
    sources = _require_list(context, "sources")
    references = _require_list(context, "reference_images")

    prompt_file = _require_text(output, "prompt_file")
    prompt_sha256 = _require_text(output, "prompt_sha256")

    checks = validation.get("checks")
    warnings = validation.get("warnings")
    if not isinstance(checks, list) or not all(isinstance(item, str) for item in checks):
        raise ManifestGeneratorError("validation.checks must be a list of strings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        raise ManifestGeneratorError("validation.warnings must be a list of strings")

    draft_override_used = context.get("draft_override_used")
    production_authorized = context.get("production_authorized")
    if not isinstance(draft_override_used, bool):
        raise ManifestGeneratorError("draft_override_used must be boolean")
    if not isinstance(production_authorized, bool):
        raise ManifestGeneratorError("production_authorized must be boolean")

    return {
        "metadata": {
            "type": "generation_manifest",
            "compiler": "GAPS build_prompt.py",
            "compiler_version": COMPILER_VERSION,
            "manifest_generator_version": GENERATOR_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "draft_override_used": draft_override_used,
            "validation_passed": True,
            "validation_check_count": len(checks),
            "production_authorized": production_authorized,
        },
        "output": {
            "prompt_file": prompt_file,
            "prompt_sha256": prompt_sha256,
        },
        "validation": {
            "checks": checks,
            "warnings": warnings,
        },
        "sources": sources,
        "reference_images": references,
    }
