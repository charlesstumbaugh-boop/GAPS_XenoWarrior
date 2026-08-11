# GAPS Calibrated Rig Bridge v001

This bridge promotes the layout saved in **GAPS Calibration Studio** into a
repository rig manifest.

It is intentionally narrow:

- no redraw;
- no new image generation;
- no approved PNG overwrite;
- no replacement of `RigSpecification.yaml`;
- no assumption that shoulder animation behavior is already solved.

## Install

Extract into the repository root:

```text
Compiler/build_calibrated_rig.py
Compiler/validate_calibrated_rig.py
Docs/CalibratedRigBridge.md
```

## Build

```cmd
python Compiler\build_calibrated_rig.py
```

Outputs:

```text
Production\CHR-GRUNT-001\03_Rig\Calibrated\
  CalibratedRigManifest.yaml
  CalibratedRigPreview.png
  CalibratedRigPreview_Pivots.png
  BuildReport.md
```

The preview should visually match the layout saved in Calibration Studio.

## Validate

```cmd
python Compiler\validate_calibrated_rig.py
```

This validates that all 16 production parts are represented and that the bridge
did not claim to modify approved artwork.

## Shoulder / Epaulette Note

The current visual calibration found that the shoulder armor reads correctly as
an epaulette-like outer armor layer. The bridge records that observation but
does not restructure the rig yet.

Why: the first animation test should determine whether the shoulder armor needs
different parenting/rotation behavior. We preserve the successful visual layout
first, then make only the behavioral change demonstrated by animation.
