#!/usr/bin/env python3
"""
GAPS Production Pack Builder
Version 0.1.0

Purpose:
Turn one approved PNG into a standardized reusable Production Library asset and
a compatibility copy for a character's 03_Parts folder.

The repository remains the source of truth.

Example:
    python Compiler/build_production_pack.py ^
        --asset ARM_UPPER_L_001 ^
        --category Armor ^
        --character CHR-GRUNT-001 ^
        --part UpperArm_L ^
        --image "C:\path\to\approved.png"

Outputs:
- Production/Libraries/<Category>/<asset>.png
- Production/Libraries/<Category>/<asset>.yaml
- Production/<character>/03_Parts/<part>.png
- Production/<character>/03_Parts/<part>.yaml
- updates Production/Libraries/LibraryRegistry.yaml
- updates Production/<character>/CharacterAssembly.yaml
- Management/ProductionPackReports/<asset>_BuildReport.md
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image

TOOL_VERSION = "0.1.0"

CATEGORY_MAP = {
    "heads": "Heads",
    "head": "Heads",
    "helmets": "Helmets",
    "helmet": "Helmets",
    "armor": "Armor",
    "weapons": "Weapons",
    "weapon": "Weapons",
    "materials": "Materials",
    "material": "Materials",
    "props": "Props",
    "prop": "Props",
    "effects": "Effects",
    "effect": "Effects",
}

REGISTRY_KEYS = {
    "Heads": "heads",
    "Helmets": "helmets",
    "Armor": "armor",
    "Weapons": "weapons",
    "Materials": "materials",
    "Props": "props",
    "Effects": "effects",
}

ASSEMBLY_SLOT_MAP = {
    "Head": "head",
    "Helmet": "helmet",
    "Torso": "armor",
    "Pelvis": "pelvis",
    "UpperArm_L": "upper_arm_l",
    "LowerArm_L": "lower_arm_l",
    "Hand_L": "hand_l",
    "UpperArm_R": "upper_arm_r",
    "LowerArm_R": "lower_arm_r",
    "Hand_R": "hand_r",
    "UpperLeg_L": "upper_leg_l",
    "LowerLeg_L": "lower_leg_l",
    "Foot_L": "foot_l",
    "UpperLeg_R": "upper_leg_r",
    "LowerLeg_R": "lower_leg_r",
    "Foot_R": "foot_r",
}

def parse_args():
    p = argparse.ArgumentParser(description="Build a standardized GAPS production asset package.")
    p.add_argument("--asset", required=True, help="Reusable library asset ID, e.g. ARM_UPPER_L_001")
    p.add_argument("--category", required=True, help="Heads, Helmets, Armor, Weapons, Materials, Props, Effects")
    p.add_argument("--character", required=True, help="Character asset ID, e.g. CHR-GRUNT-001")
    p.add_argument("--part", required=True, help="Compatibility part name, e.g. UpperArm_L")
    p.add_argument("--image", required=True, type=Path, help="Approved source PNG")
    p.add_argument("--name", default=None, help="Human-readable asset name")
    p.add_argument("--variant", default="default", help="Variant label")
    p.add_argument("--no-assembly-update", action="store_true", help="Do not update CharacterAssembly.yaml")
    return p.parse_args()

def repo_root() -> Path:
    root = Path.cwd().resolve()
    required = ["Production", "Management", "Compiler"]
    missing = [x for x in required if not (root / x).exists()]
    if missing:
        raise RuntimeError("Run from the GAPS repository root. Missing: " + ", ".join(missing))
    return root

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def load_yaml(path: Path, default):
    if not path.is_file():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else default

def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def canonical_category(raw: str) -> str:
    key = raw.strip().lower()
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    raise RuntimeError(f"Unsupported category: {raw}")

def validate_source_png(path: Path):
    if not path.is_file():
        raise RuntimeError(f"Image not found: {path}")
    if path.suffix.lower() != ".png":
        raise RuntimeError("Production Pack Builder currently accepts PNG only.")

    im = Image.open(path)
    if im.size != (1024, 1024):
        raise RuntimeError(f"Expected 1024x1024 PNG; found {im.size[0]}x{im.size[1]}.")
    if im.mode != "RGBA":
        raise RuntimeError(f"Expected RGBA PNG; found {im.mode}.")
    if im.getchannel("A").getbbox() is None:
        raise RuntimeError("PNG alpha channel contains no visible pixels.")

def update_registry(repo: Path, category: str, asset_id: str, library_path: Path, name: str, variant: str):
    registry_path = repo / "Production" / "Libraries" / "LibraryRegistry.yaml"
    registry = load_yaml(registry_path, {
        "metadata": {
            "system": "GAPS_XenoWarrior",
            "registry": "ProductionLibraries",
            "version": "1.0.0",
            "status": "ACTIVE",
        },
        "heads": [],
        "helmets": [],
        "armor": [],
        "weapons": [],
        "materials": [],
        "props": [],
        "effects": [],
    })

    for key in REGISTRY_KEYS.values():
        registry.setdefault(key, [])

    key = REGISTRY_KEYS[category]
    registry[key] = [e for e in registry[key] if e.get("id") != asset_id]
    registry[key].append({
        "id": asset_id,
        "name": name,
        "file": str(library_path.relative_to(repo)).replace("\\", "/"),
        "sha256": sha256(library_path),
        "status": "APPROVED",
        "reusable": True,
        "variant": variant,
    })
    save_yaml(registry_path, registry)
    return registry_path

def update_assembly(repo: Path, character: str, part: str, asset_id: str):
    path = repo / "Production" / character / "CharacterAssembly.yaml"
    assembly = load_yaml(path, {
        "metadata": {
            "asset_id": character,
            "version": "v001",
            "status": "ACTIVE",
        },
        "inherits": {
            "animation_base": "HUMANOID_BASE_v001",
        },
        "default_assembly": {},
        "approved_variants": {},
        "runtime_policy": {},
    })

    slot = ASSEMBLY_SLOT_MAP.get(part, part.lower())
    assembly.setdefault("default_assembly", {})[slot] = asset_id
    save_yaml(path, assembly)
    return path, slot

def write_part_metadata(repo: Path, character: str, part: str, asset_id: str, part_path: Path, library_path: Path):
    meta = {
        "metadata": {
            "asset_id": character,
            "part": part,
            "version": "v001",
            "status": "APPROVED",
            "library_reference": asset_id,
        },
        "file": str(part_path.relative_to(repo)).replace("\\", "/"),
        "canonical_library_file": str(library_path.relative_to(repo)).replace("\\", "/"),
        "sha256": sha256(part_path),
        "image": {
            "width": 1024,
            "height": 1024,
            "mode": "RGBA",
            "transparent_background": True,
        },
    }
    meta_path = part_path.with_suffix(".yaml")
    save_yaml(meta_path, meta)
    return meta_path

def write_library_metadata(repo: Path, category: str, asset_id: str, name: str, image_path: Path, variant: str):
    meta = {
        "metadata": {
            "asset_id": asset_id,
            "asset_name": name,
            "category": category,
            "artifact_type": "production_library_asset",
            "version": "v001",
            "status": "APPROVED",
        },
        "file": str(image_path.relative_to(repo)).replace("\\", "/"),
        "sha256": sha256(image_path),
        "variant": variant,
        "image": {
            "width": 1024,
            "height": 1024,
            "mode": "RGBA",
            "transparent_background": True,
        },
    }
    path = image_path.with_suffix(".yaml")
    save_yaml(path, meta)
    return path

def write_report(repo: Path, args, category: str, library_path: Path, part_path: Path, registry_path: Path, assembly_path: Path | None):
    report_dir = repo / "Management" / "ProductionPackReports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{args.asset}_BuildReport.md"

    assembly_line = str(assembly_path.relative_to(repo)) if assembly_path else "Skipped by --no-assembly-update"

    text = f"""# GAPS Production Pack Build Report

