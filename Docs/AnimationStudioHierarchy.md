# GAPS Animation Studio v0.2.0 — Hierarchical Pivots

This patch fixes the wave-test blocker.

With **Hierarchy** checked:

- `UpperArm_L/R` rotates around the shoulder pivot and carries the lower arm and hand.
- `LowerArm_L/R` rotates around the elbow pivot and carries the hand.
- `Hand_L/R` rotates around the wrist pivot.
- Upper/lower leg chains follow the same parent-child rule using hip/knee/ankle pivots.

The pivot coordinates come from the existing `03_Rig/RigSpecification.yaml`.
The parent relationships come from the promoted calibrated rig manifest.

## First validation

Create a throwaway animation named `WaveTest_v001`.

1. Keep Frame 1 as neutral.
2. Duplicate Frame 1.
3. Select an UpperArm and use Q/E. LowerArm + Hand should travel with it.
4. Select its LowerArm and use Q/E. It should bend at the elbow and the Hand should follow.
5. Select the Hand and use Q/E. Only the hand should rotate at the wrist.
6. Press Play.

Do not compensate for a hierarchy error by redrawing or manually separating art.
