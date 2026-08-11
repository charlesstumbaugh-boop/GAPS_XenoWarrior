#!/usr/bin/env python3
from pathlib import Path
import yaml, hashlib

LIB_ID = "PEL_LIGHT_001"
LIB_FILE = "Production/Libraries/Armor/PEL_LIGHT_001.png"
ASSET_ID = "CHR-GRUNT-001"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
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
    lib = repo / LIB_FILE
    part = repo / "Production" / ASSET_ID / "03_Parts" / "Pelvis.png"

    if not lib.is_file():
        print(f"PELVIS PROMOTION BLOCKED: missing {lib}")
        return 2
    if not part.is_file():
        print(f"PELVIS PROMOTION BLOCKED: missing {part}")
        return 2

    registry_path = repo / "Production" / "Libraries" / "LibraryRegistry.yaml"
    registry = load_yaml(registry_path, {
        "metadata":{"system":"GAPS_XenoWarrior","registry":"ProductionLibraries","version":"1.0.0","status":"ACTIVE"},
        "heads":[], "helmets":[], "armor":[], "weapons":[], "materials":[]
    })
    for key in ["heads","helmets","armor","weapons","materials"]:
        registry.setdefault(key, [])

    registry["armor"] = [e for e in registry["armor"] if e.get("id") != LIB_ID]
    registry["armor"].append({
        "id": LIB_ID,
        "name": "Light Humanoid Pelvis Armor",
        "file": LIB_FILE,
        "sha256": sha256(lib),
        "humanoid_base": "HUMANOID_BASE_v001",
        "status": "APPROVED",
        "reusable": True,
        "compatible_variants": ["male","female"]
    })
    save_yaml(registry_path, registry)

    assembly_path = repo / "Production" / ASSET_ID / "CharacterAssembly.yaml"
    assembly = load_yaml(assembly_path, {
        "metadata":{"asset_id":ASSET_ID,"asset_name":"Grunt Soldier 1","version":"v001","status":"ACTIVE"},
        "inherits":{"animation_base":"HUMANOID_BASE_v001"},
        "default_assembly":{},
        "approved_variants":{},
        "runtime_policy":{}
    })
    assembly.setdefault("default_assembly", {})["pelvis"] = LIB_ID
    save_yaml(assembly_path, assembly)

    print("PELVIS LIBRARY PROMOTION: PASS")
    print(f"Canonical pelvis: {lib}")
    print(f"Registry ID: {LIB_ID}")
    print("Grunt assembly updated: YES")
    print("Pelvis compatibility part installed: YES")
    print("NEXT: python gaps.py --sync")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