- Tool version: {TOOL_VERSION}
- Library asset: `{args.asset}`
- Category: `{category}`
- Character: `{args.character}`
- Compatibility part: `{args.part}`
- Source image: `{args.image}`
- Library output: `{library_path.relative_to(repo)}`
- Character output: `{part_path.relative_to(repo)}`
- Registry: `{registry_path.relative_to(repo)}`
- Character assembly: `{assembly_line}`
- SHA-256: `{sha256(library_path)}`
- Status: **PASS**
"""
    report.write_text(text, encoding="utf-8")
    return report

def main():
    args = parse_args()

    try:
        repo = repo_root()
        category = canonical_category(args.category)
        source = args.image.expanduser().resolve()
        validate_source_png(source)

        name = args.name or args.asset.replace("_", " ").title()

        library_dir = repo / "Production" / "Libraries" / category
        library_dir.mkdir(parents=True, exist_ok=True)
        library_path = library_dir / f"{args.asset}.png"

        parts_dir = repo / "Production" / args.character / "03_Parts"
        parts_dir.mkdir(parents=True, exist_ok=True)
        part_path = parts_dir / f"{args.part}.png"

        # Refuse silent overwrite unless source is identical.
        for target in [library_path, part_path]:
            if target.exists():
                existing_hash = sha256(target)
                source_hash = sha256(source)
                if existing_hash != source_hash:
                    raise RuntimeError(f"Refusing to overwrite different existing file: {target}")

        shutil.copy2(source, library_path)
        shutil.copy2(source, part_path)

        library_meta = write_library_metadata(
            repo, category, args.asset, name, library_path, args.variant
        )
        part_meta = write_part_metadata(
            repo, args.character, args.part, args.asset, part_path, library_path
        )
        registry_path = update_registry(
            repo, category, args.asset, library_path, name, args.variant
        )

        assembly_path = None
        slot = None
        if not args.no_assembly_update:
            assembly_path, slot = update_assembly(
                repo, args.character, args.part, args.asset
            )

        report = write_report(
            repo, args, category, library_path, part_path, registry_path, assembly_path
        )

        print(f"GAPS Production Pack Builder v{TOOL_VERSION}")
        print("PRODUCTION PACK BUILD: PASS")
        print(f"Library asset : {library_path}")
        print(f"Part copy     : {part_path}")
        print(f"Library YAML  : {library_meta}")
        print(f"Part YAML     : {part_meta}")
        print(f"Registry      : {registry_path}")
        if assembly_path:
            print(f"Assembly      : {assembly_path}")
            print(f"Assembly slot : {slot}")
        print(f"Build report  : {report}")
        print(f"SHA-256       : {sha256(library_path)}")
        print()
        print("NEXT:")
        print("python gaps.py --sync")
        print("python gaps.py --status")
        return 0

    except Exception as exc:
        print(f"PRODUCTION PACK BUILD: FAIL")
        print(exc)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
