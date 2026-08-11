# Rig Masks

Each mask is a 1024×1024 image aligned exactly to the Gold Master.

- Black/transparent = remove.
- White/opaque = keep.
- Gray = partial alpha/feathered overlap.

Run:

```cmd
python Compiler\build_rig.py --asset-id CHR-GRUNT-001 --prepare
```

Then open the Gold Master and masks in Krita (or Photopea/GIMP) and paint the
visible pixels for each named part.

Important: the current front-view Gold Master contains occlusions. For large
joint rotations, hidden pixels behind the rifle/arms/torso do not exist in the
source and cannot be recovered deterministically. Idle animation can use small
rotations; larger motion requires model-sheet/rig-source art.
