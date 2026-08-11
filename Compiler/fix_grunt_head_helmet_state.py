#!/usr/bin/env python3
"""
Fix CHR-GRUNT-001 Head/Helmet production state.

Reason:
The first generated "Head.png" is actually the armored helmet/head assembly.
For the reusable humanoid rig, Head and Helmet must remain separate.

This script:
1. Renames Head.png -> Helmet.png
2. Rewrites Head.yaml -> Helmet.yaml if present
3. Resets ProjectStatus next part to Head
4. Leaves the Helmet file in place so it will be skipped later once Head is completed
"""

from pathlib import Path
import yaml
import hashlib

ASSET_ID = "CHR-GRUNT-001"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    repo = Path.cwd().resolve()
    parts = repo/"Production"/ASSET_ID/"03_Parts"
    status_path = repo/"Management"/"ProjectStatus.yaml"

    head_png = parts/"Head.png"
    head_yaml = parts/"Head.yaml"
    helmet_png = parts/"Helmet.png"
    helmet_yaml = parts/"Helmet.yaml"

    if not head_png.is_file():
        print(f"FIX BLOCKED: missing {head_png}")
        return 2

    if helmet_png.exists():
        print(f"FIX BLOCKED: {helmet_png} already exists; refusing to overwrite.")
        return 2

    head_png.rename(helmet_png)

    record = {
        "metadata": {
            "asset_id": ASSET_ID,
            "part": "Helmet",
            "artifact_type": "production_part",
            "version": "v001",
            "status": "APPROVED",
            "approved_by": "Project Owner",
            "correction": "Renamed from initial Head production part because the image is the armored helmet/head assembly."
        },
        "file": f"Production/{ASSET_ID}/03_Parts/Helmet.png",
        "sha256": sha256(helmet_png),
        "image": {
            "width": 1024,
            "height": 1024,
            "mode": "RGBA",
            "transparent_background": True
        }
    }
    helmet_yaml.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    if head_yaml.exists():
        head_yaml.unlink()

    if not status_path.is_file():
        print(f"FIX BLOCKED: missing {status_path}")
        return 2

    status = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    asset = status["active_asset"]
    asset["current_stage"] = "parts_manufacturing"
    asset["next_required_part"] = "Head"
    asset["next_output"] = f"Production/{ASSET_ID}/03_Parts/Head.png"

    handoff = status.setdefault("handoff", {})
    handoff["action_type"] = "external_generation"
    handoff["destination"] = asset["next_output"]

    status_path.write_text(yaml.safe_dump(status, sort_keys=False), encoding="utf-8")

    print("HEAD/HELMET STATE FIX: PASS")
    print(f"Preserved approved armored assembly as: {helmet_png}")
    print("ProjectStatus reset to next part: Head")
    print("NEXT: python gaps.py --handoff")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
