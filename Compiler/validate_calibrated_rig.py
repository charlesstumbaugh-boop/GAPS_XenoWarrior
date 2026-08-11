#!/usr/bin/env python3
from pathlib import Path
import yaml

ASSET_ID="CHR-GRUNT-001"
EXPECTED=[
    "Head","Helmet","Torso","Pelvis",
    "UpperArm_L","LowerArm_L","Hand_L",
    "UpperArm_R","LowerArm_R","Hand_R",
    "UpperLeg_L","LowerLeg_L","Foot_L",
    "UpperLeg_R","LowerLeg_R","Foot_R",
]

def main():
    repo=Path.cwd().resolve()
    d=repo/"Production"/ASSET_ID/"03_Rig"/"Calibrated"
    manifest=d/"CalibratedRigManifest.yaml"
    preview=d/"CalibratedRigPreview.png"
    pivots=d/"CalibratedRigPreview_Pivots.png"

    errors=[]
    for p in [manifest,preview,pivots]:
        if not p.is_file():
            errors.append(f"missing: {p}")

    if manifest.is_file():
        data=yaml.safe_load(manifest.read_text(encoding="utf-8"))
        parts=data.get("parts",{}) if isinstance(data,dict) else {}
        missing=[n for n in EXPECTED if n not in parts]
        if missing:
            errors.append("manifest missing parts: "+", ".join(missing))
        if data.get("metadata",{}).get("approved_art_modified") is not False:
            errors.append("approved_art_modified must be false")
        if data.get("metadata",{}).get("status")!="VISUAL_CALIBRATION_PROMOTED":
            errors.append("unexpected manifest status")

    if errors:
        print("CALIBRATED RIG VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2

    print("CALIBRATED RIG VALIDATION: PASS")
    print("Parts:",len(EXPECTED))
    print("Approved art modified: NO")
    print("Animation proven: NOT YET — first motion test remains required")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
