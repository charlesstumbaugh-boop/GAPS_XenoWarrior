# GAPS Animation Studio v0.5.0 — Transform Core

## Why v0.4 still orbited

The v0.4 patch fixed the requested pivot coordinate, but the Studio still stored
animation as:

- PNG rotation around the image's own local center;
- followed by x/y compensation.

That is not the same transform as rotating the actual layer around an elbow.
The visual result can orbit around the marker even when the marker itself is
correct.

## v0.5 architectural fix

Every calibrated body part is now first rendered into its own full
`1024 x 1024` transparent layer in the exact calibrated A-pose.

Animation is stored as global operations on that layer:

```yaml
- type: rotate
  degrees: -10
  pivot_x: 184
  pivot_y: 248
```

Pillow then rotates the **entire layer around that exact global coordinate**.

There is no image-center rotation and no positional compensation.

The same operation is sent to every descendant. Therefore:

```text
LowerArm_L rotates about elbow
  └─ Hand_L receives the exact same rotation about the same elbow
```

The elbow is mathematically invariant.

## Immediate test

Use only two frames.

1. Neutral.
2. Duplicate neutral.
3. Select `LowerArm_L`.
4. Q or E approximately 10 times.

Pass:
- elbow remains fixed at cyan pivot;
- lower arm swings around elbow;
- hand stays attached and follows;
- upper arm remains still.

Only after this passes should a wave be authored.
