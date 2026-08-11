# GAPS Production Pack Builder

The builder replaces the custom per-part promotion scripts used during the pilot
Grunt production run.

## Standard workflow

1. Approve a 1024×1024 RGBA PNG.
2. Save/download it somewhere accessible on the local machine.
3. Run `build_production_pack.py`.
4. Run `validate_production_part.py`.
5. Run `python gaps.py --sync`.
6. Commit/push.

Example:

```cmd
python Compiler\build_production_pack.py ^
  --asset ARM_UPPER_L_001 ^
  --category Armor ^
  --character CHR-GRUNT-001 ^
  --part UpperArm_L ^
  --image "C:\Users\<YOU>\Downloads\UpperArm_L.png"
```

Then:

```cmd
python Compiler\validate_production_part.py --character CHR-GRUNT-001 --part UpperArm_L
python gaps.py --sync
python gaps.py --status
```

The builder refuses to silently overwrite a different existing PNG.
