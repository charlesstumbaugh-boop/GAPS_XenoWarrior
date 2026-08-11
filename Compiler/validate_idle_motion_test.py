#!/usr/bin/env python3
from pathlib import Path
import yaml

ASSET_ID="CHR-GRUNT-001"

def main():
    repo=Path.cwd().resolve()
    d=repo/"Production"/ASSET_ID/"05_AnimationTests"/"Idle_v001"
    manifest=d/"IdleTestManifest.yaml"
    strip=d/"IdleTestStrip.png"

    errors=[]
    if not manifest.is_file():
        errors.append(f"missing: {manifest}")
    if not strip.is_file():
        errors.append(f"missing: {strip}")

    if manifest.is_file():
        data=yaml.safe_load(manifest.read_text(encoding="utf-8"))
        frames=data.get("frames",[]) if isinstance(data,dict) else []
        if len(frames)!=6:
            errors.append(f"expected 6 frames, found {len(frames)}")
        for rec in frames:
            p=repo/Path(rec.get("file",""))
            if not p.is_file():
                errors.append(f"missing frame: {p}")
        if data.get("metadata",{}).get("approved_art_modified") is not False:
            errors.append("approved_art_modified must be false")
        if data.get("metadata",{}).get("animation_proven") is not False:
            errors.append("animation_proven must remain false before visual review")

    if errors:
        print("IDLE MOTION TEST VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2

    print("IDLE MOTION TEST VALIDATION: PASS")
    print("Frames: 6")
    print("Approved art modified: NO")
    print("Animation proven: NOT YET — visual review required")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
