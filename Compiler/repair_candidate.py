#!/usr/bin/env python3
"""
GAPS Candidate Repair Utility
Version 0.1.0

Purpose:
- Convert a rejected PNG with a border-connected baked checkerboard/background
  into a true RGBA PNG.
- Preserve the subject by removing only background regions connected to the
  outer image border.
- Fit the repaired subject inside an exact 1024x1024 transparent canvas.
- Never overwrite the source image.
- Write a repair report beside the output.

Requirements:
    Pillow>=10.0,<12.0

Important:
This is a deterministic cleanup utility, not an image generator. Review the
output visually before promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


TOOL_VERSION = "0.1.0"


@dataclass(frozen=True)
class RepairStats:
    source_width: int
    source_height: int
    removed_pixels: int
    kept_pixels: int
    bbox: tuple[int, int, int, int]
    output_width: int
    output_height: int
    scale: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove border-connected checkerboard/background pixels and place "
            "the subject on a true transparent canvas."
        )
    )
    parser.add_argument("source", type=Path, help="Rejected source PNG.")
    parser.add_argument("output", type=Path, help="New repaired candidate PNG.")
    parser.add_argument("--canvas-width", type=int, default=1024)
    parser.add_argument("--canvas-height", type=int, default=1024)
    parser.add_argument(
        "--margin",
        type=int,
        default=48,
        help="Transparent margin around the fitted subject. Default: 48",
    )
    parser.add_argument(
        "--neutral-min",
        type=int,
        default=205,
        help="Minimum RGB channel for light neutral background pixels.",
    )
    parser.add_argument(
        "--neutral-spread",
        type=int,
        default=18,
        help="Maximum difference between RGB channels for neutral background.",
    )
    parser.add_argument(
        "--shadow-min",
        type=int,
        default=145,
        help="Minimum RGB channel for border-connected gray shadow/background.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only; do not write output files.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_background_pixel(
    rgb: tuple[int, int, int],
    neutral_min: int,
    neutral_spread: int,
    shadow_min: int,
) -> bool:
    r, g, b = rgb
    spread = max(rgb) - min(rgb)

    light_neutral = min(rgb) >= neutral_min and spread <= neutral_spread
    gray_shadow = min(rgb) >= shadow_min and spread <= max(neutral_spread, 12)

    return light_neutral or gray_shadow


def flood_remove_background(
    image: Image.Image,
    neutral_min: int,
    neutral_spread: int,
    shadow_min: int,
) -> tuple[Image.Image, int]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()

    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def enqueue_if_background(x: int, y: int) -> None:
        idx = index(x, y)
        if visited[idx]:
            return
        visited[idx] = 1

        r, g, b, _ = pixels[x, y]
        if is_background_pixel(
            (r, g, b),
            neutral_min=neutral_min,
            neutral_spread=neutral_spread,
            shadow_min=shadow_min,
        ):
            queue.append((x, y))

    for x in range(width):
        enqueue_if_background(x, 0)
        enqueue_if_background(x, height - 1)

    for y in range(height):
        enqueue_if_background(0, y)
        enqueue_if_background(width - 1, y)

    removed = 0

    while queue:
        x, y = queue.popleft()
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        removed += 1

        if x > 0:
            enqueue_if_background(x - 1, y)
        if x + 1 < width:
            enqueue_if_background(x + 1, y)
        if y > 0:
            enqueue_if_background(x, y - 1)
        if y + 1 < height:
            enqueue_if_background(x, y + 1)

    return rgba, removed


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("No visible subject remains after background removal.")
    return bbox


def fit_to_canvas(
    image: Image.Image,
    canvas_width: int,
    canvas_height: int,
    margin: int,
) -> tuple[Image.Image, tuple[int, int, int, int], float]:
    bbox = alpha_bbox(image)
    subject = image.crop(bbox)

    available_width = canvas_width - 2 * margin
    available_height = canvas_height - 2 * margin

    if available_width <= 0 or available_height <= 0:
        raise ValueError("Margin leaves no usable canvas area.")

    scale = min(
        available_width / subject.width,
        available_height / subject.height,
        1.0,
    )

    if scale < 1.0:
        new_size = (
            max(1, round(subject.width * scale)),
            max(1, round(subject.height * scale)),
        )
        subject = subject.resize(new_size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

    x = (canvas_width - subject.width) // 2
    y = canvas_height - margin - subject.height
    y = max(margin, y)

    canvas.alpha_composite(subject, (x, y))
    return canvas, bbox, scale


def write_report(
    report_path: Path,
    source: Path,
    output: Path,
    stats: RepairStats,
) -> None:
    report = {
        "tool": {
            "name": "GAPS Candidate Repair Utility",
            "version": TOOL_VERSION,
        },
        "source": {
            "path": str(source.resolve()),
            "sha256": sha256(source),
            "canvas": {
                "width": stats.source_width,
                "height": stats.source_height,
            },
        },
        "repair": {
            "method": "border_connected_neutral_background_removal",
            "removed_pixels": stats.removed_pixels,
            "kept_pixels": stats.kept_pixels,
            "source_subject_bbox": list(stats.bbox),
            "scale": stats.scale,
        },
        "output": {
            "path": str(output.resolve()),
            "sha256": sha256(output),
            "canvas": {
                "width": stats.output_width,
                "height": stats.output_height,
            },
            "mode": "RGBA",
        },
        "review": {
            "status": "REQUIRES_VISUAL_REVIEW",
            "promotion_authorized": False,
        },
    }

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()

    if not source.is_file():
        print(f"REPAIR FAILED: Source file not found:\n  {source}", file=sys.stderr)
        return 2

    if source.suffix.lower() != ".png":
        print("REPAIR FAILED: Source must be a PNG file.", file=sys.stderr)
        return 2

    if output.exists():
        print(
            f"REPAIR FAILED: Output already exists and will not be overwritten:\n  {output}",
            file=sys.stderr,
        )
        return 2

    try:
        with Image.open(source) as opened:
            opened.load()
            source_width, source_height = opened.size

            cleaned, removed = flood_remove_background(
                opened,
                neutral_min=args.neutral_min,
                neutral_spread=args.neutral_spread,
                shadow_min=args.shadow_min,
            )

        repaired, bbox, scale = fit_to_canvas(
            cleaned,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            margin=args.margin,
        )
    except Exception as error:
        print(f"REPAIR FAILED: {error}", file=sys.stderr)
        return 2

    total_pixels = source_width * source_height
    stats = RepairStats(
        source_width=source_width,
        source_height=source_height,
        removed_pixels=removed,
        kept_pixels=total_pixels - removed,
        bbox=bbox,
        output_width=args.canvas_width,
        output_height=args.canvas_height,
        scale=scale,
    )

    print("GAPS Candidate Repair Utility")
    print(f"Version: {TOOL_VERSION}")
    print(f"Source: {source}")
    print(f"Source canvas: {source_width}x{source_height}")
    print(f"Background pixels removed: {removed}")
    print(f"Subject bounding box: {bbox}")
    print(f"Output canvas: {args.canvas_width}x{args.canvas_height}")
    print(f"Scale applied: {scale:.6f}")

    if args.dry_run:
        print("DRY RUN: No files were written.")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    repaired.save(output, format="PNG", optimize=True)

    report_path = output.with_suffix(".repair.json")
    write_report(report_path, source, output, stats)

    print(f"Repaired candidate: {output}")
    print(f"Repair report: {report_path}")
    print("Status: REQUIRES VISUAL REVIEW")
    print("Next: run validate_reference.py against the repaired candidate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
