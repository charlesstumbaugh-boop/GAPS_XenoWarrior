"""Generate ReferenceList.md from a compiler-owned context."""

from __future__ import annotations

from typing import Any

GENERATOR_VERSION = "1.0.0"


class ReferenceGeneratorError(RuntimeError):
    """Raised when a reference list cannot be generated safely."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReferenceGeneratorError(f"{label} must be a mapping.")
    return value


def _text(value: Any, fallback: str = "Not specified") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def generate(context: dict[str, Any]) -> str:
    """Build and return ReferenceList.md text without writing a file."""
    context = _mapping(context, "context")
    build = _mapping(context.get("build"), "context.build")
    ias = _mapping(context.get("ias"), "context.ias")
    identity = _mapping(ias.get("identity"), "IAS.identity")
    references = context.get("references", [])
    if not isinstance(references, list):
        raise ReferenceGeneratorError("context.references must be a list.")

    asset_id = _text(identity.get("asset_id"), "UNKNOWN-ASSET")
    asset_name = _text(identity.get("asset_name"), asset_id)
    build_id = _text(_mapping(build.get("metadata"), "Build.metadata").get("build_id"), "UNKNOWN-BUILD")

    lines = [
        "# Reference List",
        "",
        f"- **Generator version:** {GENERATOR_VERSION}",
        f"- **Build ID:** `{build_id}`",
        f"- **Asset ID:** `{asset_id}`",
        f"- **Asset name:** {asset_name}",
        f"- **References evaluated:** {len(references)}",
        "",
        "## Reference Contract",
        "",
        "References influence the build only through their declared roles. A style-only reference may transfer rendering language but may not transfer asset identity, silhouette, equipment, proportions, or component design.",
        "",
    ]

    if not references:
        lines.extend([
            "## References",
            "",
            "No reference images were declared for this build.",
            "",
        ])
        return "\n".join(lines)

    lines.extend(["## References", ""] )
    for index, reference in enumerate(references, start=1):
        if not isinstance(reference, dict):
            raise ReferenceGeneratorError(f"Reference {index} must be a mapping.")
        reference_id = _text(reference.get("reference_id"), f"REFERENCE-{index}")
        relationship = _text(reference.get("relationship"), "unspecified")
        authority = _text(reference.get("authority_level"), "unspecified")
        purpose = _text(reference.get("purpose"))
        file_value = _text(reference.get("file"))
        resolved = reference.get("resolved") is True
        sha256 = _text(reference.get("sha256"), "Not available")

        lines.extend([
            f"### {index}. `{reference_id}`",
            "",
            f"- **File:** `{file_value}`",
            f"- **Resolved:** {'Yes' if resolved else 'No'}",
            f"- **Relationship:** `{relationship}`",
            f"- **Authority level:** `{authority}`",
            f"- **Purpose:** {purpose}",
            f"- **SHA-256:** `{sha256}`",
            "",
        ])

        if relationship == "style_only":
            lines.extend([
                "**Allowed influence**",
                "",
                "- Rendering style",
                "- Palette discipline",
                "- Outline treatment",
                "- Lighting language",
                "- Material finish",
                "- Camera presentation",
                "",
                "**Forbidden identity influence**",
                "",
                "- Silhouette",
                "- Helmet or head geometry",
                "- Armor layout",
                "- Weapon identity",
                "- Body proportions",
                "- Accessory placement",
                "",
            ])
        elif relationship == "identity":
            lines.extend([
                "**Identity authority**",
                "",
                "This reference defines the approved identity of the asset and must not be reinterpreted without explicit review.",
                "",
            ])

    lines.extend([
        "## Review Gate",
        "",
        "Before generation, confirm that every listed file is resolved and that each reference role matches the Build Request.",
        "",
    ])
    return "\n".join(lines)
