#!/usr/bin/env python3
"""
GAPS Animation Studio v0.5.0 — Transform Core

Key architectural change:
Animation no longer "rotates a PNG around its center and compensates its x/y".

Each calibrated part is first rendered as a full 1024x1024 layer in its exact
approved/calibrated position. Animation then applies serializable global affine
operations to that full layer:

    translate(dx, dy)
    rotate(degrees, pivot_x, pivot_y)
    scale(factor, pivot_x, pivot_y)

A rotation around the elbow therefore leaves the elbow coordinate fixed by
construction. Descendant layers receive the identical transform, so the hand
travels rigidly with the forearm.

Approved source PNGs are never modified.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk
import yaml

ASSET_ID = "CHR-GRUNT-001"
APP_VERSION = "0.5.0"
CANVAS = 1024

PART_ORDER = [
    "Head","Helmet","Torso","Pelvis",
    "UpperArm_L","LowerArm_L","Hand_L",
    "UpperArm_R","LowerArm_R","Hand_R",
    "UpperLeg_L","LowerLeg_L","Foot_L",
    "UpperLeg_R","LowerLeg_R","Foot_R",
]

def load_yaml(path: Path, default=None):
    if not path.is_file():
        if default is not None:
            return copy.deepcopy(default)
        raise RuntimeError(f"Missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else copy.deepcopy(default or {})

def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

def alpha_crop(im: Image.Image):
    bb = im.getchannel("A").getbbox()
    if not bb:
        raise RuntimeError("Source image contains no visible alpha pixels.")
    return im.crop(bb)

def rotate_point(x, y, cx, cy, degrees):
    r = math.radians(degrees)
    vx, vy = x-cx, y-cy
    return (
        cx + vx*math.cos(r) - vy*math.sin(r),
        cy + vx*math.sin(r) + vy*math.cos(r),
    )

class AnimationStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"GAPS Animation Studio v{APP_VERSION}")
        self.geometry("1500x980")
        self.minsize(1200, 800)

        self.repo = Path.cwd().resolve()
        self.cal_dir = self.repo/"Production"/ASSET_ID/"04_Calibration"
        self.manifest_path = self.repo/"Production"/ASSET_ID/"03_Rig"/"Calibrated"/"CalibratedRigManifest.yaml"
        self.pivot_path = self.cal_dir/"AnimationPivots.yaml"

        self.manifest = load_yaml(self.manifest_path)
        if self.manifest.get("metadata",{}).get("status") != "VISUAL_CALIBRATION_PROMOTED":
            messagebox.showerror("GAPS Animation Studio","Calibrated rig is not promoted.")
            raise SystemExit(2)

        self.parts_meta = self.manifest["parts"]
        self.parent_map = {n:self.parts_meta[n].get("parent") for n in PART_ORDER}
        self.base_layers = {}
        self.base_pivots = self._load_pivots()

        self.zoom = 0.74
        self.pan_x = 22
        self.pan_y = 22
        self.hierarchy = tk.BooleanVar(value=True)
        self.show_pivots = tk.BooleanVar(value=True)
        self.onion_prev = tk.BooleanVar(value=False)
        self.onion_next = tk.BooleanVar(value=False)
        self.fps = tk.IntVar(value=6)
        self.anim_name = tk.StringVar(value="WaveTest_v001")

        self.selected = None
        self.set_pivot_mode = False
        self.drag_last = None
        self.playing = False
        self.play_after = None

        self._build_base_layers()
        self.frames = [self._new_frame(f"Frame {i+1}") for i in range(6)]
        self.current = 0

        self._build_ui()
        self._render()

    # ---------- Base calibrated rig ----------

    def _load_pivots(self):
        saved = {}
        if self.pivot_path.is_file():
            try:
                saved = load_yaml(self.pivot_path).get("pivots",{})
            except Exception:
                saved = {}

        result = {}
        rig_spec = load_yaml(
            self.repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml",
            {"pivots":{}}
        )
        rig_pivots = rig_spec.get("pivots",{})

        for n in PART_ORDER:
            if n in saved:
                result[n] = {
                    "x":float(saved[n]["x_px"]),
                    "y":float(saved[n]["y_px"]),
                }
            else:
                key = self.parts_meta[n].get("pivot")
                rec = rig_pivots.get(key,{})
                result[n] = {
                    "x":float(rec.get("x_px",512)),
                    "y":float(rec.get("y_px",512)),
                }
        return result

    def _build_base_layers(self):
        for n in PART_ORDER:
            rec = self.parts_meta[n]
            src = self.repo/Path(rec["source"])
            if not src.is_file():
                raise RuntimeError(f"Missing source: {src}")

            im = alpha_crop(Image.open(src).convert("RGBA"))
            base_scale = float(rec.get("base_scale",1.0))
            vt = rec.get("visual_transform",{})
            local_scale = float(vt.get("scale",1.0) or 1.0)
            rotation = float(vt.get("rotation_deg",0) or 0)

            s = base_scale * local_scale
            im = im.resize(
                (max(1,round(im.width*s)), max(1,round(im.height*s))),
                Image.Resampling.LANCZOS
            )
            if rotation:
                im = im.rotate(
                    rotation,
                    resample=Image.Resampling.BICUBIC,
                    expand=True,
                    fillcolor=(0,0,0,0),
                )

            place = rec["resolved_canvas_placement"]
            layer = Image.new("RGBA",(CANVAS,CANVAS),(0,0,0,0))
            layer.alpha_composite(im,(int(place["x_px"]),int(place["y_px"])))
            self.base_layers[n] = layer

    # ---------- Transform operations ----------

    def _apply_op(self, layer: Image.Image, op: dict) -> Image.Image:
        typ = op["type"]

        if typ == "translate":
            dx = float(op["dx"])
            dy = float(op["dy"])
            # Pillow affine maps output -> input, hence negative translation.
            return layer.transform(
                layer.size,
                Image.Transform.AFFINE,
                (1,0,-dx,0,1,-dy),
                resample=Image.Resampling.BICUBIC,
                fillcolor=(0,0,0,0),
            )

        if typ == "rotate":
            return layer.rotate(
                float(op["degrees"]),
                resample=Image.Resampling.BICUBIC,
                expand=False,
                center=(float(op["pivot_x"]),float(op["pivot_y"])),
                fillcolor=(0,0,0,0),
            )

        if typ == "scale":
            s = float(op["factor"])
            if s <= 0:
                return layer
            px = float(op["pivot_x"])
            py = float(op["pivot_y"])
            inv = 1.0/s
            return layer.transform(
                layer.size,
                Image.Transform.AFFINE,
                (
                    inv, 0, (1-inv)*px,
                    0, inv, (1-inv)*py,
                ),
                resample=Image.Resampling.BICUBIC,
                fillcolor=(0,0,0,0),
            )

        return layer

    def _part_layer(self, frame, name):
        layer = self.base_layers[name]
        for op in frame["ops"].get(name,[]):
            layer = self._apply_op(layer, op)
        return layer

    def _frame_image(self, frame):
        out = Image.new("RGBA",(CANVAS,CANVAS),(0,0,0,0))
        for n in sorted(PART_ORDER,key=lambda x:int(self.parts_meta[x].get("z_order",0))):
            out.alpha_composite(self._part_layer(frame,n))
        return out

    # ---------- Hierarchy ----------

    def _children(self,n):
        return [c for c,p in self.parent_map.items() if p == n]

    def _descendants(self,n):
        result = []
        stack = list(self._children(n))
        while stack:
            c = stack.pop(0)
            if c not in result:
                result.append(c)
                stack.extend(self._children(c))
        return result

    def _targets(self,n):
        return [n] + self._descendants(n) if self.hierarchy.get() else [n]

    def _new_frame(self,name):
        return {
            "name":name,
            "ops":{n:[] for n in PART_ORDER},
            "pivots":copy.deepcopy(self.base_pivots),
        }

    def frame(self):
        return self.frames[self.current]

    def _translate(self,n,dx,dy):
        fr = self.frame()
        for t in self._targets(n):
            fr["ops"][t].append({"type":"translate","dx":dx,"dy":dy})
            fr["pivots"][t]["x"] += dx
            fr["pivots"][t]["y"] += dy

    def _rotate(self,degrees):
        if not self.selected:
            return
        fr = self.frame()
        pivot = fr["pivots"][self.selected]
        px,py = float(pivot["x"]),float(pivot["y"])

        targets = self._targets(self.selected)
        for t in targets:
            fr["ops"][t].append({
                "type":"rotate",
                "degrees":float(degrees),
                "pivot_x":px,
                "pivot_y":py,
            })

        # Selected pivot remains fixed. Descendant pivots orbit around it.
        for t in self._descendants(self.selected):
            x,y = fr["pivots"][t]["x"],fr["pivots"][t]["y"]
            nx,ny = rotate_point(x,y,px,py,degrees)
            fr["pivots"][t]["x"] = nx
            fr["pivots"][t]["y"] = ny

        self.status.set(
            f"{self.selected}: {degrees:+.1f}° about fixed pivot "
            f"({px:.1f}, {py:.1f})"
        )
        self._render()

    def _scale(self,factor):
        if not self.selected:
            return
        fr = self.frame()
        p = fr["pivots"][self.selected]
        px,py = p["x"],p["y"]
        for t in self._targets(self.selected):
            fr["ops"][t].append({
                "type":"scale","factor":factor,
                "pivot_x":px,"pivot_y":py,
            })
        for t in self._descendants(self.selected):
            x,y=fr["pivots"][t]["x"],fr["pivots"][t]["y"]
            fr["pivots"][t]["x"]=px+(x-px)*factor
            fr["pivots"][t]["y"]=py+(y-py)*factor
        self._render()

    # ---------- UI ----------

    def _build_ui(self):
        outer=ttk.Panedwindow(self,orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH,expand=True)
        left=ttk.Frame(outer,width=210);center=ttk.Frame(outer);right=ttk.Frame(outer,width=300)
        outer.add(left,weight=0);outer.add(center,weight=1);outer.add(right,weight=0)

        ttk.Label(left,text="PARTS",font=("Segoe UI",11,"bold")).pack(anchor="w",padx=10,pady=(10,4))
        self.part_list=tk.Listbox(left,exportselection=False,font=("Consolas",10))
        self.part_list.pack(fill=tk.BOTH,expand=True,padx=10,pady=(0,10))
        self.part_list.bind("<<ListboxSelect>>",self._list_select)
        for n in PART_ORDER:self.part_list.insert(tk.END,n)

        tb=ttk.Frame(center);tb.pack(fill=tk.X,padx=8,pady=6)
        ttk.Checkbutton(tb,text="Hierarchy",variable=self.hierarchy,command=self._render).pack(side=tk.LEFT)
        ttk.Checkbutton(tb,text="Show Pivots",variable=self.show_pivots,command=self._render).pack(side=tk.LEFT,padx=8)
        ttk.Checkbutton(tb,text="Onion Prev",variable=self.onion_prev,command=self._render).pack(side=tk.LEFT,padx=(12,0))
        ttk.Checkbutton(tb,text="Onion Next",variable=self.onion_next,command=self._render).pack(side=tk.LEFT,padx=8)
        ttk.Button(tb,text="Zoom +",command=lambda:self._zoom(1.1)).pack(side=tk.RIGHT)
        ttk.Button(tb,text="Zoom -",command=lambda:self._zoom(.9)).pack(side=tk.RIGHT,padx=4)
        ttk.Button(tb,text="Fit",command=self._fit).pack(side=tk.RIGHT,padx=4)

        self.canvas=tk.Canvas(center,bg="#141414",highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH,expand=True,padx=8,pady=(0,6))
        self.canvas.bind("<Button-1>",self._click)
        self.canvas.bind("<B1-Motion>",self._drag)
        self.canvas.bind("<ButtonRelease-1>",lambda e:setattr(self,"drag_last",None))
        self.canvas.bind("<MouseWheel>",lambda e:self._zoom(1.08 if e.delta>0 else .92))
        self.canvas.bind("<Configure>",lambda e:self._render())

        tl=ttk.Frame(center);tl.pack(fill=tk.X,padx=8,pady=(0,8))
        controls=ttk.Frame(tl);controls.pack(fill=tk.X)
        ttk.Button(controls,text="◀",command=self._prev).pack(side=tk.LEFT)
        ttk.Button(controls,text="▶",command=self._next).pack(side=tk.LEFT,padx=3)
        ttk.Button(controls,text="Duplicate",command=self._duplicate).pack(side=tk.LEFT,padx=(10,3))
        ttk.Button(controls,text="+ Frame",command=self._add).pack(side=tk.LEFT,padx=3)
        ttk.Button(controls,text="Delete",command=self._delete).pack(side=tk.LEFT,padx=3)
        ttk.Button(controls,text="Play",command=self._play).pack(side=tk.LEFT,padx=(12,3))
        ttk.Button(controls,text="Stop",command=self._stop).pack(side=tk.LEFT,padx=3)
        ttk.Label(controls,text="FPS").pack(side=tk.LEFT,padx=(10,2))
        ttk.Spinbox(controls,from_=1,to=30,textvariable=self.fps,width=4).pack(side=tk.LEFT)

        ttk.Button(controls,text="Save",command=self._save_animation).pack(side=tk.RIGHT)
        ttk.Button(controls,text="Export Strip",command=self._export_strip).pack(side=tk.RIGHT,padx=4)
        ttk.Button(controls,text="Export GIF",command=self._export_gif).pack(side=tk.RIGHT,padx=4)

        self.timeline=ttk.Frame(tl);self.timeline.pack(fill=tk.X,pady=(5,0))

        ttk.Label(right,text="SELECTED PART",font=("Segoe UI",11,"bold")).pack(anchor="w",padx=10,pady=(10,5))
        self.sel_var=tk.StringVar(value="None")
        ttk.Label(right,textvariable=self.sel_var,font=("Consolas",10)).pack(anchor="w",padx=10)

        ttk.Button(right,text="Set Selected Pivot",command=self._begin_set_pivot).pack(fill=tk.X,padx=10,pady=(12,3))
        ttk.Button(right,text="Save Animation Pivots",command=self._save_pivots).pack(fill=tk.X,padx=10,pady=3)
        ttk.Button(right,text="Clear Frame Transforms",command=self._clear_selected).pack(fill=tk.X,padx=10,pady=3)

        ttk.Separator(right).pack(fill=tk.X,padx=10,pady=12)
        ttk.Label(right,text="ANIMATION NAME").pack(anchor="w",padx=10)
        ttk.Entry(right,textvariable=self.anim_name).pack(fill=tk.X,padx=10,pady=(3,8))

        ttk.Label(
            right,
            text=(
                "Drag: translate selected hierarchy\n"
                "Arrow: 1 px\n"
                "Shift+Arrow: 10 px\n"
                "Q/E: rotate ±1°\n"
                "Shift+Q/E: ±5°\n"
                "Ctrl+Up/Down: scale ±1%\n\n"
                "v0.5 Transform Core:\n"
                "rotation is applied to the complete 1024×1024 layer\n"
                "around the exact calibrated pivot.\n\n"
                "No center-axis compensation is used."
            ),
            justify=tk.LEFT,wraplength=270
        ).pack(anchor="w",padx=10,pady=6)

        self.status=tk.StringVar(value="Ready")
        ttk.Label(right,textvariable=self.status,wraplength=270,justify=tk.LEFT).pack(anchor="w",padx=10,pady=6)

        self.bind("<Left>",lambda e:self._nudge(-self._step(e),0))
        self.bind("<Right>",lambda e:self._nudge(self._step(e),0))
        self.bind("<Up>",self._key_up)
        self.bind("<Down>",self._key_down)
        self.bind("q",lambda e:self._rotate(-1))
        self.bind("e",lambda e:self._rotate(1))
        self.bind("Q",lambda e:self._rotate(-5))
        self.bind("E",lambda e:self._rotate(5))

        self._refresh_timeline()

    # ---------- Rendering ----------

    def _draw_frame(self,fr,opacity=255,selectable=False):
        for n in sorted(PART_ORDER,key=lambda x:int(self.parts_meta[x].get("z_order",0))):
            layer=self._part_layer(fr,n)
            bb=layer.getchannel("A").getbbox()
            if not bb:continue
            crop=layer.crop(bb)
            if opacity<255:
                crop=crop.copy()
                crop.putalpha(crop.getchannel("A").point(lambda v:int(v*opacity/255)))
            view=crop.resize(
                (max(1,round(crop.width*self.zoom)),max(1,round(crop.height*self.zoom))),
                Image.Resampling.LANCZOS
            )
            ref=ImageTk.PhotoImage(view)
            self._refs.append(ref)
            x=self.pan_x+bb[0]*self.zoom
            y=self.pan_y+bb[1]*self.zoom
            self.canvas.create_image(x,y,image=ref,anchor=tk.NW)
            if selectable and n==self.selected:
                self.canvas.create_rectangle(
                    x,y,x+view.width,y+view.height,outline="#00ffff",width=2
                )

    def _render(self):
        if not hasattr(self,"canvas"):return
        self.canvas.delete("all");self._refs=[]
        self.canvas.create_rectangle(
            self.pan_x,self.pan_y,
            self.pan_x+CANVAS*self.zoom,self.pan_y+CANVAS*self.zoom,
            fill="#050505",outline="#555"
        )
        if self.onion_prev.get() and self.current>0:
            self._draw_frame(self.frames[self.current-1],70)
        if self.onion_next.get() and self.current<len(self.frames)-1:
            self._draw_frame(self.frames[self.current+1],55)
        self._draw_frame(self.frame(),255,True)

        if self.show_pivots.get():
            for n,p in self.frame()["pivots"].items():
                x=self.pan_x+p["x"]*self.zoom
                y=self.pan_y+p["y"]*self.zoom
                r=6 if n==self.selected else 4
                col="#00ffff" if n==self.selected else "#ffffff"
                self.canvas.create_oval(x-r,y-r,x+r,y+r,outline=col,width=2)
                if n==self.selected:
                    self.canvas.create_line(x-10,y,x+10,y,fill=col)
                    self.canvas.create_line(x,y-10,x,y+10,fill=col)

    # ---------- Selection / editing ----------

    def _select(self,n):
        self.selected=n
        self.sel_var.set(n)
        idx=PART_ORDER.index(n)
        self.part_list.selection_clear(0,tk.END)
        self.part_list.selection_set(idx);self.part_list.see(idx)
        self._render()

    def _list_select(self,e=None):
        s=self.part_list.curselection()
        if s:self._select(self.part_list.get(s[0]))

    def _click(self,e):
        wx=(e.x-self.pan_x)/self.zoom
        wy=(e.y-self.pan_y)/self.zoom

        if self.set_pivot_mode and self.selected:
            # Rig-level calibration: propagate to all frames.
            for fr in self.frames:
                fr["pivots"][self.selected]={"x":float(wx),"y":float(wy)}
            self.base_pivots[self.selected]={"x":float(wx),"y":float(wy)}
            self.set_pivot_mode=False
            self.status.set(f"Pivot set: {self.selected} ({wx:.1f},{wy:.1f})")
            self._render()
            return

        hits=[]
        fr=self.frame()
        for n in PART_ORDER:
            bb=self._part_layer(fr,n).getchannel("A").getbbox()
            if bb and bb[0]<=wx<=bb[2] and bb[1]<=wy<=bb[3]:
                hits.append((int(self.parts_meta[n].get("z_order",0)),n))
        if hits:
            self._select(max(hits)[1])
            self.drag_last=(e.x,e.y)

    def _drag(self,e):
        if not self.selected or self.drag_last is None:return
        dx=round((e.x-self.drag_last[0])/self.zoom)
        dy=round((e.y-self.drag_last[1])/self.zoom)
        self._translate(self.selected,dx,dy)
        self.drag_last=(e.x,e.y)
        self._render()

    def _nudge(self,dx,dy):
        if self.selected:
            self._translate(self.selected,dx,dy);self._render()

    def _step(self,e):return 10 if e.state&1 else 1

    def _key_up(self,e):
        if e.state&0x0004:self._scale(1.01)
        else:self._nudge(0,-self._step(e))

    def _key_down(self,e):
        if e.state&0x0004:self._scale(.99)
        else:self._nudge(0,self._step(e))

    def _begin_set_pivot(self):
        if not self.selected:
            messagebox.showinfo("Set Pivot","Select a part first.");return
        self.set_pivot_mode=True
        self.status.set(f"Click exact joint for {self.selected}.")

    def _save_pivots(self):
        piv=self.frame()["pivots"]
        self.base_pivots=copy.deepcopy(piv)
        save_yaml(self.pivot_path,{
            "metadata":{
                "asset_id":ASSET_ID,
                "document":"AnimationPivots",
                "version":"v002",
                "studio_version":APP_VERSION,
                "status":"CALIBRATED",
                "approved_art_modified":False,
            },
            "pivots":{
                n:{
                    "pivot":self.parts_meta[n].get("pivot"),
                    "x_px":round(piv[n]["x"],3),
                    "y_px":round(piv[n]["y"],3),
                } for n in PART_ORDER
            },
        })
        messagebox.showinfo("Pivots Saved",str(self.pivot_path))

    def _clear_selected(self):
        if not self.selected:return
        self.frame()["ops"][self.selected]=[]
        self.frame()["pivots"][self.selected]=copy.deepcopy(self.base_pivots[self.selected])
        self._render()

    # ---------- Timeline ----------

    def _refresh_timeline(self):
        if not hasattr(self,"timeline"):return
        for w in self.timeline.winfo_children():w.destroy()
        for i,fr in enumerate(self.frames):
            tk.Button(
                self.timeline,text=str(i+1),width=5,
                relief=tk.SUNKEN if i==self.current else tk.RAISED,
                command=lambda idx=i:self._goto(idx)
            ).pack(side=tk.LEFT,padx=2)

    def _goto(self,i):
        self.current=max(0,min(i,len(self.frames)-1))
        self._refresh_timeline();self._render()

    def _prev(self):self._goto((self.current-1)%len(self.frames))
    def _next(self):self._goto((self.current+1)%len(self.frames))

    def _duplicate(self):
        self.frames.insert(self.current+1,copy.deepcopy(self.frame()))
        self.frames[self.current+1]["name"]=f"Frame {self.current+2}"
        self._goto(self.current+1)

    def _add(self):
        self.frames.append(self._new_frame(f"Frame {len(self.frames)+1}"))
        self._goto(len(self.frames)-1)

    def _delete(self):
        if len(self.frames)<=1:return
        self.frames.pop(self.current)
        self.current=min(self.current,len(self.frames)-1)
        self._refresh_timeline();self._render()

    def _play(self):
        if self.playing:return
        self.playing=True;self._play_step()

    def _play_step(self):
        if not self.playing:return
        self._next()
        self.play_after=self.after(max(1,int(1000/max(1,self.fps.get()))),self._play_step)

    def _stop(self):
        self.playing=False
        if self.play_after:
            self.after_cancel(self.play_after);self.play_after=None

    # ---------- Persistence / export ----------

    def _anim_dir(self):
        name=self.anim_name.get().strip() or "Animation_v001"
        return self.repo/"Production"/ASSET_ID/"06_Animations"/name

    def _save_animation(self):
        d=self._anim_dir();d.mkdir(parents=True,exist_ok=True)
        save_yaml(d/"Animation.yaml",{
            "metadata":{
                "asset_id":ASSET_ID,
                "document":"AnimationStudioAnimation",
                "version":"v002",
                "studio_version":APP_VERSION,
                "transform_core":"full_canvas_affine_ops",
                "status":"WORKING",
                "approved_art_modified":False,
            },
            "animation":{
                "name":self.anim_name.get().strip() or "Animation_v001",
                "fps":int(self.fps.get()),
                "frame_count":len(self.frames),
                "frames":[
                    {
                        "index":i,
                        "name":fr["name"],
                        "ops":fr["ops"],
                        "pivots":{
                            n:{
                                "x_px":round(fr["pivots"][n]["x"],3),
                                "y_px":round(fr["pivots"][n]["y"],3),
                            } for n in PART_ORDER
                        },
                    } for i,fr in enumerate(self.frames)
                ],
            },
        })
        messagebox.showinfo("Saved",str(d/"Animation.yaml"))

    def _export_strip(self):
        d=self._anim_dir();d.mkdir(parents=True,exist_ok=True)
        images=[self._frame_image(fr) for fr in self.frames]
        strip=Image.new("RGBA",(CANVAS*len(images),CANVAS),(0,0,0,0))
        for i,im in enumerate(images):strip.alpha_composite(im,(i*CANVAS,0))
        p=d/"SpriteStrip.png";strip.save(p,"PNG")
        messagebox.showinfo("Exported",str(p))

    def _export_gif(self):
        d=self._anim_dir();d.mkdir(parents=True,exist_ok=True)
        ims=[self._frame_image(fr).convert("P",palette=Image.ADAPTIVE) for fr in self.frames]
        p=d/"Preview.gif"
        ms=max(1,int(1000/max(1,self.fps.get())))
        ims[0].save(p,save_all=True,append_images=ims[1:],duration=ms,loop=0,disposal=2,transparency=0)
        messagebox.showinfo("Exported",str(p))

    def _zoom(self,f):
        self.zoom=max(.25,min(2,self.zoom*f));self._render()

    def _fit(self):
        cw=max(300,self.canvas.winfo_width());ch=max(300,self.canvas.winfo_height())
        self.zoom=min((cw-45)/CANVAS,(ch-45)/CANVAS);self.pan_x=20;self.pan_y=20;self._render()

def main():
    AnimationStudio().mainloop()

if __name__=="__main__":
    main()
