#!/usr/bin/env python3
"""
GAPS Production Orchestrator
Version 0.2.0

The repository is the source of truth.

v0.2 changes:
- Scans Production/<ASSET-ID>/03_Parts for actual completion.
- Shows completed / missing parts and completion percentage.
- Automatically resolves the next missing required part.
- --sync reconciles ProjectStatus.yaml with repository contents.
- --handoff synchronizes before creating a handoff.
- --advance is retained for compatibility but now performs repository sync.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

VERSION = "0.2.0"

PARTS = [
    "Head",
    "Helmet",
    "Torso",
    "Pelvis",
    "UpperArm_L",
    "LowerArm_L",
    "Hand_L",
    "UpperArm_R",
    "LowerArm_R",
    "Hand_R",
    "UpperLeg_L",
    "LowerLeg_L",
    "Foot_L",
    "UpperLeg_R",
    "LowerLeg_R",
    "Foot_R",
]


def repo_root() -> Path:
    root = Path(__file__).resolve().parent
    required = ["Compiler", "Management", "Reference", "Production", "Intermediate"]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise RuntimeError("Missing repository folders: " + ", ".join(missing))
    return root


def status_path(root: Path) -> Path:
    return root / "Management" / "ProjectStatus.yaml"


def load_status(root: Path) -> dict:
    path = status_path(root)
    if not path.is_file():
        raise RuntimeError(f"Missing ProjectStatus.yaml: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("ProjectStatus.yaml must contain a YAML mapping.")
    return data


def save_status(root: Path, data: dict) -> None:
    status_path(root).write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )


def parts_state(root: Path, asset_id: str) -> tuple[list[str], list[str]]:
    parts_dir = root / "Production" / asset_id / "03_Parts"
    completed = []
    missing = []
    for part in PARTS:
        path = parts_dir / f"{part}.png"
        if path.is_file():
            completed.append(part)
        else:
            missing.append(part)
    return completed, missing


def completion_bar(done: int, total: int, width: int = 20) -> str:
    filled = round(width * done / total) if total else 0
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def synchronize(root: Path, data: dict, write: bool = True) -> dict:
    asset = data.setdefault("active_asset", {})
    asset_id = asset.get("asset_id")
    if not asset_id:
        raise RuntimeError("ProjectStatus active_asset.asset_id is missing.")

    completed_parts, missing_parts = parts_state(root, asset_id)
    next_part = missing_parts[0] if missing_parts else None

    asset["parts_completed"] = len(completed_parts)
    asset["parts_required"] = len(PARTS)
    asset["completion_percent"] = round((len(completed_parts) / len(PARTS)) * 100, 1)
    asset["next_required_part"] = next_part

    if next_part:
        asset["current_stage"] = "parts_manufacturing"
        asset["next_output"] = f"Production/{asset_id}/03_Parts/{next_part}.png"
        data.setdefault("handoff", {})["action_type"] = "external_generation"
        data["handoff"]["destination"] = asset["next_output"]
    else:
        asset["current_stage"] = "rig_assembly"
        asset["next_output"] = None

        pending = data.setdefault("pending", [])
        completed = data.setdefault("completed", [])
        if "parts" in pending:
            pending.remove("parts")
        if "parts" not in completed:
            completed.append("parts")

        data["handoff"] = {
            "action_type": "local_tool",
            "next_command": f"python Compiler/build_rig.py --asset-id {asset_id} --build",
        }

    if write:
        save_status(root, data)

    return data


def show_status(root: Path, data: dict) -> None:
    data = synchronize(root, data, write=False)
    project = data.get("project", {})
    asset = data.get("active_asset", {})
    handoff = data.get("handoff", {})

    completed_parts, missing_parts = parts_state(root, asset["asset_id"])
    done = len(completed_parts)
    total = len(PARTS)

    print("=" * 68)
    print(" GAPS_XenoWarrior — Production Dashboard")
    print("=" * 68)
    print(f"Tool Version : {VERSION}")
    print(f"Phase        : {project.get('current_phase', 'UNKNOWN')}")
    print(f"Sprint       : {project.get('current_sprint', 'UNKNOWN')}")
    print(f"Asset        : {asset.get('asset_id')} - {asset.get('asset_name')}")
    print(f"Stage        : {asset.get('current_stage')}")
    print()
    print("PART COMPLETION")
    print(f"  {completion_bar(done, total)} {done}/{total} ({asset.get('completion_percent')}%)")
    print()

    if completed_parts:
        print("COMPLETED PARTS")
        for name in completed_parts:
            print(f"  [PASS] {name}")
        print()

    print("MISSING PARTS")
    if missing_parts:
        for idx, name in enumerate(missing_parts):
            marker = "NEXT" if idx == 0 else "    "
            print(f"  [{marker}] {name}")
    else:
        print("  None — parts manufacturing complete.")
    print()

    print("NEXT REQUIRED ACTION")
    if asset.get("next_required_part"):
        print(f"  Part        : {asset['next_required_part']}")
        print(f"  Destination : {asset['next_output']}")
        print(f"  Action      : {handoff.get('action_type')}")
    else:
        print(f"  Stage       : {asset.get('current_stage')}")
        print(f"  Command     : {handoff.get('next_command', 'NONE')}")
    print("=" * 68)


def run_validators(root: Path) -> int:
    scripts = [
        "Compiler/validate_yaml.py",
        "Compiler/validate_repository.py",
        "Compiler/validate_humanoid_base.py",
        "Compiler/validate_grunt_animation_profile.py",
        "Compiler/validate_production_library.py",
    ]
    blocking = False
    for rel in scripts:
        script = root / rel
        if not script.is_file():
            print(f"SKIP: {rel}")
            continue
        print(f"\nRUN: {rel}")
        code = subprocess.run([sys.executable, str(script)], cwd=root, check=False).returncode
        # Existing validators may return 1 for PASS WITH WARNINGS.
        if code >= 2:
            blocking = True

    print()
    print("GAPS VALIDATION:", "FAIL" if blocking else "PASS / PASS WITH WARNINGS")
    return 2 if blocking else 0


def create_handoff(root: Path, data: dict) -> int:
    data = synchronize(root, data, write=True)
    asset = data["active_asset"]
    handoff = data.get("handoff", {})

    part = asset.get("next_required_part")
    if not part:
        print("HANDOFF NOT REQUIRED")
        print("All required production parts exist.")
        print(f"Next stage: {asset.get('current_stage')}")
        return 0

    folder = (
        root
        / "Intermediate"
        / "Handoffs"
        / asset["asset_id"]
        / f"{part}_v001"
    )
    folder.mkdir(parents=True, exist_ok=True)

    # Remove stale request/contract only; preserve other handoff contents.
    for name in ["Request.md", "OutputContract.yaml"]:
        target = folder / name
        if target.exists():
            target.unlink()

    copied = []
    missing_inputs = []

    for rel in handoff.get("required_inputs", []):
        source = root / Path(rel)
        if source.is_file():
            target = folder / source.name
            shutil.copy2(source, target)
            copied.append(target.name)
        else:
            missing_inputs.append(rel)

    request = f"""# GAPS External Generation Handoff

