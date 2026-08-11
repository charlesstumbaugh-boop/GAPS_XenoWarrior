# GAPS Animation Engine v001

This is the first reusable animation engine layer for the calibrated rig.

## Critical rule

Animation never starts from raw source art.

It always starts from:

```text
CalibratedRigManifest.yaml
```

The engine reconstructs each part using its saved:

- source file;
- base scale;
- Calibration Studio scale;
- Calibration Studio rotation;
- resolved canvas position;
- z-order.

Only then is animation motion added.

This specifically fixes the previous idle-test bug where the hands lost their
saved rotation/scale.

## First gate

v001 deliberately uses **translation-only** idle motion.

Why: before implementing rotating parent/child joint chains, GAPS must prove
that the saved calibrated pose survives the animation engine exactly.

Frame 000 is compared pixel-for-pixel with:

```text
03_Rig/Calibrated/CalibratedRigPreview.png
```

If it differs, the build fails.

## Run

```cmd
python Compiler\build_animation_engine_idle_test.py
python Compiler\validate_animation_engine.py
```

Review:

```text
Production\CHR-GRUNT-001\05_AnimationTests\EngineIdle_v001\
  EngineIdleTestStrip.png
  EngineIdleOnionSkin.png
  frame_000.png ... frame_005.png
```

After this passes visual review, the next engine increment is hierarchical
rotation about shoulder/elbow/wrist/hip/knee/ankle pivots.
