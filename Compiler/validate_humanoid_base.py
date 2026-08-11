#!/usr/bin/env python3
from pathlib import Path
import yaml

REQUIRED_FILES=["Skeleton.yaml","RigSpecification.yaml","PivotMap.yaml","JointLimits.yaml","LayerOrder.yaml","AnimationStandards.yaml"]
REQUIRED_JOINTS={"pelvis","spine","chest","neck","head","shoulder_L","elbow_L","wrist_L","hand_L","shoulder_R","elbow_R","wrist_R","hand_R","hip_L","knee_L","ankle_L","foot_L","hip_R","knee_R","ankle_R","foot_R"}

def main():
    root=Path.cwd()/"Animation"/"Bases"/"HUMANOID_BASE_v001"
    errors=[]
    for n in REQUIRED_FILES:
        if not (root/n).is_file(): errors.append(f"missing file: {root/n}")
    if errors:
        print("HUMANOID BASE VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2
    sk=yaml.safe_load((root/"Skeleton.yaml").read_text(encoding="utf-8"))
    names={j["name"] for j in sk.get("joints",[])}
    missing=sorted(REQUIRED_JOINTS-names)
    if missing: errors.append("missing required joints: "+", ".join(missing))
    rig=yaml.safe_load((root/"RigSpecification.yaml").read_text(encoding="utf-8"))
    invalid=sorted({p["joint"] for p in rig.get("parts",[])}-names)
    if invalid: errors.append("rig references unknown joints: "+", ".join(invalid))
    if errors:
        print("HUMANOID BASE VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2
    print("HUMANOID BASE VALIDATION: PASS")
    print(f"Required joints: {len(REQUIRED_JOINTS)}")
    print(f"Rig parts: {len(rig.get('parts',[]))}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
