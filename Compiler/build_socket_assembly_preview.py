#!/usr/bin/env python3
"""
GAPS Socket-Driven Assembly Preview
Version 0.1.0

Purpose:
Align each child part by an explicit local attachment anchor to the existing
global joint target from JointSockets.yaml.

This replaces "center part inside a guide box" as the primary placement rule.

No approved PNG is modified.
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
        raise RuntimeError(f"Invalid YAML: {path}")
    return data

def visible_crop(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return None, None
    return im.crop(bbox), bbox

def choose_source(repo: Path, name: str, overrides: dict):
    rig_source = repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
    parts = repo/"Production"/ASSET_ID/"03_Parts"

    override = overrides.get(name)
    if override:
        base = Path(override).name
        p = rig_source/base
        if p.is_file():
            return p
        p = repo/Path(override)
        if p.is_file():
            return p

    p = rig_source/f"{name}.png"
    if p.is_file():
        return p

    p = parts/f"{name}.png"
    if p.is_file():
        return p

    return None

def part_scale(crop: Image.Image, guide_box):
    x0,y0,x1,y1 = guide_box
    bw,bh = x1-x0, y1-y0
    # Use guide box only for scale envelope, never for position.
    return min(bw/crop.width, bh/crop.height)

def scaled_crop(im: Image.Image, guide_box, rotation_deg=0):
    if rotation_deg:
        im = im.rotate(
            float(rotation_deg),
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0,0,0,0),
        )
    crop, _ = visible_crop(im)
    if crop is None:
        return None
    s = part_scale(crop, guide_box)
    return crop.resize(
        (max(1,round(crop.width*s)), max(1,round(crop.height*s))),
        Image.Resampling.LANCZOS
    )

def find_joint_for_child(joints: dict, child: str):
    matches=[]
    for joint_name, rec in joints.items():
        if rec.get("child") == child:
            matches.append((joint_name,rec))
    if len(matches) == 1:
        return matches[0]
    return None, None

def main():
    repo = Path.cwd().resolve()
    rig_path = repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml"
    cal = repo/"Production"/ASSET_ID/"04_Calibration"
    offsets_path = cal/"AssemblyOffsets.yaml"
    sockets_path = cal/"JointSockets.yaml"
    anchors_path = cal/"AttachmentAnchors.yaml"

    try:
        rig = load_yaml(rig_path)
        offsets = load_yaml(offsets_path)
        sockets = load_yaml(sockets_path)
        anchors = load_yaml(anchors_path)
    except Exception as exc:
        print("SOCKET ASSEMBLY PREVIEW: FAIL")
        print(exc)
        return 2

    source_overrides = offsets.get("source_overrides", {})
    offset_table = offsets.get("offsets_px", {})
    anchor_table = anchors.get("anchors", {})
    joints = sockets.get("joints", {})

    canvas = Image.new("RGBA",(1024,1024),(0,0,0,0))
    positions={}
    failures=[]

    # Torso is root. Place by existing guide box so the global skeleton remains
    # anchored to the current character coordinate space.
    parts_by_name={p["name"]:p for p in rig.get("parts",[]) if p.get("name")!="Weapon"}

    render_order=sorted(parts_by_name.values(), key=lambda p:p.get("z_order",0))

    for part in render_order:
        name=part["name"]
        src=choose_source(repo,name,source_overrides)
        if src is None:
            failures.append(f"{name}: missing source")
            continue

        correction=offset_table.get(name,{})
        im=Image.open(src).convert("RGBA")
        crop=scaled_crop(im,part["guide_box_px"],correction.get("rotation_deg",0))
        if crop is None:
            failures.append(f"{name}: empty alpha")
            continue

        if name=="Torso":
            x0,y0,x1,y1=part["guide_box_px"]
            x=x0+((x1-x0)-crop.width)//2
            y=y0+((y1-y0)-crop.height)//2
        else:
            anchor=anchor_table.get(name)
            if not anchor:
                failures.append(f"{name}: missing local anchor")
                continue

            joint_name,joint=find_joint_for_child(joints,name)
            if not joint:
                failures.append(f"{name}: no unique joint socket")
                continue

            target=joint.get("target_px")
            if not target or len(target)!=2:
                failures.append(f"{name}: missing joint target")
                continue

            ax=float(anchor.get("x_norm",0.5))*crop.width
            ay=float(anchor.get("y_norm",0.5))*crop.height
            x=round(float(target[0])-ax)
            y=round(float(target[1])-ay)

        x += int(correction.get("x",0) or 0)
        y += int(correction.get("y",0) or 0)
        positions[name]={"x":x,"y":y,"width":crop.width,"height":crop.height}
        canvas.alpha_composite(crop,(x,y))

    out=cal/"SocketAssemblyPreview.png"
    canvas.save(out,"PNG")

    overlay=canvas.copy()
    draw=ImageDraw.Draw(overlay)
    for joint_name,joint in joints.items():
        target=joint.get("target_px")
        if not target: continue
        x,y=int(target[0]),int(target[1])
        r=5
        draw.ellipse((x-r,y-r,x+r,y+r),outline=(255,255,255,255),width=2)
        draw.line((x-9,y,x+9,y),fill=(255,255,255,255),width=1)
        draw.line((x,y-9,x,y+9),fill=(255,255,255,255),width=1)

    overlay_path=cal/"SocketAssemblyPreview_Pivots.png"
    overlay.save(overlay_path,"PNG")

    placement_path=cal/"SocketAssemblyPlacements.yaml"
    placement_path.write_text(
        yaml.safe_dump({
            "metadata":{
                "asset_id":ASSET_ID,
                "document":"SocketAssemblyPlacements",
                "version":"v001",
                "status":"CALIBRATION_OUTPUT",
                "approved_art_modified":False,
            },
            "placements":positions,
            "failures":failures,
        },sort_keys=False),
        encoding="utf-8"
    )

    if failures:
        print("SOCKET ASSEMBLY PREVIEW: PASS WITH WARNINGS")
        for failure in failures:
            print("-",failure)
    else:
        print("SOCKET ASSEMBLY PREVIEW: PASS")

    print("Preview:",out)
    print("Pivot preview:",overlay_path)
    print("Placements:",placement_path)
    print("Approved art modified: NO")
    print("NEXT: visual QA of socket assembly; then adjust only AttachmentAnchors.yaml / AssemblyOffsets.yaml")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
