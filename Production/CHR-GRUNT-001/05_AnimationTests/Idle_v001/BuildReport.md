# CHR-GRUNT-001 Idle Motion Test v001

- Tool: GAPS First Idle Motion Test 0.1.0
- Status: **REVIEW REQUIRED**
- Frames: 6
- Approved art modified: **NO**
- Calibrated rig source: `03_Rig/Calibrated/CalibratedRigManifest.yaml`
- Preview strip: `Production\CHR-GRUNT-001\05_AnimationTests\Idle_v001\IdleTestStrip.png`

## Purpose

This is not a final idle animation. It is a controlled rig-behavior test.

Motion is intentionally tiny:
- torso vertical motion: approximately 1–3 px;
- head/helmet vertical motion: approximately 1–3 px;
- head rotation: less than 1 degree;
- arm sway: approximately 1 degree.

## Review Gate

Review all six frames for:
- shoulder/epaulette behavior;
- elbow continuity;
- wrist/hand continuity;
- head/helmet relationship;
- torso/pelvis continuity;
- knees;
- ankles.

If the rig remains cohesive through all frames, the next step is to promote the
test to `animation_proven: true` and begin the first real idle animation.
