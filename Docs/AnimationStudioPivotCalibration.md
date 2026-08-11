# GAPS Animation Studio v0.3.0 — Visual Pivot Calibration

## Why v0.2 failed

v0.2 used the original global coordinates from `RigSpecification.yaml`.

Those coordinates were created before the character was visually recalibrated
in GAPS Calibration Studio. The artwork moved, but the elbow/shoulder/wrist
coordinates did not. Therefore a lower arm could rotate around a stale point
instead of the visible elbow, and its hand would separate.

## v0.3 rule

Animation joints can now be calibrated visually against the final assembled
character.

### Set a joint

1. Select `LowerArm_L`.
2. Click **Set Selected Pivot**.
3. Click the exact center of the visible left elbow.
4. The cyan pivot marker moves there.
5. Press Q/E.

Expected:
- LowerArm_L rotates around that exact elbow.
- Hand_L follows the forearm.
- The wrist pivot travels with the hand/forearm chain.

Repeat for UpperArm shoulder or Hand wrist only if needed.

### Save the pivot calibration

Click **Save Animation Pivots**.

Writes:

```text
Production/CHR-GRUNT-001/04_Calibration/AnimationPivots.yaml
```

The studio loads these values on future sessions.

## First validation

Do not create a full wave yet.

Use a duplicate neutral frame and test only:

```text
LowerArm_L: ±10 degrees at elbow
```

If the forearm rotates at the visible elbow and the hand stays connected, the
pivot/hierarchy gate passes.

Approved PNGs are not modified.
