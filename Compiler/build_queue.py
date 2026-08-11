#!/usr/bin/env python3
"""
GAPS Production Queue Manager
Version 0.1.0

Purpose:
- Discover missing production parts from the repository.
- Build and persist a queue.
- Show current/remaining work.
- Create the next handoff automatically through gaps.py.
- Keep ProjectStatus synchronized.

The repository remains the source of truth.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import yaml

VERSION = "0.1.0"

DEFAULT_PARTS = [
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
    root = Path.cwd().resolve()
    required = ["Production", "Management", "Intermediate", "Compiler"]
    missing = [x for x in required if not (root / x).exists()]
    if missing:
        raise RuntimeError("Run from repository root. Missing: " + ", ".join(missing))
    return root

def project_status(root: Path) -> dict:
    p = root / "Management" / "ProjectStatus.yaml"
    if not p.is_file():
        raise RuntimeError(f"Missing {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("ProjectStatus.yaml must contain a mapping.")
    return data

def queue_path(root: Path) -> Path:
    return root / "Management" / "ProductionQueue.yaml"

def scan_asset(root: Path, asset_id: str) -> dict:
    parts_dir = root / "Production" / asset_id / "03_Parts"
    completed = []
    missing = []
    for part in DEFAULT_PARTS:
        if (parts_dir / f"{part}.png").is_file():
            completed.append(part)
        else:
            missing.append(part)
    return {
        "asset_id": asset_id,
        "parts_required": len(DEFAULT_PARTS),
        "completed": completed,
        "missing": missing,
        "percent_complete": round(len(completed) / len(DEFAULT_PARTS) * 100, 1),
    }

def discover(root: Path) -> dict:
    status = project_status(root)
    active = status.get("active_asset", {})
    asset_id = active.get("asset_id")
    if not asset_id:
        raise RuntimeError("No active asset in ProjectStatus.yaml")

    state = scan_asset(root, asset_id)
    queue = [
        {
            "asset_id": asset_id,
            "stage": "parts_manufacturing",
            "part": part,
            "destination": f"Production/{asset_id}/03_Parts/{part}.png",
            "status": "READY" if i == 0 else "PENDING",
        }
        for i, part in enumerate(state["missing"])
    ]

    data = {
        "metadata": {
            "system": "GAPS_XenoWarrior",
            "document": "ProductionQueue",
            "version": "1.0.0",
            "status": "ACTIVE",
        },
        "active_asset": asset_id,
        "summary": {
            "parts_required": state["parts_required"],
            "parts_complete": len(state["completed"]),
            "parts_missing": len(state["missing"]),
            "percent_complete": state["percent_complete"],
        },
        "completed_parts": state["completed"],
        "queue": queue,
    }
    queue_path(root).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return data

def load_or_discover(root: Path) -> dict:
    return discover(root)

def show(data: dict):
    q = data.get("queue", [])
    s = data.get("summary", {})
    print("=" * 68)
    print(" GAPS_XenoWarrior — Production Queue")
    print("=" * 68)
    print(f"Tool Version    : {VERSION}")
    print(f"Active Asset    : {data.get('active_asset')}")
    print(f"Parts Complete  : {s.get('parts_complete')}/{s.get('parts_required')}")
    print(f"Completion      : {s.get('percent_complete')}%")
    print(f"Remaining Queue : {s.get('parts_missing')}")
    print()
    if not q:
        print("QUEUE COMPLETE")
        print("No missing production parts.")
    else:
        print("QUEUE")
        for i, item in enumerate(q, start=1):
            marker = "NEXT" if i == 1 else "    "
            print(f"{i:02d}. [{marker}] {item['part']}")
    print("=" * 68)

def run_gaps(root: Path, flag: str) -> int:
    cmd = [sys.executable, str(root / "gaps.py"), flag]
    return subprocess.run(cmd, cwd=root, check=False).returncode

def create_next_handoff(root: Path) -> int:
    data = discover(root)
    q = data.get("queue", [])
    if not q:
        print("QUEUE COMPLETE: no handoff required.")
        return 0

    expected = q[0]["part"]
    print(f"NEXT QUEUED PART: {expected}")
    print()
    rc = run_gaps(root, "--sync")
    if rc >= 2:
        print("QUEUE ERROR: gaps.py --sync failed.")
        return rc

    rc = run_gaps(root, "--handoff")
    if rc >= 2:
        print("QUEUE ERROR: gaps.py --handoff failed.")
        return rc

    print()
    print("QUEUE HANDOFF: PASS")
    print(f"Part: {expected}")
    print(f"Destination: {q[0]['destination']}")
    return 0

def sync_queue(root: Path) -> int:
    rc = run_gaps(root, "--sync")
    if rc >= 2:
        return rc
    data = discover(root)
    show(data)
    return 0

def parse_args():
    p = argparse.ArgumentParser(description="GAPS Production Queue Manager")
    p.add_argument("--show", action="store_true", help="Discover and show the current production queue.")
    p.add_argument("--sync", action="store_true", help="Sync gaps.py and rebuild queue.")
    p.add_argument("--handoff-next", action="store_true", help="Create the handoff for the next missing queued part.")
    return p.parse_args()

def main():
    args = parse_args()
    try:
        root = repo_root()
    except Exception as exc:
        print(f"QUEUE ERROR: {exc}")
        return 2

    if args.show:
        show(discover(root))
        return 0
    if args.sync:
        return sync_queue(root)
    if args.handoff_next:
        return create_next_handoff(root)

    show(discover(root))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
