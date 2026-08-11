#!/usr/bin/env python3
"""
GAPS First Idle Motion Test
Version 0.1.0

Purpose:
Create a minimal multi-frame idle-motion validation from the calibrated rig.

This is NOT a final animation.
It is a rig-behavior test.

Reads:
- Production/CHR-GRUNT-001/03_Rig/Calibrated/CalibratedRigManifest.yaml
- Production/CHR-GRUNT-001/03_Rig/RigSpecification.yaml
- Production/CHR-GRUNT-001/04_Calibration/AssemblyOffsets.yaml
- Production/CHR-GRUNT-001/03_Rig/RigSource/*.png or 03_Parts/*.png

Writes:
- Production/CHR-GRUNT-001/05_AnimationTests/Idle_v001/frame_000.png ... frame_005.png
- Production/CHR-GRUNT-001/05_AnimationTests/Idle_v001/IdleTestStrip.png
- Production/CHR-GRUNT-001/05_AnimationTests/Idle_v001/IdleTestManifest.yaml
- Production/CHR-GRUNT-001/05_AnimationTests/Idle_v001/BuildReport.md

Approved source PNGs are never modified.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import yaml
import hashlib

ASSET_ID = "CHR-GRUNT-001"
TOOL_VERSION = "0.1.0"

PART_ORDER = [
    "Head", "Helmet", "Torso", "Pelvis",
    "UpperArm_L", "LowerArm_L", "Hand_L",
    "UpperArm_R", "LowerArm_R", "Hand_R",
    "UpperLeg_L", "LowerLeg_L", "Foot_L",
    "UpperLeg_R", "LowerLeg_R", "Foot_R",
]

# Six-frame subtle idle. Values are intentionally tiny.
# Each frame can apply x/y offset and rotation on top of calibrated transforms.
IDLE_FRAMES = [
    {
        "name": "neutral",
        "parts": {}
    },
    {
        "name": "rise_1",
        "parts": {
            "Torso": {"y": -2},
            "Head": {"y": -2, "rotation": -0.5},
            "Helmet": {"y": -2, "rotation": -0.5},
            "UpperArm_L": {"rotation": -0.8},
            "UpperArm_R": {"rotation": 0.8},
        }
    },
    {
        "name": "rise_2",
        "parts": {
            "Torso": {"y": -3},
            "Head": {"y": -3, "rotation": -0.8},
            "Helmet": {"y": -3, "rotation": -0.8},
            "UpperArm_L": {"rotation": -1.2},
            "UpperArm_R": {"rotation": 1.2},
            "LowerArm_L": {"rotation": -0.5},
            "LowerArm_R": {"rotation": 0.5},
        }
    },
    {
        "name": "settle",
        "parts": {
            "Torso": {"y": -1},
            "Head": {"y": -1},
            "Helmet": {"y": -1},
        }
    },
    {
        "name": "dip_1",
        "parts": {
            "Torso": {"y": 1},
            "Head": {"y": 1, "rotation": 0.5},
            "Helmet": {"y": 1, "rotation": 0.5},
            "UpperArm_L": {"rotation": 0.7},
            "UpperArm_R": {"rotation": -0.7},
        }
    },
    {
        "name": "return",
        "parts": {}
    },
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
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def alpha_crop(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return None
    return im.crop(bbox)

def choose_source(repo: Path, manifest_part: dict):
    rel = manifest_part.get("source")
    if rel:
        p = repo / Path(rel)
        if p.is_file():
            return p

    name = manifest_part["name"]
    for p in [
        repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"/f"{name}.png",
        repo/"Production"/ASSET_ID/"03_Parts"/f"{name}.png",
    ]:
        if p.is_file():
            return p
    return None

def render_source(source: Path, placement: dict, delta: dict):
    im = Image.open(source).convert("RGBA")
    crop = alpha_crop(im)
    if crop is None:
        raise RuntimeError(f"Empty source: {source}")

    base = placement["resolved_canvas_placement"]
    target_w = int(base["render_width_px"])
    target_h = int(base["render_height_px"])

    crop = crop.resize((max(1,target_w), max(1,target_h)), Image.Resampling.LANCZOS)

    base_rotation = float(placement["visual_transform"].get("rotation_deg", 0) or 0)
    frame_rotation = float(delta.get("rotation", 0) or 0)
    total_rotation = base_rotation + frame_rotation

    # Important: The calibrated manifest render size already reflects base rotation.
    # For this test we apply only the frame delta to avoid double-rotating.
    if frame_rotation:
        crop = crop.rotate(
            frame_rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0,0,0,0),
        )

    x = int(base["x_px"]) + int(delta.get("x",0) or 0)
    y = int(base["y_px"]) + int(delta.get("y",0) or 0)

    return crop, x, y, total_rotation

def main():
    repo = Path.cwd().resolve()

    calibrated_dir = repo/"Production"/ASSET_ID/"03_Rig"/"Calibrated"
    manifest_path = calibrated_dir/"CalibratedRigManifest.yaml"

    try:
        manifest = load_yaml(manifest_path)
    except Exception as exc:
        print("IDLE MOTION TEST BUILD: FAIL")
        print(exc)
        return 2

    if manifest.get("metadata",{}).get("status") != "VISUAL_CALIBRATION_PROMOTED":
        print("IDLE MOTION TEST BUILD: FAIL")
        print("Calibrated rig manifest is not in VISUAL_CALIBRATION_PROMOTED status.")
        return 2

    parts = manifest.get("parts", {})
    missing = [name for name in PART_ORDER if name not in parts]
    if missing:
        print("IDLE MOTION TEST BUILD: FAIL")
        print("Missing calibrated parts:", ", ".join(missing))
        return 2

    out_dir = repo/"Production"/ASSET_ID/"05_AnimationTests"/"Idle_v001"
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_records = []

    for idx, frame_spec in enumerate(IDLE_FRAMES):
        canvas = Image.new("RGBA",(1024,1024),(0,0,0,0))
        deltas = frame_spec.get("parts", {})

        sorted_parts = sorted(
            PART_ORDER,
            key=lambda name: int(parts[name].get("z_order",0))
        )

        per_part = {}

        for name in sorted_parts:
            rec = parts[name]
            source = choose_source(repo, {"name": name, **rec})
            if source is None:
                print("IDLE MOTION TEST BUILD: FAIL")
                print(f"Missing source for {name}")
                return 2

            delta = deltas.get(name, {})
            rendered, x, y, total_rotation = render_source(source, rec, delta)
            canvas.alpha_composite(rendered, (x,y))

            per_part[name] = {
                "source": str(source.relative_to(repo)).replace("\\","/"),
                "x_px": x,
                "y_px": y,
                "frame_rotation_delta_deg": float(delta.get("rotation",0) or 0),
                "resolved_rotation_deg": total_rotation,
            }

        frame_path = out_dir/f"frame_{idx:03d}.png"
        canvas.save(frame_path,"PNG")

        frame_records.append({
            "index": idx,
            "name": frame_spec["name"],
            "file": str(frame_path.relative_to(repo)).replace("\\","/"),
            "sha256": sha256(frame_path),
            "parts": per_part,
        })

    # Create horizontal preview strip from the six frames.
    thumb_w = 256
    thumb_h = 256
    strip = Image.new("RGBA",(thumb_w*len(frame_records),thumb_h),(0,0,0,0))
    for idx, rec in enumerate(frame_records):
        im = Image.open(repo/Path(rec["file"])).convert("RGBA")
        im.thumbnail((thumb_w,thumb_h),Image.Resampling.LANCZOS)
        x = idx*thumb_w + (thumb_w-im.width)//2
        y = (thumb_h-im.height)//2
        strip.alpha_composite(im,(x,y))

    strip_path = out_dir/"IdleTestStrip.png"
    strip.save(strip_path,"PNG")

    idle_manifest = {
        "metadata": {
            "asset_id": ASSET_ID,
            "document": "IdleTestManifest",
            "version": "v001",
            "tool": "GAPS First Idle Motion Test",
            "tool_version": TOOL_VERSION,
            "status": "REVIEW_REQUIRED",
            "animation_proven": False,
            "approved_art_modified": False,
        },
        "purpose": "Validate rig behavior under minimal motion before creating real animation.",
        "frame_count": len(frame_records),
        "frames": frame_records,
        "review_gate": {
            "check_shoulders": True,
            "check_elbows": True,
            "check_wrists": True,
            "check_head_helmet_chain": True,
            "check_torso_pelvis_continuity": True,
            "check_knees": True,
            "check_ankles": True,
            "pass_condition": "No unacceptable separation, overlap, side swap, or armor parenting failure under motion.",
        },
        "outputs": {
            "strip": str(strip_path.relative_to(repo)).replace("\\","/"),
        }
    }

    manifest_out = out_dir/"IdleTestManifest.yaml"
    save_yaml(manifest_out,idle_manifest)

    report = out_dir/"BuildReport.md"
    report.write_text(
f"""# CHR-GRUNT-001 Idle Motion Test v001