Asset: {asset['asset_id']}
Asset Name: {asset.get('asset_name')}
Part: {part}
Stage: {asset.get('current_stage')}
Output: {asset.get('next_output')}

## Task

Generate exactly one production PNG for `{part}`.

## Requirements

- preserve the approved character identity;
- match the approved Animation Master;
- isolate only the requested production part;
- 1024 x 1024 RGBA;
- true alpha transparency;
- no checkerboard;
- no text or labels;
- no UI;
- no floor or scenery;
- no cast shadow;
- full requested part visible.

## Repository Destination

`{asset.get('next_output')}`
"""
    (folder / "Request.md").write_text(request, encoding="utf-8")

    contract = {
        "asset_id": asset["asset_id"],
        "asset_name": asset.get("asset_name"),
        "part": part,
        "artifact_type": "production_part",
        "format": "PNG",
        "color_mode": "RGBA",
        "width": 1024,
        "height": 1024,
        "transparent_background": True,
        "destination": asset.get("next_output"),
        "approval_required": True,
    }
    (folder / "OutputContract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False),
        encoding="utf-8",
    )

    print(f"HANDOFF CREATED: {folder}")
    if copied:
        print("Inputs copied:")
        for name in copied:
            print(f"  - {name}")

    if missing_inputs:
        print("WARNING missing inputs:")
        for rel in missing_inputs:
            print(f"  - {rel}")
        return 1

    return 0


def sync_command(root: Path, data: dict) -> int:
    before = data.get("active_asset", {}).get("next_required_part")
    data = synchronize(root, data, write=True)
    after = data["active_asset"].get("next_required_part")

    print("PROJECT STATUS SYNCHRONIZED")
    print(f"Parts complete: {data['active_asset']['parts_completed']}/{data['active_asset']['parts_required']}")
    print(f"Completion: {data['active_asset']['completion_percent']}%")
    print(f"Next: {after}")
    if before != after:
        print(f"Changed from: {before}")
    return 0


def parse_args():
    p = argparse.ArgumentParser(description="GAPS Production Orchestrator")
    p.add_argument("--status", action="store_true", help="Show live repository completion.")
    p.add_argument("--handoff", action="store_true", help="Create the next required handoff.")
    p.add_argument("--validate", action="store_true", help="Run GAPS validators.")
    p.add_argument("--sync", action="store_true", help="Reconcile ProjectStatus with repository files.")
    p.add_argument("--advance", action="store_true", help="Compatibility alias for --sync.")
    return p.parse_args()


def interactive(root: Path, data: dict) -> int:
    while True:
        show_status(root, data)
        print()
        print("[1] Create handoff  [2] Validate  [3] Sync repository  [Q] Quit")
        choice = input("Select: ").strip().lower()

        if choice == "1":
            create_handoff(root, data)
            data = load_status(root)
        elif choice == "2":
            run_validators(root)
        elif choice == "3":
            sync_command(root, data)
            data = load_status(root)
        elif choice in {"q", "quit", "exit"}:
            return 0
        else:
            print("Unknown selection.")


def main() -> int:
    args = parse_args()
    try:
        root = repo_root()
        data = load_status(root)
    except Exception as exc:
        print(f"GAPS ERROR: {exc}")
        return 2

    if args.status:
        show_status(root, data)
        return 0
    if args.handoff:
        return create_handoff(root, data)
    if args.validate:
        return run_validators(root)
    if args.sync or args.advance:
        return sync_command(root, data)

    return interactive(root, data)


if __name__ == "__main__":
    raise SystemExit(main())
