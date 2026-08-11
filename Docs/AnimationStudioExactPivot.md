# GAPS Animation Studio v0.4.0 — Exact Pivot Rotation

## What was wrong in v0.3

The Studio correctly let you place and save the elbow marker, but the transform
math still reconstructed the rotated PNG around its image center and then tried
to compensate by moving the image.

Your test proved that was not reliable enough.

## v0.4 fix

Rotation is now solved explicitly around the exact user-calibrated global
joint position.

For `LowerArm_L`:

1. The current rendered lower-arm layer is placed on a temporary transparent
   canvas.
2. The saved elbow pivot is placed at the mathematical center of that canvas.
3. The whole layer is rotated around that center.
4. The new layer position is resolved back into the 1024x1024 character space.
5. `Hand_L` receives the same rigid transform.
6. The wrist pivot also travels with the lower-arm chain.

The elbow itself remains fixed.

## Test only one joint first

Do not re-author the wave yet.

1. Open the Studio.
2. Confirm your saved `AnimationPivots.yaml` loads.
3. Keep **Hierarchy** enabled.
4. Duplicate neutral Frame 1.
5. Select `LowerArm_L`.
6. Press Q/E until it rotates about 10 degrees.

Pass condition:
- the visible elbow does not move;
- the lower arm swings around that elbow;
- the hand remains attached;
- the wrist pivot moves with the hand.

If this passes, repeat for the opposite elbow and then shoulder/wrist.