- Tool: GAPS First Idle Motion Test {TOOL_VERSION}
- Status: **REVIEW REQUIRED**
- Frames: {len(frame_records)}
- Approved art modified: **NO**
- Calibrated rig source: `03_Rig/Calibrated/CalibratedRigManifest.yaml`
- Preview strip: `{strip_path.relative_to(repo)}`

## Purpose

This is not a final idle animation. It is a controlled rig-behavior test.

Motion is intentionally tiny:
- torso vertical motion: approximately 1–3 px;
- head/helmet vertical motion: approximately 1–3 px;
- head rotation: less than 1 degree;
- arm sway: approximately 1 degree.

## Review Gate

Review all six frames for:
- shoulder/epaulette behavior;
- elbow continuity;
- wrist/hand continuity;
- head/helmet relationship;
- torso/pelvis continuity;
- knees;
- ankles.

If the rig remains cohesive through all frames, the next step is to promote the
test to `animation_proven: true` and begin the first real idle animation.
""",
        encoding="utf-8"
    )

    print("IDLE MOTION TEST BUILD: PASS")
    print("Frames:", len(frame_records))
    print("Approved art modified: NO")
    print("Output:", out_dir)
    print("Preview strip:", strip_path)
    print("Manifest:", manifest_out)
    print("Animation proven: NOT YET — visual review required")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
