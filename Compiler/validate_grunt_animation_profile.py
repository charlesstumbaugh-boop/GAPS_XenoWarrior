#!/usr/bin/env python3
from pathlib import Path
import yaml

PROFILE = Path("Animation/Characters/CHR-GRUNT-001/CharacterAnimationProfile.yaml")
SPEC = Path("Production/CHR-GRUNT-001/02_AnimationMaster/AnimationMasterSpecification.yaml")
LAYERS = Path("Production/CHR-GRUNT-001/02_AnimationMaster/LayerManifest.yaml")

REQUIRED_BASE = [
    Path("Animation/Bases/HUMANOID_BASE_v001/Skeleton.yaml"),
    Path("Animation/Bases/HUMANOID_BASE_v001/RigSpecification.yaml"),
    Path("Animation/Bases/HUMANOID_BASE_v001/PivotMap.yaml"),
    Path("Animation/Bases/HUMANOID_BASE_v001/JointLimits.yaml"),
    Path("Animation/Bases/HUMANOID_BASE_v001/LayerOrder.yaml"),
    Path("Animation/Bases/HUMANOID_BASE_v001/AnimationStandards.yaml"),
]

def main():
    repo = Path.cwd()
    errors = []

    for rel in REQUIRED_BASE + [PROFILE, SPEC, LAYERS]:
        if not (repo/rel).is_file():
            errors.append(f"missing: {rel}")

    if errors:
        print("GRUNT ANIMATION PROFILE VALIDATION: FAIL")
        for e in errors: print("-", e)
        return 2

    profile = yaml.safe_load((repo/PROFILE).read_text(encoding="utf-8"))
    spec = yaml.safe_load((repo/SPEC).read_text(encoding="utf-8"))
    layers = yaml.safe_load((repo/LAYERS).read_text(encoding="utf-8"))

    if profile.get("inherits",{}).get("animation_base") != "Animation/Bases/HUMANOID_BASE_v001":
        errors.append("Grunt does not inherit HUMANOID_BASE_v001")

    rules = profile.get("animation_master_rules",{})
    for key in ["arms_clear_of_torso","hands_visible","legs_separated",
                "hidden_joint_geometry_required","joint_overlap_required"]:
        if rules.get(key) is not True:
            errors.append(f"animation master rule must be true: {key}")

    if rules.get("weapon_held") is not False:
        errors.append("weapon_held must be false for Animation Master")

    required_layers = [x["name"] for x in layers.get("layers",[]) if x.get("required")]
    if len(required_layers) < 20:
        errors.append("expected at least 20 required Grunt animation layers")

    if errors:
        print("GRUNT ANIMATION PROFILE VALIDATION: FAIL")
        for e in errors: print("-", e)
        return 2

    print("GRUNT ANIMATION PROFILE VALIDATION: PASS")
    print("Animation base: HUMANOID_BASE_v001")
    print(f"Required Grunt layers: {len(required_layers)}")
    print("Weapon is separate: YES")
    print("Ready for Animation Master production: YES")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
