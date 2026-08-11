#!/usr/bin/env python3
"""
GAPS Animation Engine v0.1.0

Core rule:
Every animation begins from the promoted calibrated rig pose.
Saved rotation, scale, source overrides, and placement are reconstructed before
any animation delta is applied.

This module does not modify approved source art.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import yaml

ASSET_ID = "CHR-GRUNT-001"
ENGINE_VERSION = "0.1.0"

PART_ORDER = [
    "Head", "Helmet", "Torso", "Pelvis",
    "UpperArm_L", "LowerArm_L", "Hand_L",
    "UpperArm_R", "LowerArm_R", "Hand_R",
    "UpperLeg_L", "LowerLeg_L", "Foot_L",
    "UpperLeg_R", "LowerLeg_R", "Foot_R",
]

UPPER_BODY = [
    "Head", "Helmet", "Torso",
    "UpperArm_L", "LowerArm_L", "Hand_L",
    "UpperArm_R", "LowerArm_R", "Hand_R",
]

def load_yaml(path: Path):
    if not path.is_file():
        raise RuntimeError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid YAML mapping: {path}")
    return data

def alpha_crop(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("Source image has no visible alpha pixels.")
    return im.crop(bbox)

class CalibratedRig:
    def __init__(self, repo: Path, asset_id: str = ASSET_ID):
        self.repo = repo.resolve()
        self.asset_id = asset_id
        self.calibrated_dir = (
            self.repo/"Production"/asset_id/"03_Rig"/"Calibrated"
        )
        self.manifest_path = self.calibrated_dir/"CalibratedRigManifest.yaml"
        self.manifest = load_yaml(self.manifest_path)

        status = self.manifest.get("metadata", {}).get("status")
        if status != "VISUAL_CALIBRATION_PROMOTED":
            raise RuntimeError(
                f"Calibrated rig status must be VISUAL_CALIBRATION_PROMOTED; found {status}"
            )

        self.parts = self.manifest.get("parts", {})
        missing = [n for n in PART_ORDER if n not in self.parts]
        if missing:
            raise RuntimeError("Calibrated rig missing parts: " + ", ".join(missing))

    def source_path(self, name: str) -> Path:
        rel = self.parts[name].get("source")
        if not rel:
            raise RuntimeError(f"Manifest source missing for {name}")
        p = self.repo/Path(rel)
        if not p.is_file():
            raise RuntimeError(f"Source file missing for {name}: {p}")
        return p

    def calibrated_part_image(self, name: str) -> Image.Image:
        """
        Rebuild EXACT calibrated part transform:
        source alpha crop -> base_scale * saved local scale -> saved rotation.
        """
        rec = self.parts[name]
        visual = rec.get("visual_transform", {})
        base_scale = float(rec.get("base_scale", 1.0))
        local_scale = float(visual.get("scale", 1.0) or 1.0)
        base_rotation = float(visual.get("rotation_deg", 0) or 0)

        im = Image.open(self.source_path(name)).convert("RGBA")
        crop = alpha_crop(im)

        scale = base_scale * local_scale
        w = max(1, round(crop.width * scale))
        h = max(1, round(crop.height * scale))
        rendered = crop.resize((w, h), Image.Resampling.LANCZOS)

        if base_rotation:
            rendered = rendered.rotate(
                base_rotation,
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=(0, 0, 0, 0),
            )

        return rendered

    def base_position(self, name: str) -> tuple[int, int]:
        resolved = self.parts[name]["resolved_canvas_placement"]
        return int(resolved["x_px"]), int(resolved["y_px"])

    def z_order(self, name: str) -> int:
        return int(self.parts[name].get("z_order", 0))

    def render_frame(
        self,
        part_deltas: dict | None = None,
        group_deltas: dict | None = None,
    ) -> Image.Image:
        """
        Render a frame from calibrated baseline.

        v0.1 deliberately supports translation-only animation deltas.
        This preserves joint integrity while proving the calibrated transform
        baseline. Rotational chain inheritance will be added only after this gate.
        """
        part_deltas = part_deltas or {}
        group_deltas = group_deltas or {}

        canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))

        upper_dx = int(group_deltas.get("upper_body", {}).get("x", 0) or 0)
        upper_dy = int(group_deltas.get("upper_body", {}).get("y", 0) or 0)

        for name in sorted(PART_ORDER, key=self.z_order):
            im = self.calibrated_part_image(name)
            x, y = self.base_position(name)

            if name in UPPER_BODY:
                x += upper_dx
                y += upper_dy

            delta = part_deltas.get(name, {})
            x += int(delta.get("x", 0) or 0)
            y += int(delta.get("y", 0) or 0)

            canvas.alpha_composite(im, (x, y))

        return canvas
