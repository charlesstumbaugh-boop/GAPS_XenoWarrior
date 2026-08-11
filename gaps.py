#!/usr/bin/env python3
from pathlib import Path
import argparse, shutil, subprocess, sys, yaml

VERSION="0.1.0"
PARTS=["Head","Helmet","Torso","Pelvis","UpperArm_L","LowerArm_L","Hand_L","UpperArm_R","LowerArm_R","Hand_R","UpperLeg_L","LowerLeg_L","Foot_L","UpperLeg_R","LowerLeg_R","Foot_R"]

def root():
    r=Path(__file__).resolve().parent
    for n in ["Compiler","Management","Reference","Production"]:
        if not (r/n).exists():
            raise RuntimeError(f"Missing repository folder: {n}")
    return r

def load(r):
    p=r/"Management"/"ProjectStatus.yaml"
    if not p.is_file(): raise RuntimeError(f"Missing {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def save(r,d):
    (r/"Management"/"ProjectStatus.yaml").write_text(yaml.safe_dump(d,sort_keys=False),encoding="utf-8")

def show(d):
    a=d["active_asset"]; p=d["project"]; h=d["handoff"]
    print("="*60)
    print(" GAPS_XenoWarrior — Production Orchestrator")
    print("="*60)
    print("Phase :",p["current_phase"])
    print("Sprint:",p["current_sprint"])
    print("Asset :",a["asset_id"],"-",a["asset_name"])
    print("Stage :",a["current_stage"])
    print("Next  :",a.get("next_required_part"))
    print("Output:",a.get("next_output"))
    print("Action:",h.get("action_type"))
    print("\nCOMPLETED")
    for x in d.get("completed",[]): print(" [PASS]",x)
    print("\nPENDING")
    for x in d.get("pending",[]): print(" [ ]",x)
    print("="*60)

def validators(r):
    scripts=["Compiler/validate_yaml.py","Compiler/validate_repository.py","Compiler/validate_humanoid_base.py","Compiler/validate_grunt_animation_profile.py"]
    bad=False
    for s in scripts:
        p=r/s
        if not p.is_file():
            print("SKIP:",s); continue
        print("\nRUN:",s)
        rc=subprocess.run([sys.executable,str(p)],cwd=r,check=False).returncode
        if rc>=2: bad=True
    print("\nGAPS VALIDATION:", "FAIL" if bad else "PASS / PASS WITH WARNINGS")
    return 2 if bad else 0

def handoff(r,d):
    a=d["active_asset"]; h=d["handoff"]
    part=a["next_required_part"]
    folder=r/"Intermediate"/"Handoffs"/a["asset_id"]/f"{part}_v001"
    folder.mkdir(parents=True,exist_ok=True)
    missing=[]
    for rel in h.get("required_inputs",[]):
        src=r/Path(rel)
        if src.is_file(): shutil.copy2(src,folder/src.name)
        else: missing.append(rel)
    (folder/"Request.md").write_text(
        f"# GAPS External Generation Handoff\n\nAsset: {a['asset_id']}\nPart: {part}\nOutput: {a['next_output']}\n\nGenerate exactly one production PNG for this part. Preserve approved identity and Animation Master style. True alpha only; no checkerboard, labels, UI, floor, scenery, or shadow.\n",
        encoding="utf-8")
    contract={"asset_id":a["asset_id"],"part":part,"artifact_type":"production_part","format":"PNG","color_mode":"RGBA","transparent_background":True,"destination":a["next_output"],"approval_required":True}
    (folder/"OutputContract.yaml").write_text(yaml.safe_dump(contract,sort_keys=False),encoding="utf-8")
    print("HANDOFF CREATED:",folder)
    if missing:
        print("WARNING missing inputs:")
        for m in missing: print(" -",m)
        return 1
    return 0

def advance(r,d):
    a=d["active_asset"]; cur=a.get("next_required_part")
    if cur not in PARTS:
        print("ADVANCE ERROR: invalid current part"); return 2
    out=r/"Production"/a["asset_id"]/"03_Parts"/f"{cur}.png"
    if not out.is_file():
        print("ADVANCE BLOCKED: missing",out); return 2
    i=PARTS.index(cur)
    if i==len(PARTS)-1:
        a["next_required_part"]=None; a["next_output"]=None; a["current_stage"]="rig_assembly"
        if "parts" in d.get("pending",[]): d["pending"].remove("parts")
        if "parts" not in d.get("completed",[]): d.setdefault("completed",[]).append("parts")
        d["handoff"]={"action_type":"local_tool","next_command":"python Compiler/build_rig.py --asset-id CHR-GRUNT-001 --build"}
    else:
        nxt=PARTS[i+1]
        a["next_required_part"]=nxt
        a["next_output"]=f"Production/{a['asset_id']}/03_Parts/{nxt}.png"
        d["handoff"]["destination"]=a["next_output"]
    save(r,d)
    print("PROJECT STATUS UPDATED")
    print("Next:",a.get("next_required_part"))
    return 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--status",action="store_true")
    ap.add_argument("--handoff",action="store_true")
    ap.add_argument("--validate",action="store_true")
    ap.add_argument("--advance",action="store_true")
    args=ap.parse_args()
    try:
        r=root(); d=load(r)
    except Exception as e:
        print("GAPS ERROR:",e); return 2
    if args.status: show(d); return 0
    if args.handoff: return handoff(r,d)
    if args.validate: return validators(r)
    if args.advance: return advance(r,d)
    while True:
        show(d)
        print("\n[1] Create handoff  [2] Validate  [3] Advance  [Q] Quit")
        c=input("Select: ").strip().lower()
        if c=="1": handoff(r,d)
        elif c=="2": validators(r)
        elif c=="3":
            if advance(r,d)==0: d=load(r)
        elif c in {"q","quit","exit"}: return 0

if __name__=="__main__":
    raise SystemExit(main())
