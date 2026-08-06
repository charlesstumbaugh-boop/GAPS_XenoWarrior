#!/usr/bin/env python3
"""
GAPS Asset Scaffold Tool
Version 0.1.0
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TOOL_VERSION = "0.1.0"
ASSET_ID_PATTERN = re.compile(r"^[A-Z]+(?:-[A-Z0-9]+)+-[0-9]{3}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new GAPS asset scaffold from reusable templates."
    )
    parser.add_argument("asset_id")
    parser.add_argument("--name", required=True)
    parser.add_argument("--template", choices=["character"], default="character")
    parser.add_argument("--build-type", default="DESIGN_MASTER")
    parser.add_argument("--version", default="v001")
    return parser.parse_args()


def repository_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    if not (root / "Compiler").is_dir():
        raise RuntimeError("Unable to determine repository root.")
    return root


def replace_markers(text: str, asset_id: str, name: str) -> str:
    replacements = {
        "<REQUIRED_ASSET_ID>": asset_id,
        "<REQUIRED_ASSET_ID_UNDERSCORED>": asset_id.replace("-", "_"),
        "<REQUIRED_DISPLAY_NAME>": name,
    }
    for marker, value in replacements.items():
        text = text.replace(marker, value)
    return text


def build_yaml(asset_id: str, name: str) -> str:
    build_id = asset_id.replace("-", "_") + "_DESIGN_MASTER_v001"
    return f"""###############################################################################
# GAPS_XenoWarrior
# Build.yaml
###############################################################################

metadata:
  build_id: {build_id}
  build_type: design_master
  version: "1.0.0"
  status: DRAFT
  requested_by: Project Owner

asset:
  asset_id: {asset_id}
  ias_file: Intermediate/Assets/{asset_id}.yaml

objective: >
  Compile repository-authorized instructions for one canonical full-body
  {name} design-master candidate.

reference_policy:
  identity_reference_ids: []
  style_only_reference_ids:
    - REF_CHR_PLAYER_001_GOLD_MASTER
  copy_style_not_design: true
  asset_identity_must_remain_distinct: true

production_output:
  asset_count: 1
  format: PNG
  color_mode: RGBA
  width: 1024
  height: 1024
  transparent_background: true
  full_body_visible: true
  orientation: forward_facing

output:
  prompt_file: Prompt.md
  manifest_file: GenerationManifest.yaml
  report_file: BuildReport.md

execution:
  production_authorized: false
  allow_draft_testing: true
  handwritten_prompt_allowed: false
  repository_is_source_of_truth: true

notes:
  - Replace all remaining required markers in the IAS before compilation.
  - Run with --allow-draft during initial testing.
"""


def main() -> int:
    args = parse_args()
    asset_id = args.asset_id.strip().upper()
    name = args.name.strip()

    if not ASSET_ID_PATTERN.fullmatch(asset_id):
        print("SCAFFOLD FAILED: Use an ID such as CHR-MEDIC-001.", file=sys.stderr)
        return 2
    if not name:
        print("SCAFFOLD FAILED: --name cannot be blank.", file=sys.stderr)
        return 2

    try:
        root = repository_root()
    except RuntimeError as error:
        print(f"SCAFFOLD FAILED: {error}", file=sys.stderr)
        return 2

    template_path = root / "Templates" / "CharacterAssetTemplate.yaml"
    if not template_path.is_file():
        print(f"SCAFFOLD FAILED: Missing template: {template_path}", file=sys.stderr)
        return 2

    ias_path = root / "Intermediate" / "Assets" / f"{asset_id}.yaml"
    build_dir = root / "Intermediate" / "Builds" / asset_id / args.build_type.upper() / args.version.lower()
    build_path = build_dir / "Build.yaml"

    collisions = [p for p in (ias_path, build_path) if p.exists()]
    if collisions:
        print("SCAFFOLD BLOCKED: Existing files will not be overwritten.")
        for path in collisions:
            print(f"- {path}")
        return 2

    try:
        template_text = template_path.read_text(encoding="utf-8")
        ias_text = replace_markers(template_text, asset_id, name)
        ias_path.parent.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)
        ias_path.write_text(ias_text, encoding="utf-8")
        build_path.write_text(build_yaml(asset_id, name), encoding="utf-8")
    except OSError as error:
        print(f"SCAFFOLD FAILED: {error}", file=sys.stderr)
        return 2

    print(f"GAPS Asset Scaffold Tool v{TOOL_VERSION}")
    print(f"Created IAS: {ias_path}")
    print(f"Created Build request: {build_path}")
    print(f"Remaining required markers: {ias_text.count('<REQUIRED')}")
    print("NEXT ACTION: complete the remaining markers before compiling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
