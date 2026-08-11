#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import hashlib, yaml, shutil, sys

ASSET_ID = "CHR-GRUNT-001"

# Pixel crop boxes on the approved 1024x1024 production source canvases.
# Crops isolate the semantic part only; right-side parts are mirrored from cleaned left-side counterparts.
CROP_BOXES = {
    "UpperArm_L": (285, 145, 865, 745),
    "LowerArm_L": (335, 300, 815, 700),
    "UpperLeg_L": (320, 135, 725, 720),
    "LowerLeg_L": (390, 25, 700, 705),
}

MIRROR_FROM = {
    "UpperArm_R": "UpperArm_L",
    "LowerArm_R": "LowerArm_L",
    "Hand_R": "Hand_L",
    "UpperLeg_R": "UpperLeg_L",
    "LowerLeg_R": "LowerLeg_L",
    "Foot_R": "Foot_L",
}

PASS_THROUGH = ["Head","Helmet","Torso","Pelvis","Hand_L","Foot_L"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def normalize_crop(src: Path, crop_box, dst: Path):
    im = Image.open(src).convert("RGBA")
    crop = im.crop(crop_box)
    alpha = crop.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        crop = crop.crop(bbox)

    canvas = Image.new("RGBA", (1024,1024), (0,0,0,0))
    # Preserve source pixels except resampling needed to fit; no repaint/redesign.
    margin = 64
    scale = min((1024-2*margin)/crop.width, (1024-2*margin)/crop.height, 1.0)
    if scale != 1.0:
        crop = crop.resize((round(crop.width*scale), round(crop.height*scale)), Image.Resampling.LANCZOS)
    x=(1024-crop.width)//2
    y=(1024-crop.height)//2
    canvas.alpha_composite(crop,(x,y))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst,"PNG")

def main():
    repo = Path.cwd().resolve()
    src_dir = repo/"Production"/ASSET_ID/"03_Parts"
    rig_src = repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
    rig_src.mkdir(parents=True, exist_ok=True)

    missing=[]
    for name in PASS_THROUGH + list(CROP_BOXES):
        p=src_dir/f"{name}.png"
        if not p.is_file():
            missing.append(str(p))
    if missing:
        print("RIG SOURCE CLEANUP: FAIL")
        for p in missing: print("-",p)
        return 2

    # Pass-through parts already semantically isolated enough.
    for name in PASS_THROUGH:
        shutil.copy2(src_dir/f"{name}.png", rig_src/f"{name}.png")

    # Crop left-side semantic sources.
    for name, box in CROP_BOXES.items():
        normalize_crop(src_dir/f"{name}.png", box, rig_src/f"{name}.png")

    # Right-side counterparts are deterministic mirrors of the cleaned left.
    for right,left in MIRROR_FROM.items():
        src = rig_src/f"{left}.png"
        if not src.exists():
            # For right hand/foot, left pass-through is already present.
            src = rig_src/f"{left}.png"
        im = Image.open(src).convert("RGBA").transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        im.save(rig_src/f"{right}.png","PNG")

    manifest = {
        "metadata":{
            "asset_id":ASSET_ID,
            "document":"RigSourceManifest",
            "version":"v001",
            "status":"CLEANED_FROM_APPROVED_PRODUCTION_PARTS",
            "method":"deterministic_crop_and_mirror_only"
        },
        "parts":[]
    }
    for name in ["Head","Helmet","Torso","Pelvis","UpperArm_L","LowerArm_L","Hand_L",
                 "UpperArm_R","LowerArm_R","Hand_R","UpperLeg_L","LowerLeg_L","Foot_L",
                 "UpperLeg_R","LowerLeg_R","Foot_R"]:
        p=rig_src/f"{name}.png"
        manifest["parts"].append({
            "name":name,
            "file":str(p.relative_to(repo)).replace("\\","/"),
            "sha256":sha256(p)
        })
    (rig_src/"RigSourceManifest.yaml").write_text(yaml.safe_dump(manifest,sort_keys=False),encoding="utf-8")

    print("RIG SOURCE CLEANUP: PASS")
    print("Output:", rig_src)
    print("Parts:", len(manifest["parts"]))
    print("NEXT: python Compiler/build_rig_source_preview.py")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
