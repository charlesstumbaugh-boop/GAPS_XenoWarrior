#!/usr/bin/env python3
"""
GAPS Calibrated Assembly Preview
Version 0.1.0

Reads the existing rig specification and calibration metadata and creates a
single review preview. It does not modify approved production art.

Input authority:
- Production/CHR-GRUNT-001/03_Rig/RigSpecification.yaml
- Production/CHR-GRUNT-001/04_Calibration/AssemblyOffsets.yaml
- Production/CHR-GRUNT-001/04_Calibration/JointSockets.yaml
- Production/CHR-GRUNT-001/03_Rig/RigSource/*.png when available
- Production/CHR-GRUNT-001/03_Parts/*.png as fallback

Output:
- Production/CHR-GRUNT-001/04_Calibration/CalibratedAssemblyPreview.png
"""

from pathlib import Path
from PIL import Image, ImageDraw
import yaml

ASSET_ID = "CHR-GRUNT-001"

def load_yaml(path: Path):
    if not path.is_file():
        raise RuntimeError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid YAML mapping: {path}")
    return data

def choose_source(repo: Path, part_name: str, override_path: str | None):
    rig_source_dir = repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
    parts_dir = repo/"Production"/ASSET_ID/"03_Parts"

    # If calibration names an override, prefer the cleaned RigSource file with
    # the same basename when present. This preserves semantic cleanup while
    # honoring side swaps.
    if override_path:
        basename = Path(override_path).name
        cleaned = rig_source_dir/basename
        if cleaned.is_file():
            return cleaned
        explicit = repo/Path(override_path)
        if explicit.is_file():
            return explicit

    cleaned = rig_source_dir/f"{part_name}.png"
    if cleaned.is_file():
        return cleaned

    fallback = parts_dir/f"{part_name}.png"
    if fallback.is_file():
        return fallback

    return None

def fit_to_box(im: Image.Image, box):
    x0,y0,x1,y1 = box
    bw,bh = x1-x0,y1-y0

    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return im, x0, y0

    crop = im.crop(bbox)
    scale = min(bw/crop.width, bh/crop.height)
    new_size = (
        max(1, round(crop.width*scale)),
        max(1, round(crop.height*scale)),
    )
    crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    x = x0 + (bw-crop.width)//2
    y = y0 + (bh-crop.height)//2
    return crop, x, y

def apply_rotation(im: Image.Image, degrees: float):
    if not degrees:
        return im
    return im.rotate(
        degrees,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(0,0,0,0),
    )

def main():
    repo = Path.cwd().resolve()

    rig_spec_path = repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml"
    offsets_path = repo/"Production"/ASSET_ID/"04_Calibration"/"AssemblyOffsets.yaml"
    sockets_path = repo/"Production"/ASSET_ID/"04_Calibration"/"JointSockets.yaml"
    output_dir = repo/"Production"/ASSET_ID/"04_Calibration"
    output_path = output_dir/"CalibratedAssemblyPreview.png"

    try:
        rig = load_yaml(rig_spec_path)
        offsets = load_yaml(offsets_path)
        sockets = load_yaml(sockets_path)
    except Exception as exc:
        print("CALIBRATED ASSEMBLY PREVIEW: FAIL")
        print(exc)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (1024,1024), (0,0,0,0))

    source_overrides = offsets.get("source_overrides", {})
    offset_table = offsets.get("offsets_px", {})

    missing = []

    # Render back-to-front using existing z-order authority.
    for part in sorted(rig.get("parts", []), key=lambda p: p.get("z_order", 0)):
        name = part.get("name")
        if not name or name == "Weapon":
            continue

        src = choose_source(repo, name, source_overrides.get(name))
        if src is None:
            missing.append(name)
            continue

        im = Image.open(src).convert("RGBA")

        correction = offset_table.get(name, {})
        rotation = float(correction.get("rotation_deg", 0) or 0)
        im = apply_rotation(im, rotation)

        placed, x, y = fit_to_box(im, part["guide_box_px"])
        x += int(correction.get("x", 0) or 0)
        y += int(correction.get("y", 0) or 0)

        canvas.alpha_composite(placed, (x,y))

    canvas.save(output_path, "PNG")

    # Optional pivot overlay for calibration review.
    overlay = canvas.copy()
    draw = ImageDraw.Draw(overlay)
    for joint_name, joint in sockets.get("joints", {}).items():
        target = joint.get("target_px")
        if not target or len(target) != 2:
            continue
        x,y = int(target[0]), int(target[1])
        r = 5
        draw.ellipse([x-r,y-r,x+r,y+r], outline=(255,255,255,255), width=2)
        draw.line([x-8,y,x+8,y], fill=(255,255,255,255), width=1)
        draw.line([x,y-8,x,y+8], fill=(255,255,255,255), width=1)

    overlay_path = output_dir/"CalibratedAssemblyPreview_Pivots.png"
    overlay.save(overlay_path, "PNG")

    if missing:
        print("CALIBRATED ASSEMBLY PREVIEW: PASS WITH WARNINGS")
        print("Missing parts:", ", ".join(missing))
    else:
        print("CALIBRATED ASSEMBLY PREVIEW: PASS")

    print("Preview:", output_path)
    print("Pivot preview:", overlay_path)
    print("Approved art modified: NO")
    print()
    print("NEXT: visually review both previews before changing offsets or rotations.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
