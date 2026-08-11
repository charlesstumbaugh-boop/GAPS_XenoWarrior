#!/usr/bin/env python3
"""
GAPS Calibrated Rig Bridge
Version 0.1.0

Purpose:
Promote the saved visual calibration into an authoritative rig-assembly
manifest without modifying approved artwork.

Reads:
- Production/CHR-GRUNT-001/03_Rig/RigSpecification.yaml
- Production/CHR-GRUNT-001/04_Calibration/AssemblyOffsets.yaml
- Production/CHR-GRUNT-001/04_Calibration/VisualCalibrationSession.yaml
- Production/CHR-GRUNT-001/03_Rig/RigSource/*.png when present
- Production/CHR-GRUNT-001/03_Parts/*.png as fallback

Writes:
- Production/CHR-GRUNT-001/03_Rig/Calibrated/CalibratedRigManifest.yaml
- Production/CHR-GRUNT-001/03_Rig/Calibrated/CalibratedRigPreview.png
- Production/CHR-GRUNT-001/03_Rig/Calibrated/CalibratedRigPreview_Pivots.png
- Production/CHR-GRUNT-001/03_Rig/Calibrated/BuildReport.md

The approved source PNG files are never overwritten.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import yaml

ASSET_ID = "CHR-GRUNT-001"
TOOL_VERSION = "0.1.0"

PART_ORDER = [
    "Head", "Helmet", "Torso", "Pelvis",
    "UpperArm_L", "LowerArm_L", "Hand_L",
    "UpperArm_R", "LowerArm_R", "Hand_R",
    "UpperLeg_L", "LowerLeg_L", "Foot_L",
    "UpperLeg_R", "LowerLeg_R", "Foot_R",
]

def load_yaml(path: Path):
    if not path.is_file():
        raise RuntimeError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid YAML mapping: {path}")
    return data

def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def alpha_crop(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return None
    return im.crop(bbox)

def choose_source(repo: Path, name: str, override: str | None):
    rig_source = repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
    parts_dir = repo/"Production"/ASSET_ID/"03_Parts"

    if override:
        basename = Path(override).name
        cleaned = rig_source/basename
        if cleaned.is_file():
            return cleaned
        explicit = repo/Path(override)
        if explicit.is_file():
            return explicit

    cleaned = rig_source/f"{name}.png"
    if cleaned.is_file():
        return cleaned

    fallback = parts_dir/f"{name}.png"
    if fallback.is_file():
        return fallback

    return None

def render_part(source: Path, guide_box, rotation_deg: float, local_scale: float):
    im = Image.open(source).convert("RGBA")
    crop = alpha_crop(im)
    if crop is None:
        raise RuntimeError(f"Source contains no visible pixels: {source}")

    x0,y0,x1,y1 = guide_box
    bw,bh = x1-x0,y1-y0
    base_scale = min(bw/crop.width, bh/crop.height)
    total_scale = base_scale * local_scale

    w = max(1, round(crop.width * total_scale))
    h = max(1, round(crop.height * total_scale))
    rendered = crop.resize((w,h), Image.Resampling.LANCZOS)

    if rotation_deg:
        rendered = rendered.rotate(
            float(rotation_deg),
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0,0,0,0),
        )

    base_w = max(1, round(crop.width * base_scale))
    base_h = max(1, round(crop.height * base_scale))
    base_x = x0 + (bw-base_w)//2
    base_y = y0 + (bh-base_h)//2

    return rendered, base_scale, base_x, base_y

def main():
    repo = Path.cwd().resolve()
    rig_path = repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml"
    cal_dir = repo/"Production"/ASSET_ID/"04_Calibration"
    offsets_path = cal_dir/"AssemblyOffsets.yaml"
    session_path = cal_dir/"VisualCalibrationSession.yaml"
    sockets_path = cal_dir/"JointSockets.yaml"

    try:
        rig = load_yaml(rig_path)
        offsets_doc = load_yaml(offsets_path)
        session_doc = load_yaml(session_path)
        sockets_doc = load_yaml(sockets_path)
    except Exception as exc:
        print("CALIBRATED RIG BUILD: FAIL")
        print(exc)
        return 2

    if session_doc.get("metadata",{}).get("status") != "SAVED":
        print("CALIBRATED RIG BUILD: FAIL")
        print("VisualCalibrationSession.yaml is not marked SAVED.")
        return 2

    saved_offsets = session_doc.get("offsets_px", {})
    assembly_offsets = offsets_doc.get("offsets_px", {})
    source_overrides = offsets_doc.get("source_overrides", {})

    # The saved session and AssemblyOffsets must agree for every part.
    mismatches = []
    for name in PART_ORDER:
        if saved_offsets.get(name) != assembly_offsets.get(name):
            mismatches.append(name)
    if mismatches:
        print("CALIBRATED RIG BUILD: FAIL")
        print("Saved visual session does not match AssemblyOffsets for:")
        for name in mismatches:
            print("-", name)
        return 2

    rig_parts = {p["name"]: p for p in rig.get("parts",[]) if p.get("name") != "Weapon"}
    missing_specs = [name for name in PART_ORDER if name not in rig_parts]
    if missing_specs:
        print("CALIBRATED RIG BUILD: FAIL")
        print("RigSpecification missing:", ", ".join(missing_specs))
        return 2

    output_dir = repo/"Production"/ASSET_ID/"03_Rig"/"Calibrated"
    output_dir.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGBA",(1024,1024),(0,0,0,0))
    placements = {}
    render_cache = {}

    # Render exactly like Calibration Studio: guide-box establishes base scale
    # and base position; saved visual offsets/rotation/scale then modify it.
    for spec in sorted(rig_parts.values(), key=lambda p:p.get("z_order",0)):
        name = spec["name"]
        source = choose_source(repo, name, source_overrides.get(name))
        if source is None:
            print("CALIBRATED RIG BUILD: FAIL")
            print(f"Missing source for {name}")
            return 2

        cal = saved_offsets.get(name, {})
        rotation = float(cal.get("rotation_deg",0) or 0)
        local_scale = float(cal.get("scale",1.0) or 1.0)
        rendered, base_scale, base_x, base_y = render_part(
            source, spec["guide_box_px"], rotation, local_scale
        )

        x = base_x + int(cal.get("x",0) or 0)
        y = base_y + int(cal.get("y",0) or 0)

        canvas.alpha_composite(rendered,(x,y))
        render_cache[name] = (rendered,x,y)

        placements[name] = {
            "parent": spec.get("parent"),
            "pivot": spec.get("pivot"),
            "z_order": spec.get("z_order"),
            "source": str(source.relative_to(repo)).replace("\\","/"),
            "source_sha256": sha256(source),
            "guide_box_px": spec["guide_box_px"],
            "base_scale": round(base_scale,6),
            "visual_transform": {
                "x_offset_px": int(cal.get("x",0) or 0),
                "y_offset_px": int(cal.get("y",0) or 0),
                "rotation_deg": rotation,
                "scale": local_scale,
            },
            "resolved_canvas_placement": {
                "x_px": x,
                "y_px": y,
                "render_width_px": rendered.width,
                "render_height_px": rendered.height,
            },
            "calibration_status": cal.get("status","UNKNOWN"),
        }

    preview_path = output_dir/"CalibratedRigPreview.png"
    canvas.save(preview_path,"PNG")

    pivot_preview = canvas.copy()
    draw = ImageDraw.Draw(pivot_preview)
    for joint_name,joint in sockets_doc.get("joints",{}).items():
        target = joint.get("target_px")
        if not target:
            continue
        x,y = int(target[0]),int(target[1])
        r=5
        draw.ellipse((x-r,y-r,x+r,y+r),outline=(255,255,255,255),width=2)
        draw.line((x-8,y,x+8,y),fill=(255,255,255,255),width=1)
        draw.line((x,y-8,x,y+8),fill=(255,255,255,255),width=1)

    pivot_path = output_dir/"CalibratedRigPreview_Pivots.png"
    pivot_preview.save(pivot_path,"PNG")

    manifest = {
        "metadata": {
            "asset_id": ASSET_ID,
            "document": "CalibratedRigManifest",
            "version": "v001",
            "tool": "GAPS Calibrated Rig Bridge",
            "tool_version": TOOL_VERSION,
            "status": "VISUAL_CALIBRATION_PROMOTED",
            "canvas": [1024,1024],
            "approved_art_modified": False,
            "source_calibration": "Production/CHR-GRUNT-001/04_Calibration/VisualCalibrationSession.yaml",
        },
        "assembly_policy": {
            "root": "Torso",
            "placement_authority": "saved_visual_calibration",
            "animation_pivot_authority": "Production/CHR-GRUNT-001/03_Rig/RigSpecification.yaml",
            "source_override_authority": "Production/CHR-GRUNT-001/04_Calibration/AssemblyOffsets.yaml",
            "note": "Visual placement is promoted; animation pivot behavior remains subject to first animation validation.",
        },
        "shoulder_review": {
            "status": "ACCEPTED_VISUALLY_PENDING_ANIMATION_BEHAVIOR_TEST",
            "observation": "Shoulder armor visually fits as an epaulette-like outer armor layer.",
            "rule": "Do not restructure source art before first animation test. Validate shoulder parenting/rotation behavior during idle/arm motion.",
        },
        "parts": placements,
        "outputs": {
            "preview": str(preview_path.relative_to(repo)).replace("\\","/"),
            "pivot_preview": str(pivot_path.relative_to(repo)).replace("\\","/"),
        },
    }
    manifest_path = output_dir/"CalibratedRigManifest.yaml"
    save_yaml(manifest_path,manifest)

    report_path = output_dir/"BuildReport.md"
    report_path.write_text(
f"""# CHR-GRUNT-001 Calibrated Rig Build Report

