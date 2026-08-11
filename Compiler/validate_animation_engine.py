#!/usr/bin/env python3
from pathlib import Path
import yaml

ASSET_ID="CHR-GRUNT-001"

def main():
    repo=Path.cwd().resolve()
    d=repo/"Production"/ASSET_ID/"05_AnimationTests"/"EngineIdle_v001"
    m=d/"AnimationEngineIdleTest.yaml"
    required=[
        m,
        d/"EngineIdleTestStrip.png",
        d/"EngineIdleOnionSkin.png",
    ] + [d/f"frame_{i:03d}.png" for i in range(6)]

    errors=[f"missing: {p}" for p in required if not p.is_file()]

    if m.is_file():
        data=yaml.safe_load(m.read_text(encoding="utf-8"))
        if data.get("baseline_validation",{}).get("frame_000_pixel_exact_match") is not True:
            errors.append("calibrated baseline pixel-exact match is not true")
        if data.get("metadata",{}).get("approved_art_modified") is not False:
            errors.append("approved_art_modified must be false")
        if data.get("metadata",{}).get("animation_proven") is not False:
            errors.append("animation_proven must remain false before visual motion review")

    if errors:
        print("ANIMATION ENGINE VALIDATION: FAIL")
        for e in errors:
            print("-",e)
        return 2

    print("ANIMATION ENGINE VALIDATION: PASS")
    print("Calibrated baseline preserved: YES")
    print("Frames: 6")
    print("Approved art modified: NO")
    print("Animation proven: NOT YET — visual motion review required")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
