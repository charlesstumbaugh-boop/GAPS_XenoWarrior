#!/usr/bin/env python3
"""
GAPS_XenoWarrior Reference Asset Validator
Version 0.1.0

Validates a PNG reference or Gold Master before an IAS is promoted.

Checks:
- exact file path exists
- PNG signature is valid
- expected canvas dimensions
- 8-bit, non-interlaced PNG
- real alpha channel exists
- transparent pixels actually exist
- likely baked checkerboard/background is rejected
- optional SHA-256 is printed for manifest use

No third-party packages are required.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PngInfo:
    width: int
    height: int
    bit_depth: int
    color_type: int
    interlace: int
    channels: int
    pixels: bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a GAPS PNG reference or Gold Master."
    )
    parser.add_argument("image", type=Path, help="Repository-relative or absolute PNG path.")
    parser.add_argument("--width", type=int, default=1024, help="Required width. Default: 1024")
    parser.add_argument("--height", type=int, default=1024, help="Required height. Default: 1024")
    parser.add_argument(
        "--allow-opaque",
        action="store_true",
        help="Allow a PNG without transparent pixels. Not recommended for sprites."
    )
    return parser.parse_args()


def read_png(path: Path) -> PngInfo:
    raw = path.read_bytes()
    if not raw.startswith(PNG_SIGNATURE):
        raise ValidationError("File is not a valid PNG.")

    offset = len(PNG_SIGNATURE)
    ihdr = None
    idat_parts: list[bytes] = []

    while offset + 12 <= len(raw):
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        chunk_type = raw[offset + 4:offset + 8]
        chunk_data = raw[offset + 8:offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            ihdr = chunk_data
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if ihdr is None or len(ihdr) != 13:
        raise ValidationError("PNG is missing a valid IHDR chunk.")
    if not idat_parts:
        raise ValidationError("PNG is missing image data.")

    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )

    if compression != 0 or filtering != 0:
        raise ValidationError("Unsupported PNG compression or filtering method.")
    if bit_depth != 8:
        raise ValidationError(f"PNG bit depth must be 8; found {bit_depth}.")
    if interlace != 0:
        raise ValidationError("Interlaced PNGs are not supported by this validator.")

    channels_by_type = {
        0: 1,  # grayscale
        2: 3,  # RGB
        4: 2,  # grayscale + alpha
        6: 4,  # RGBA
    }
    if color_type not in channels_by_type:
        raise ValidationError(f"Unsupported PNG color type: {color_type}.")

    channels = channels_by_type[color_type]
    decompressed = zlib.decompress(b"".join(idat_parts))
    stride = width * channels
    expected = height * (stride + 1)

    if len(decompressed) != expected:
        raise ValidationError(
            f"Unexpected decompressed size: expected {expected}, found {len(decompressed)}."
        )

    rows: list[bytearray] = []
    position = 0
    previous = bytearray(stride)

    for _ in range(height):
        filter_type = decompressed[position]
        position += 1
        scanline = bytearray(decompressed[position:position + stride])
        position += stride

        reconstructed = unfilter(scanline, previous, channels, filter_type)
        rows.append(reconstructed)
        previous = reconstructed

    return PngInfo(
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
        interlace=interlace,
        channels=channels,
        pixels=b"".join(rows),
    )


def unfilter(
    scanline: bytearray,
    previous: bytearray,
    bytes_per_pixel: int,
    filter_type: int,
) -> bytearray:
    result = bytearray(len(scanline))

    for index, value in enumerate(scanline):
        left = result[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = paeth(left, up, upper_left)
        else:
            raise ValidationError(f"Unsupported PNG row filter: {filter_type}.")

        result[index] = (value + predictor) & 0xFF

    return result


def paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    distance_a = abs(estimate - a)
    distance_b = abs(estimate - b)
    distance_c = abs(estimate - c)

    if distance_a <= distance_b and distance_a <= distance_c:
        return a
    if distance_b <= distance_c:
        return b
    return c


def alpha_values(info: PngInfo) -> list[int]:
    if info.color_type == 6:
        return list(info.pixels[3::4])
    if info.color_type == 4:
        return list(info.pixels[1::2])
    return []


def rgb_at(info: PngInfo, x: int, y: int) -> tuple[int, int, int]:
    index = (y * info.width + x) * info.channels

    if info.color_type in (2, 6):
        return tuple(info.pixels[index:index + 3])  # type: ignore[return-value]

    gray = info.pixels[index]
    return gray, gray, gray


def likely_baked_checkerboard(info: PngInfo) -> bool:
    """
    Detect a common baked white/light-gray transparency checkerboard.

    This is intentionally conservative and examines border/corner samples only.
    """
    sample_points: list[tuple[int, int]] = []
    step_x = max(1, info.width // 16)
    step_y = max(1, info.height // 16)

    for x in range(0, info.width, step_x):
        sample_points.append((x, 0))
        sample_points.append((x, info.height - 1))

    for y in range(0, info.height, step_y):
        sample_points.append((0, y))
        sample_points.append((info.width - 1, y))

    colors = [rgb_at(info, x, y) for x, y in sample_points]
    light_neutral = [
        color for color in colors
        if max(color) - min(color) <= 8 and min(color) >= 220
    ]

    if len(light_neutral) < max(8, len(colors) // 2):
        return False

    rounded_levels = {
        tuple((channel // 8) * 8 for channel in color)
        for color in light_neutral
    }

    return len(rounded_levels) >= 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_similar_candidates(path: Path) -> list[Path]:
    parent = path.parent.parent if path.parent.name.lower() == "design" else path.parent
    if not parent.exists():
        return []

    stem = path.stem.lower()
    tokens = [token for token in stem.replace("-", "_").split("_") if token]

    candidates: list[Path] = []
    for candidate in parent.rglob("*"):
        if not candidate.is_file():
            continue
        candidate_name = candidate.name.lower().replace("-", "_")
        if all(token in candidate_name for token in tokens[:3]):
            candidates.append(candidate)

    return sorted(candidates)


def main() -> int:
    args = parse_args()
    image_path = args.image.resolve()

    if not image_path.exists():
        print(f"VALIDATION FAILED: Required file does not exist:\n  {image_path}", file=sys.stderr)
        candidates = find_similar_candidates(image_path)
        if candidates:
            print("\nPossible similarly named files:", file=sys.stderr)
            for candidate in candidates:
                print(f"  - {candidate}", file=sys.stderr)
        return 2

    failures: list[str] = []
    warnings: list[str] = []

    try:
        info = read_png(image_path)
    except (OSError, ValidationError, zlib.error) as error:
        print(f"VALIDATION FAILED: {error}", file=sys.stderr)
        return 2

    if info.width != args.width or info.height != args.height:
        failures.append(
            f"Canvas must be {args.width}x{args.height}; "
            f"found {info.width}x{info.height}."
        )

    alpha = alpha_values(info)
    if not alpha:
        failures.append(
            "PNG has no alpha channel. A displayed checkerboard is not transparency."
        )
    elif not args.allow_opaque:
        transparent_count = sum(value < 255 for value in alpha)
        if transparent_count == 0:
            failures.append(
                "PNG contains an alpha channel, but every pixel is fully opaque."
            )
        else:
            transparent_percent = transparent_count / len(alpha) * 100
            if transparent_percent < 5:
                warnings.append(
                    f"Only {transparent_percent:.2f}% of pixels contain transparency."
                )

    if likely_baked_checkerboard(info):
        failures.append(
            "Border samples indicate a likely baked white/light-gray checkerboard background."
        )

    print("GAPS Reference Validation")
    print(f"File: {image_path}")
    print(f"Canvas: {info.width}x{info.height}")
    print(f"PNG color type: {info.color_type}")
    print(f"Alpha channel: {'yes' if alpha else 'no'}")
    print(f"SHA-256: {sha256(image_path)}")

    for warning in warnings:
        print(f"WARNING: {warning}")

    if failures:
        print("\nVALIDATION FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nVALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
