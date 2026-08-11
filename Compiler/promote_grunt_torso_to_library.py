#!/usr/bin/env python3
"""
Promote the approved CHR-GRUNT-001 torso into the reusable Production Library.

Creates/updates:
- Production/Libraries/LibraryRegistry.yaml
- Production/CHR-GRUNT-001/CharacterAssembly.yaml
- Production/CHR-GRUNT-001/03_Parts/Torso.png
- Production/CHR-GRUNT-001/03_Parts/Torso.yaml

Never overwrites ARM_LIGHT_001.png; that file is supplied by this package.
"""

from pathlib import Path
import hashlib, shutil, yaml

ARMOR_ID = "ARM_LIGHT_001"
ARMOR_FILE = "Production/Libraries/Armor/ARM_LIGHT_001.png"
ASSET_ID = "CHR-GRUNT-001"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
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

def main():
    repo = Path.cwd().resolve()
    armor = repo / ARMOR_FILE
    if not armor.is_file():
        print(f"PROMOTION BLOCKED: missing {armor}")
        return 2

    # Registry merge
    registry_path = repo / "Production" / "Libraries" / "LibraryRegistry.yaml"
    registry = load_yaml(registry_path, {
        "metadata":{"system":"GAPS_XenoWarrior","registry":"ProductionLibraries","version":"1.0.0","status":"ACTIVE"},
        "heads":[], "helmets":[], "armor":[], "weapons":[], "materials":[]
    })
    for key in ["heads","helmets","armor","weapons","materials"]:
        registry.setdefault(key, [])

    registry["armor"] = [e for e in registry["armor"] if e.get("id") != ARMOR_ID]
    registry["armor"].append({
        "id": ARMOR_ID,
        "name": "Grunt Light Combat Torso",
        "file": ARMOR_FILE,
        "sha256": sha256(armor),
        "humanoid_base": "HUMANOID_BASE_v001",
        "status": "APPROVED",
        "reusable": True,
        "compatible_variants": ["male","female"]
    })
    save_yaml(registry_path, registry)

    # Character assembly merge
    assembly_path = repo / "Production" / ASSET_ID / "CharacterAssembly.yaml"
    assembly = load_yaml(assembly_path, {
        "metadata":{"asset_id":ASSET_ID,"asset_name":"Grunt Soldier 1","version":"v001","status":"ACTIVE"},
        "inherits":{"animation_base":"HUMANOID_BASE_v001"},
        "default_assembly":{},
        "approved_variants":{},
        "runtime_policy":{}
    })
    assembly.setdefault("default_assembly", {})["armor"] = ARMOR_ID
    assembly["default_assembly"].pop("armor_profile", None)
    save_yaml(assembly_path, assembly)

    # Compatibility/default part for current GAPS queue
    parts = repo / "Production" / ASSET_ID / "03_Parts"
    parts.mkdir(parents=True, exist_ok=True)
    torso = parts / "Torso.png"
    shutil.copy2(armor, torso)
    save_yaml(parts / "Torso.yaml", {
        "metadata":{
            "asset_id":ASSET_ID,
            "part":"Torso",
            "version":"v001",
            "status":"APPROVED",
            "library_reference":ARMOR_ID
        },
        "file":f"Production/{ASSET_ID}/03_Parts/Torso.png",
        "canonical_library_file":ARMOR_FILE,
        "sha256":sha256(torso)
    })

    print("ARMOR LIBRARY PROMOTION: PASS")
    print(f"Canonical armor: {armor}")
    print(f"Registry ID: {ARMOR_ID}")
    print("Grunt assembly updated: YES")
    print("Torso compatibility part installed: YES")
    print("NEXT: python gaps.py --advance")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