- Tool: GAPS Calibrated Rig Bridge {TOOL_VERSION}
- Status: **PASS**
- Parts promoted: {len(placements)}
- Approved art modified: **NO**
- Visual calibration source: `04_Calibration/VisualCalibrationSession.yaml`
- Rig specification source: `03_Rig/RigSpecification.yaml`
- Preview: `{preview_path.relative_to(repo)}`
- Pivot preview: `{pivot_path.relative_to(repo)}`
- Manifest: `{manifest_path.relative_to(repo)}`

## Shoulder Decision

The saved visual calibration places the shoulder armor successfully as an
epaulette-like outer armor layer. This visual placement is preserved. Structural
parenting/rotation behavior is intentionally deferred to the first animation
validation rather than changing approved art now.

## Gate

The calibrated rig is ready for **visual assembly validation**. It is not yet
declared animation-proven until the first pose/idle motion test passes.
""",
        encoding="utf-8"
    )

    print("CALIBRATED RIG BUILD: PASS")
    print("Parts promoted:", len(placements))
    print("Approved art modified: NO")
    print("Manifest:", manifest_path)
    print("Preview:", preview_path)
    print("Pivot preview:", pivot_path)
    print("Build report:", report_path)
    print()
    print("NEXT: visually compare CalibratedRigPreview.png to the saved Calibration Studio layout.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
