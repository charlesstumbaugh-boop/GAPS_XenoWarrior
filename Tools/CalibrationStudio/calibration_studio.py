#!/usr/bin/env python3
"""
GAPS Calibration Studio
Version 0.1.0

Desktop visual rig-calibration tool for GAPS_XenoWarrior.

Features:
- Loads the current CHR-GRUNT-001 rig sources.
- Drag parts visually on a 1024x1024 canvas.
- Select by clicking artwork or part list.
- Arrow keys nudge 1 px; Shift+Arrow nudges 10 px.
- Q / E rotate selected part by -1 / +1 degree.
- Shift+Q / Shift+E rotate by -5 / +5 degrees.
- Toggle pivot markers.
- Toggle selected-part opacity for onion-skin alignment.
- Reset selected part or all parts.
- Save calibration directly into AssemblyOffsets.yaml.
- Export a calibrated PNG preview.
- Does NOT modify approved production PNG files.

Run from repository root:
    python Tools/CalibrationStudio/calibration_studio.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk
import yaml

ASSET_ID = "CHR-GRUNT-001"
APP_VERSION = "0.1.0"

CANVAS_SIZE = 1024

PART_ORDER = [
    "Head", "Helmet", "Torso", "Pelvis",
    "UpperArm_L", "LowerArm_L", "Hand_L",
    "UpperArm_R", "LowerArm_R", "Hand_R",
    "UpperLeg_L", "LowerLeg_L", "Foot_L",
    "UpperLeg_R", "LowerLeg_R", "Foot_R",
]

def load_yaml(path: Path, default=None):
    if not path.is_file():
        if default is not None:
            return default
        raise RuntimeError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    return default if default is not None else {}

def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def alpha_bbox(im: Image.Image):
    return im.getchannel("A").getbbox()

class CalibrationStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"GAPS Calibration Studio v{APP_VERSION}")
        self.geometry("1440x1000")
        self.minsize(1180, 800)

        self.repo = Path.cwd().resolve()
        self._validate_repo()

        self.rig_spec_path = self.repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml"
        self.cal_dir = self.repo/"Production"/ASSET_ID/"04_Calibration"
        self.offsets_path = self.cal_dir/"AssemblyOffsets.yaml"
        self.sockets_path = self.cal_dir/"JointSockets.yaml"

        self.rig_spec = load_yaml(self.rig_spec_path)
        self.offsets_doc = load_yaml(self.offsets_path, {
            "metadata": {
                "asset_id": ASSET_ID,
                "document": "AssemblyOffsets",
                "version": "v001",
                "status": "CALIBRATION_DRAFT",
                "art_files_modified": False,
            },
            "source_overrides": {},
            "offsets_px": {},
        })
        self.sockets_doc = load_yaml(self.sockets_path, {"joints": {}})

        self.zoom = 0.78
        self.pan_x = 25
        self.pan_y = 25
        self.show_pivots = tk.BooleanVar(value=True)
        self.onion_selected = tk.BooleanVar(value=False)

        self.parts = {}
        self.selected = None
        self.drag_last = None

        self._build_ui()
        self._load_parts()
        self._render_all()

    def _validate_repo(self):
        required = [
            self.repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml",
            self.repo/"Production"/ASSET_ID/"03_Parts",
        ]
        missing = [p for p in required if not p.exists()]
        if missing:
            messagebox.showerror(
                "Repository not found",
                "Run this tool from the GAPS_XenoWarrior repository root.\n\nMissing:\n" +
                "\n".join(str(p) for p in missing)
            )
            self.destroy()
            raise SystemExit(2)

    def _build_ui(self):
        outer = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(outer, width=255)
        center = ttk.Frame(outer)
        right = ttk.Frame(outer, width=300)
        outer.add(left, weight=0)
        outer.add(center, weight=1)
        outer.add(right, weight=0)

        ttk.Label(left, text="PARTS", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10,4))
        self.listbox = tk.Listbox(left, exportselection=False, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.listbox.bind("<<ListboxSelect>>", self._list_select)

        for name in PART_ORDER:
            self.listbox.insert(tk.END, name)

        toolbar = ttk.Frame(center)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(toolbar, text="Zoom +", command=lambda: self._change_zoom(1.10)).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Zoom -", command=lambda: self._change_zoom(0.90)).pack(side=tk.LEFT, padx=(4,0))
        ttk.Button(toolbar, text="Fit", command=self._fit_canvas).pack(side=tk.LEFT, padx=(4,12))

        ttk.Checkbutton(toolbar, text="Show pivots", variable=self.show_pivots, command=self._render_all).pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="Onion selected", variable=self.onion_selected, command=self._render_all).pack(side=tk.LEFT, padx=(10,0))

        ttk.Button(toolbar, text="Export Preview", command=self._export_preview).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Save YAML", command=self._save_calibration).pack(side=tk.RIGHT, padx=(0,6))

        canvas_frame = ttk.Frame(center)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))

        self.canvas = tk.Canvas(canvas_frame, background="#1b1b1b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)
        self.canvas.bind("<MouseWheel>", self._mousewheel_zoom)
        self.canvas.bind("<Configure>", lambda e: self._render_all())

        self.bind("<Left>", lambda e: self._nudge(-self._step(e),0))
        self.bind("<Right>", lambda e: self._nudge(self._step(e),0))
        self.bind("<Up>", lambda e: self._nudge(0,-self._step(e)))
        self.bind("<Down>", lambda e: self._nudge(0,self._step(e)))
        self.bind("q", lambda e: self._rotate(-1))
        self.bind("e", lambda e: self._rotate(1))
        self.bind("Q", lambda e: self._rotate(-5))
        self.bind("E", lambda e: self._rotate(5))

        ttk.Label(right, text="SELECTED PART", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10,4))

        form = ttk.Frame(right)
        form.pack(fill=tk.X, padx=10)

        self.sel_name = tk.StringVar(value="None")
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self.rot_var = tk.StringVar(value="0")
        self.scale_var = tk.StringVar(value="1.000")

        for label, var in [
            ("Part", self.sel_name),
            ("X offset", self.x_var),
            ("Y offset", self.y_var),
            ("Rotation°", self.rot_var),
            ("Scale", self.scale_var),
        ]:
            row = ttk.Frame(form)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label, width=11).pack(side=tk.LEFT)
            ent = ttk.Entry(row, textvariable=var)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if label == "Part":
                ent.configure(state="readonly")

        ttk.Button(right, text="Apply typed values", command=self._apply_fields).pack(fill=tk.X, padx=10, pady=(10,4))
        ttk.Button(right, text="Reset selected", command=self._reset_selected).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(right, text="Reset all offsets", command=self._reset_all).pack(fill=tk.X, padx=10, pady=4)

        ttk.Separator(right).pack(fill=tk.X, padx=10, pady=12)
        ttk.Label(right, text="CONTROLS", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)
        ttk.Label(
            right,
            text=(
                "Drag: move selected part\n"
                "Arrow keys: 1 px nudge\n"
                "Shift+Arrow: 10 px nudge\n"
                "Q / E: rotate -1° / +1°\n"
                "Shift+Q / Shift+E: ±5°\n"
                "Mouse wheel: zoom\n\n"
                "Artwork is never overwritten."
            ),
            justify=tk.LEFT,
        ).pack(anchor="w", padx=10, pady=5)

        ttk.Separator(right).pack(fill=tk.X, padx=10, pady=12)
        ttk.Label(right, text="STATUS", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(right, textvariable=self.status, wraplength=270, justify=tk.LEFT).pack(anchor="w", padx=10, pady=5)

    def _load_parts(self):
        source_overrides = self.offsets_doc.get("source_overrides", {})
        offsets = self.offsets_doc.get("offsets_px", {})
        rig_parts = {p["name"]: p for p in self.rig_spec.get("parts", []) if p.get("name") != "Weapon"}

        for name in PART_ORDER:
            spec = rig_parts.get(name)
            if not spec:
                continue

            src = self._choose_source(name, source_overrides.get(name))
            if not src:
                continue

            im = Image.open(src).convert("RGBA")
            bbox = alpha_bbox(im)
            if not bbox:
                continue
            crop = im.crop(bbox)

            # Start from existing guide-box scale + center placement.
            x0,y0,x1,y1 = spec["guide_box_px"]
            bw,bh = x1-x0,y1-y0
            s = min(bw/crop.width, bh/crop.height)
            base_w = max(1, round(crop.width*s))
            base_h = max(1, round(crop.height*s))

            off = offsets.get(name, {})
            x = x0 + (bw-base_w)//2 + int(off.get("x",0) or 0)
            y = y0 + (bh-base_h)//2 + int(off.get("y",0) or 0)

            self.parts[name] = {
                "src": src,
                "original_crop": crop,
                "base_scale": s,
                "scale": float(off.get("scale", 1.0) or 1.0),
                "x": x,
                "y": y,
                "rotation": float(off.get("rotation_deg",0) or 0),
                "z": spec.get("z_order",0),
                "guide_box": spec["guide_box_px"],
                "tk": None,
                "canvas_id": None,
                "render_size": (base_w,base_h),
                "initial": (x,y,float(off.get("rotation_deg",0) or 0),float(off.get("scale",1.0) or 1.0)),
            }

    def _choose_source(self, name, override):
        rig_source = self.repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
        parts_dir = self.repo/"Production"/ASSET_ID/"03_Parts"

        if override:
            base = Path(override).name
            p = rig_source/base
            if p.is_file():
                return p
            p = self.repo/Path(override)
            if p.is_file():
                return p

        p = rig_source/f"{name}.png"
        if p.is_file():
            return p

        p = parts_dir/f"{name}.png"
        if p.is_file():
            return p

        return None

    def _render_part_image(self, name):
        p = self.parts[name]
        crop = p["original_crop"]

        total_scale = p["base_scale"] * p["scale"]
        w = max(1, round(crop.width*total_scale))
        h = max(1, round(crop.height*total_scale))
        im = crop.resize((w,h), Image.Resampling.LANCZOS)

        if p["rotation"]:
            im = im.rotate(
                p["rotation"],
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=(0,0,0,0),
            )

        if name == self.selected and self.onion_selected.get():
            alpha = im.getchannel("A")
            alpha = alpha.point(lambda v: int(v*0.5))
            im.putalpha(alpha)

        p["render_size"] = im.size
        return im

    def _render_all(self):
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        sx = self.pan_x
        sy = self.pan_y

        # 1024 production canvas.
        x0 = sx
        y0 = sy
        x1 = sx + CANVAS_SIZE*self.zoom
        y1 = sy + CANVAS_SIZE*self.zoom
        self.canvas.create_rectangle(x0,y0,x1,y1, fill="#090909", outline="#5a5a5a", width=2)

        for name in sorted(self.parts, key=lambda n: self.parts[n]["z"]):
            p = self.parts[name]
            im = self._render_part_image(name)
            view = im.resize(
                (max(1,round(im.width*self.zoom)), max(1,round(im.height*self.zoom))),
                Image.Resampling.LANCZOS,
            )
            tk_im = ImageTk.PhotoImage(view)
            p["tk"] = tk_im

            cx = sx + p["x"]*self.zoom
            cy = sy + p["y"]*self.zoom
            item = self.canvas.create_image(cx,cy, image=tk_im, anchor=tk.NW, tags=(f"part:{name}",))
            p["canvas_id"] = item

            if name == self.selected:
                self.canvas.create_rectangle(
                    cx, cy, cx+view.width, cy+view.height,
                    outline="#00ffff", width=2,
                )

        if self.show_pivots.get():
            for joint_name, joint in self.sockets_doc.get("joints",{}).items():
                target = joint.get("target_px")
                if not target:
                    continue
                x = sx + float(target[0])*self.zoom
                y = sy + float(target[1])*self.zoom
                r=5
                self.canvas.create_oval(x-r,y-r,x+r,y+r,outline="white",width=2)
                self.canvas.create_line(x-8,y,x+8,y,fill="white")
                self.canvas.create_line(x,y-8,x,y+8,fill="white")

    def _canvas_click(self, event):
        # hit-test topmost part by alpha-aware rectangle approximation
        wx = (event.x-self.pan_x)/self.zoom
        wy = (event.y-self.pan_y)/self.zoom
        candidates=[]
        for name,p in self.parts.items():
            w,h = p["render_size"]
            if p["x"] <= wx <= p["x"]+w and p["y"] <= wy <= p["y"]+h:
                candidates.append((p["z"],name))
        if candidates:
            _,name=max(candidates)
            self._select(name)
            self.drag_last=(event.x,event.y)
        else:
            self.drag_last=None

    def _canvas_drag(self,event):
        if not self.selected or not self.drag_last:
            return
        dx=(event.x-self.drag_last[0])/self.zoom
        dy=(event.y-self.drag_last[1])/self.zoom
        self.parts[self.selected]["x"] += round(dx)
        self.parts[self.selected]["y"] += round(dy)
        self.drag_last=(event.x,event.y)
        self._update_fields()
        self._render_all()

    def _canvas_release(self,event):
        self.drag_last=None

    def _list_select(self,event=None):
        sel=self.listbox.curselection()
        if sel:
            self._select(self.listbox.get(sel[0]))

    def _select(self,name):
        if name not in self.parts:
            return
        self.selected=name
        idx=PART_ORDER.index(name)
        self.listbox.selection_clear(0,tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self._update_fields()
        self.status.set(f"Selected: {name}")
        self._render_all()

    def _update_fields(self):
        if not self.selected:
            return
        p=self.parts[self.selected]
        self.sel_name.set(self.selected)
        # Store offsets relative to initial guide-box placement before current offsets.
        init_x,init_y,_,_=p["initial"]
        self.x_var.set(str(round(p["x"]-init_x)))
        self.y_var.set(str(round(p["y"]-init_y)))
        self.rot_var.set(f"{p['rotation']:.1f}")
        self.scale_var.set(f"{p['scale']:.3f}")

    def _apply_fields(self):
        if not self.selected:
            return
        p=self.parts[self.selected]
        try:
            ox=int(float(self.x_var.get()))
            oy=int(float(self.y_var.get()))
            rot=float(self.rot_var.get())
            scale=float(self.scale_var.get())
        except ValueError:
            messagebox.showerror("Invalid values","X/Y must be numbers; rotation and scale must be numeric.")
            return
        init_x,init_y,_,_=p["initial"]
        p["x"]=init_x+ox
        p["y"]=init_y+oy
        p["rotation"]=rot
        p["scale"]=max(0.1,scale)
        self._render_all()

    def _step(self,event):
        return 10 if (event.state & 0x0001) else 1

    def _nudge(self,dx,dy):
        if not self.selected:
            return
        self.parts[self.selected]["x"] += dx
        self.parts[self.selected]["y"] += dy
        self._update_fields()
        self._render_all()

    def _rotate(self,degrees):
        if not self.selected:
            return
        self.parts[self.selected]["rotation"] += degrees
        self._update_fields()
        self._render_all()

    def _reset_selected(self):
        if not self.selected:
            return
        p=self.parts[self.selected]
        x,y,r,s=p["initial"]
        p["x"],p["y"],p["rotation"],p["scale"]=x,y,r,s
        self._update_fields()
        self._render_all()

    def _reset_all(self):
        if not messagebox.askyesno("Reset all","Reset all parts to their loaded calibration positions?"):
            return
        for p in self.parts.values():
            x,y,r,s=p["initial"]
            p["x"],p["y"],p["rotation"],p["scale"]=x,y,r,s
        self._update_fields()
        self._render_all()

    def _change_zoom(self,factor):
        self.zoom=max(0.25,min(2.0,self.zoom*factor))
        self._render_all()

    def _mousewheel_zoom(self,event):
        self._change_zoom(1.08 if event.delta>0 else 0.92)

    def _fit_canvas(self):
        cw=max(300,self.canvas.winfo_width())
        ch=max(300,self.canvas.winfo_height())
        self.zoom=min((cw-50)/1024,(ch-50)/1024)
        self.pan_x=25
        self.pan_y=25
        self._render_all()

    def _calibration_offsets(self):
        result={}
        for name,p in self.parts.items():
            init_x,init_y,_,_=p["initial"]
            result[name]={
                "x": int(round(p["x"]-init_x)),
                "y": int(round(p["y"]-init_y)),
                "rotation_deg": round(float(p["rotation"]),2),
                "scale": round(float(p["scale"]),4),
                "status": "VISUALLY_CALIBRATED",
            }
        return result

    def _save_calibration(self):
        doc=load_yaml(self.offsets_path, self.offsets_doc)
        doc.setdefault("metadata",{})
        doc["metadata"]["calibration_tool"]="GAPS Calibration Studio"
        doc["metadata"]["calibration_tool_version"]=APP_VERSION
        doc["metadata"]["art_files_modified"]=False
        doc["offsets_px"]=self._calibration_offsets()
        save_yaml(self.offsets_path,doc)

        session_path=self.cal_dir/"VisualCalibrationSession.yaml"
        save_yaml(session_path,{
            "metadata":{
                "asset_id":ASSET_ID,
                "document":"VisualCalibrationSession",
                "version":"v001",
                "tool_version":APP_VERSION,
                "status":"SAVED",
            },
            "offsets_px":doc["offsets_px"],
        })

        self.status.set(f"Saved calibration to {self.offsets_path}")
        messagebox.showinfo("Saved","Calibration YAML saved.\n\nApproved PNG files were not modified.")

    def _export_preview(self):
        canvas=Image.new("RGBA",(1024,1024),(0,0,0,0))
        for name in sorted(self.parts,key=lambda n:self.parts[n]["z"]):
            p=self.parts[name]
            # Render without onion-skin effect.
            was=self.onion_selected.get()
            self.onion_selected.set(False)
            im=self._render_part_image(name)
            self.onion_selected.set(was)
            canvas.alpha_composite(im,(int(round(p["x"])),int(round(p["y"]))))
        out=self.cal_dir/"VisualCalibrationPreview.png"
        canvas.save(out,"PNG")
        self.status.set(f"Preview exported: {out}")
        messagebox.showinfo("Preview exported",str(out))

def main():
    CalibrationStudio().mainloop()

if __name__ == "__main__":
    main()
