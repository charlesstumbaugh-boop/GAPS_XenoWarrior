#!/usr/bin/env python3
"""
GAPS Calibrated Idle Validation v001

First animation-engine proof:
- preserves all saved Calibration Studio transforms;
- uses visible but safe translation-only movement;
- does not rotate joints yet;
- verifies frame 0 against the calibrated rig preview.
"""

from pathlib import Path
from PIL import Image, ImageChops
import hashlib
import yaml
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from animation_engine import CalibratedRig, ENGINE_VERSION

ASSET_ID = "CHR-GRUNT-001"

FRAMES = [
    {"name": "neutral",  "upper_body": {"x": 0, "y": 0}},
    {"name": "rise_1",   "upper_body": {"x": 0, "y": -3}},
    {"name": "rise_2",   "upper_body": {"x": 0, "y": -5}},
    {"name": "settle",   "upper_body": {"x": 0, "y": -2}},
    {"name": "dip_1",    "upper_body": {"x": 0, "y": 2}},
    {"name": "return",   "upper_body": {"x": 0, "y": 0}},
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def save_yaml(path: Path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def compare_images(a: Image.Image, b: Image.Image):
    if a.size != b.size:
        return False, None
    diff = ImageChops.difference(a.convert("RGBA"), b.convert("RGBA"))
    bbox = diff.getbbox()
    return bbox is None, bbox

def main():
    repo = Path.cwd().resolve()

    try:
        rig = CalibratedRig(repo, ASSET_ID)
    except Exception as exc:
        print("ANIMATION ENGINE IDLE TEST: FAIL")
        print(exc)
        return 2

    out_dir = repo/"Production"/ASSET_ID/"05_AnimationTests"/"EngineIdle_v001"
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_records = []
    rendered_frames = []

    for idx, spec in enumerate(FRAMES):
        frame = rig.render_frame(group_deltas={"upper_body": spec["upper_body"]})
        frame_path = out_dir/f"frame_{idx:03d}.png"
        frame.save(frame_path, "PNG")
        rendered_frames.append(frame)
        frame_records.append({
            "index": idx,
            "name": spec["name"],
            "file": str(frame_path.relative_to(repo)).replace("\\","/"),
            "sha256": sha256(frame_path),
            "upper_body_delta_px": spec["upper_body"],
        })

    # Baseline proof: frame 0 should match promoted calibrated preview.
    reference_path = (
        repo/"Production"/ASSET_ID/"03_Rig"/"Calibrated"/"CalibratedRigPreview.png"
    )
    baseline_match = False
    diff_bbox = None
    if reference_path.is_file():
        reference = Image.open(reference_path).convert("RGBA")
        baseline_match, diff_bbox = compare_images(rendered_frames[0], reference)

    # Full-size strip is intentionally taller/readable than old 256px thumbnails.
    preview_h = 512
    preview_w = 512
    strip = Image.new(
        "RGBA", (preview_w*len(rendered_frames), preview_h), (0,0,0,0)
    )
    for idx, frame in enumerate(rendered_frames):
        thumb = frame.copy()
        thumb.thumbnail((preview_w, preview_h), Image.Resampling.LANCZOS)
        x = idx*preview_w + (preview_w-thumb.width)//2
        y = (preview_h-thumb.height)//2
        strip.alpha_composite(thumb, (x,y))

    strip_path = out_dir/"EngineIdleTestStrip.png"
    strip.save(strip_path, "PNG")

    # Vertical difference strip makes the 5px bob easier to see.
    overlay = Image.new("RGBA", (1024,1024), (0,0,0,0))
    alphas = [50,70,90,110,130,150]
    for frame, a in zip(rendered_frames, alphas):
        temp = frame.copy()
        alpha = temp.getchannel("A").point(lambda v, aa=a: int(v*aa/255))
        temp.putalpha(alpha)
        overlay.alpha_composite(temp)
    onion_path = out_dir/"EngineIdleOnionSkin.png"
    overlay.save(onion_path, "PNG")

    manifest = {
        "metadata": {
            "asset_id": ASSET_ID,
            "document": "AnimationEngineIdleTest",
            "version": "v001",
            "engine_version": ENGINE_VERSION,
            "status": "REVIEW_REQUIRED",
            "approved_art_modified": False,
            "animation_proven": False,
        },
        "baseline_validation": {
            "calibrated_preview": str(reference_path.relative_to(repo)).replace("\\","/")
                if reference_path.is_file() else None,
            "frame_000_pixel_exact_match": baseline_match,
            "difference_bbox": list(diff_bbox) if diff_bbox else None,
        },
        "motion_policy": {
            "type": "translation_only",
            "reason": "Prove calibrated transform preservation before hierarchical joint rotation.",
            "max_upper_body_translation_px": 5,
        },
        "frames": frame_records,
        "outputs": {
            "strip": str(strip_path.relative_to(repo)).replace("\\","/"),
            "onion_skin": str(onion_path.relative_to(repo)).replace("\\","/"),
        },
    }
    manifest_path = out_dir/"AnimationEngineIdleTest.yaml"
    save_yaml(manifest_path, manifest)

    report_path = out_dir/"BuildReport.md"
    report_path.write_text(
f"""# GAPS Animation Engine — Idle Validation v001

- Engine version: {ENGINE_VERSION}
- Frames: {len(FRAMES)}
- Approved art modified: **NO**
- Motion mode: **translation only**
- Calibrated baseline pixel-exact match: **{baseline_match}**
- Strip: `{strip_path.relative_to(repo)}`
- Onion skin: `{onion_path.relative_to(repo)}`

## Purpose

This test fixes the previous animation-builder regression where calibrated
rotation/scale (especially the hands) was not faithfully reconstructed.

Frame 000 is rebuilt from the saved calibrated manifest before any motion.
The engine then moves the entire upper-body group vertically, preserving all
saved part rotations and scales.

No rotational joint animation is attempted in v001. That is intentionally
deferred until the calibrated baseline is proven.
""",
        encoding="utf-8",
    )

    if not baseline_match:
        print("ANIMATION ENGINE IDLE TEST: FAIL")
        print("Frame 000 does not pixel-match CalibratedRigPreview.png")
        print("Difference bbox:", diff_bbox)
        print("Do not proceed to motion review.")
        return 2

    print("ANIMATION ENGINE IDLE TEST: PASS")
    print("Frames:", len(FRAMES))
    print("Calibrated baseline pixel match: YES")
    print("Approved art modified: NO")
    print("Preview strip:", strip_path)
    print("Onion skin:", onion_path)
    print("Manifest:", manifest_path)
    print("Animation proven: NOT YET — motion visual review required")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
