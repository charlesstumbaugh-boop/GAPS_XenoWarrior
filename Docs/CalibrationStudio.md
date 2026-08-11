# GAPS Calibration Studio v0.1.0

A visual desktop calibration tool for the current `CHR-GRUNT-001` front rig.

## Purpose

This replaces manual YAML guessing.

You visually drag the actual rig parts until the character looks correct.
The tool records the offsets into the existing calibration YAML.

It never overwrites approved production PNG files.

## Install

Extract the package into the repository root.

Adds:

```text
Tools/
  CalibrationStudio/
    calibration_studio.py
    Launch_Calibration_Studio.bat

Docs/
  CalibrationStudio.md
```

## Launch

From the repository root:

```cmd
python Tools\CalibrationStudio\calibration_studio.py
```

or double-click:

```text
Tools\CalibrationStudio\Launch_Calibration_Studio.bat
```

## Controls

- Click a part or select it from the list.
- Drag to move.
- Arrow keys = 1 pixel.
- Shift + Arrow = 10 pixels.
- Q / E = rotate -1° / +1°.
- Shift + Q / Shift + E = rotate -5° / +5°.
- Mouse wheel = zoom.
- `Show pivots` toggles joint markers.
- `Onion selected` makes the selected part 50% transparent.
- `Reset selected` restores the loaded position.
- `Reset all offsets` restores the whole current calibration state.

## Save

Click **Save YAML**.

The tool writes:

```text
Production/CHR-GRUNT-001/04_Calibration/AssemblyOffsets.yaml
Production/CHR-GRUNT-001/04_Calibration/VisualCalibrationSession.yaml
```

The approved art is not modified.

## Export Preview

Click **Export Preview**.

Output:

```text
Production/CHR-GRUNT-001/04_Calibration/VisualCalibrationPreview.png
```

When the character visually aligns correctly, commit:
- `AssemblyOffsets.yaml`
- `VisualCalibrationSession.yaml`
- `VisualCalibrationPreview.png`

Then the existing assembly pipeline can consume those calibrated offsets.
