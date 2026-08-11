# GAPS Animation Engine — Idle Validation v001

- Engine version: 0.1.0
- Frames: 6
- Approved art modified: **NO**
- Motion mode: **translation only**
- Calibrated baseline pixel-exact match: **True**
- Strip: `Production\CHR-GRUNT-001\05_AnimationTests\EngineIdle_v001\EngineIdleTestStrip.png`
- Onion skin: `Production\CHR-GRUNT-001\05_AnimationTests\EngineIdle_v001\EngineIdleOnionSkin.png`

## Purpose

This test fixes the previous animation-builder regression where calibrated
rotation/scale (especially the hands) was not faithfully reconstructed.

Frame 000 is rebuilt from the saved calibrated manifest before any motion.
The engine then moves the entire upper-body group vertically, preserving all
saved part rotations and scales.

No rotational joint animation is attempted in v001. That is intentionally
deferred until the calibrated baseline is proven.
