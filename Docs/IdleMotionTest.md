# GAPS First Idle Motion Test v001

This is the first animation-behavior gate for the calibrated Grunt rig.

It deliberately avoids a full animation.

The test creates six frames with tiny motion so visual failures are easy to spot.

## Motion

The test uses only small deltas:

- torso rise/fall of roughly 1–3 pixels;
- head/helmet rise/fall of roughly 1–3 pixels;
- head tilt under 1 degree;
- arm sway around 1 degree.

The legs remain effectively planted.

## Build

```cmd
python Compiler\build_idle_motion_test.py
```

## Validate structure

```cmd
python Compiler\validate_idle_motion_test.py
```

## Review

Open:

```text
Production\CHR-GRUNT-001\05_AnimationTests\Idle_v001\IdleTestStrip.png
```

Also inspect individual:

```text
frame_000.png
frame_001.png
...
frame_005.png
```

The rig is not declared animation-proven until visual review passes.

## What to inspect

- shoulder / epaulette behavior;
- elbow continuity;
- wrist / hand continuity;
- head / helmet relationship;
- torso / pelvis continuity;
- knees;
- ankles.

No approved source art is modified.
