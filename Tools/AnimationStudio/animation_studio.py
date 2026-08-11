#!/usr/bin/env python3
from __future__ import annotations
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import yaml

ASSET_ID='CHR-GRUNT-001'
APP_VERSION='0.1.0'
PART_ORDER=['Head','Helmet','Torso','Pelvis','UpperArm_L','LowerArm_L','Hand_L','UpperArm_R','LowerArm_R','Hand_R','UpperLeg_L','LowerLeg_L','Foot_L','UpperLeg_R','LowerLeg_R','Foot_R']

def load_yaml(path: Path):
    if not path.is_file(): raise RuntimeError(f'Missing required file: {path}')
    data=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict): raise RuntimeError(f'Invalid YAML: {path}')
    return data

def save_yaml(path: Path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(yaml.safe_dump(data,sort_keys=False),encoding='utf-8')

def alpha_crop(im):
    b=im.getchannel('A').getbbox()
    return im.crop(b) if b else None

class AnimationStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'GAPS Animation Studio v{APP_VERSION}')
        self.geometry('1500x980')
        self.repo=Path.cwd().resolve()
        self.manifest_path=self.repo/'Production'/ASSET_ID/'03_Rig'/'Calibrated'/'CalibratedRigManifest.yaml'
        try: self.manifest=load_yaml(self.manifest_path)
        except Exception as e:
            messagebox.showerror('GAPS Animation Studio',str(e)); raise SystemExit(2)
        if self.manifest.get('metadata',{}).get('status')!='VISUAL_CALIBRATION_PROMOTED':
            messagebox.showerror('GAPS Animation Studio','Calibrated rig must be promoted first.'); raise SystemExit(2)
        self.parts_meta=self.manifest['parts']; self.base_images={}; self.base_pose={}
        for n in PART_ORDER:
            rec=self.parts_meta[n]; src=self.repo/Path(rec['source'])
            im=Image.open(src).convert('RGBA'); crop=alpha_crop(im)
            if crop is None: raise RuntimeError(f'Empty alpha: {src}')
            vt=rec.get('visual_transform',{}); place=rec['resolved_canvas_placement']
            self.base_images[n]=crop
            self.base_pose[n]={'x':int(place['x_px']),'y':int(place['y_px']),'rotation':float(vt.get('rotation_deg',0) or 0),'scale':float(vt.get('scale',1) or 1),'base_scale':float(rec.get('base_scale',1)),'z_order':int(rec.get('z_order',0))}
        self.frames=[{'name':f'Frame {i+1}','parts':copy.deepcopy(self.base_pose)} for i in range(6)]
        self.current=0; self.selected=None; self.drag_last=None; self.playing=False; self.play_after=None
        self.zoom=.72; self.pan_x=20; self.pan_y=20; self.fps=tk.IntVar(value=8); self.onion_prev=tk.BooleanVar(); self.onion_next=tk.BooleanVar(); self.anim_name=tk.StringVar(value='Idle_v001')
        self._build_ui(); self._render()
    def _build_ui(self):
        pw=ttk.Panedwindow(self,orient=tk.HORIZONTAL); pw.pack(fill=tk.BOTH,expand=True)
        left=ttk.Frame(pw,width=220); center=ttk.Frame(pw); right=ttk.Frame(pw,width=280)
        pw.add(left,weight=0); pw.add(center,weight=1); pw.add(right,weight=0)
        ttk.Label(left,text='PARTS',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=10,pady=(10,4))
        self.listbox=tk.Listbox(left,exportselection=False,font=('Consolas',10)); self.listbox.pack(fill=tk.BOTH,expand=True,padx=10,pady=(0,10))
        for n in PART_ORDER:self.listbox.insert(tk.END,n)
        self.listbox.bind('<<ListboxSelect>>',self._list_select)
        tb=ttk.Frame(center);tb.pack(fill=tk.X,padx=8,pady=6)
        ttk.Button(tb,text='Zoom +',command=lambda:self._zoom(1.1)).pack(side=tk.LEFT);ttk.Button(tb,text='Zoom -',command=lambda:self._zoom(.9)).pack(side=tk.LEFT,padx=4)
        ttk.Checkbutton(tb,text='Onion Prev',variable=self.onion_prev,command=self._render).pack(side=tk.LEFT,padx=(12,0));ttk.Checkbutton(tb,text='Onion Next',variable=self.onion_next,command=self._render).pack(side=tk.LEFT,padx=6)
        ttk.Button(tb,text='Save Animation',command=self._save).pack(side=tk.RIGHT);ttk.Button(tb,text='Load Animation',command=self._load).pack(side=tk.RIGHT,padx=6)
        self.canvas=tk.Canvas(center,bg='#171717',highlightthickness=0);self.canvas.pack(fill=tk.BOTH,expand=True,padx=8)
        self.canvas.bind('<Button-1>',self._click);self.canvas.bind('<B1-Motion>',self._drag);self.canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag_last',None));self.canvas.bind('<MouseWheel>',lambda e:self._zoom(1.08 if e.delta>0 else .92));self.canvas.bind('<Configure>',lambda e:self._render())
        controls=ttk.Frame(center);controls.pack(fill=tk.X,padx=8,pady=8)
        for txt,cmd in [('◀ Prev',self._prev),('Next ▶',self._next),('+ Frame',self._add),('Duplicate',self._dup),('Delete',self._delete),('▶ Play',self._play),('■ Stop',self._stop)]: ttk.Button(controls,text=txt,command=cmd).pack(side=tk.LEFT,padx=2)
        ttk.Label(controls,text='FPS').pack(side=tk.LEFT,padx=(10,2));ttk.Spinbox(controls,from_=1,to=30,textvariable=self.fps,width=5).pack(side=tk.LEFT)
        ttk.Button(controls,text='Export GIF',command=self._export_gif).pack(side=tk.RIGHT);ttk.Button(controls,text='Export Sprite Strip',command=self._export_strip).pack(side=tk.RIGHT,padx=5);ttk.Button(controls,text='Export Frames',command=self._export_frames).pack(side=tk.RIGHT)
        self.timeline=ttk.Frame(center);self.timeline.pack(fill=tk.X,padx=8,pady=(0,8))
        ttk.Label(right,text='SELECTED PART',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=10,pady=(10,4))
        self.sel=tk.StringVar(value='None');self.xv=tk.StringVar(value='0');self.yv=tk.StringVar(value='0');self.rv=tk.StringVar(value='0');self.sv=tk.StringVar(value='1')
        for label,var in [('Part',self.sel),('X',self.xv),('Y',self.yv),('Rotation°',self.rv),('Scale',self.sv)]:
            r=ttk.Frame(right);r.pack(fill=tk.X,padx=10,pady=3);ttk.Label(r,text=label,width=10).pack(side=tk.LEFT);e=ttk.Entry(r,textvariable=var);e.pack(side=tk.LEFT,fill=tk.X,expand=True);e.configure(state='readonly' if label=='Part' else 'normal')
        ttk.Button(right,text='Apply typed values',command=self._apply).pack(fill=tk.X,padx=10,pady=(8,4));ttk.Button(right,text='Reset part to calibrated pose',command=self._reset).pack(fill=tk.X,padx=10,pady=4)
        r=ttk.Frame(right);r.pack(fill=tk.X,padx=10,pady=(14,4));ttk.Label(r,text='Animation',width=10).pack(side=tk.LEFT);ttk.Entry(r,textvariable=self.anim_name).pack(side=tk.LEFT,fill=tk.X,expand=True)
        ttk.Label(right,text='Drag = move\nArrow = 1 px\nShift+Arrow = 10 px\nQ/E = rotate ±1°\nShift+Q/E = ±5°\nCtrl+Up/Down = scale ±1%\n\nApproved source PNGs are never modified.',justify=tk.LEFT).pack(anchor='w',padx=10,pady=8)
        self.status=tk.StringVar(value='Ready');ttk.Label(right,textvariable=self.status,wraplength=250).pack(anchor='w',padx=10,pady=8)
        self.bind('<Left>',lambda e:self._nudge(-self._step(e),0));self.bind('<Right>',lambda e:self._nudge(self._step(e),0));self.bind('<Up>',self._key_up);self.bind('<Down>',self._key_down);self.bind('q',lambda e:self._rotate(-1));self.bind('e',lambda e:self._rotate(1));self.bind('Q',lambda e:self._rotate(-5));self.bind('E',lambda e:self._rotate(5))
        self._refresh_timeline()
    def pose(self): return self.frames[self.current]['parts']
    def _part_img(self,n,pose,opacity=255):
        p=pose[n];c=self.base_images[n];s=p['base_scale']*p['scale'];im=c.resize((max(1,round(c.width*s)),max(1,round(c.height*s))),Image.Resampling.LANCZOS)
        if p['rotation']: im=im.rotate(p['rotation'],resample=Image.Resampling.BICUBIC,expand=True,fillcolor=(0,0,0,0))
        if opacity<255: im.putalpha(im.getchannel('A').point(lambda v:int(v*opacity/255)))
        return im
    def _render_pose_image(self,pose):
        out=Image.new('RGBA',(1024,1024),(0,0,0,0))
        for n in sorted(PART_ORDER,key=lambda x:pose[x]['z_order']): out.alpha_composite(self._part_img(n,pose),(round(pose[n]['x']),round(pose[n]['y'])))
        return out
    def _render(self):
        if not hasattr(self,'canvas'):return
        self.canvas.delete('all');self._refs=[];sx,sy=self.pan_x,self.pan_y;self.canvas.create_rectangle(sx,sy,sx+1024*self.zoom,sy+1024*self.zoom,fill='#050505',outline='#555')
        if self.onion_prev.get() and self.current>0:self._draw_pose(self.frames[self.current-1]['parts'],75)
        if self.onion_next.get() and self.current<len(self.frames)-1:self._draw_pose(self.frames[self.current+1]['parts'],55)
        self._draw_pose(self.pose(),255,True)
    def _draw_pose(self,pose,opacity,select=False):
        for n in sorted(PART_ORDER,key=lambda x:pose[x]['z_order']):
            im=self._part_img(n,pose,opacity);view=im.resize((max(1,round(im.width*self.zoom)),max(1,round(im.height*self.zoom))),Image.Resampling.LANCZOS);ref=ImageTk.PhotoImage(view);self._refs.append(ref);x=self.pan_x+pose[n]['x']*self.zoom;y=self.pan_y+pose[n]['y']*self.zoom;self.canvas.create_image(x,y,image=ref,anchor=tk.NW)
            if select and n==self.selected:self.canvas.create_rectangle(x,y,x+view.width,y+view.height,outline='#00ffff',width=2)
    def _click(self,e):
        wx=(e.x-self.pan_x)/self.zoom;wy=(e.y-self.pan_y)/self.zoom;hits=[];p=self.pose()
        for n in PART_ORDER:
            im=self._part_img(n,p);x,y=p[n]['x'],p[n]['y']
            if x<=wx<=x+im.width and y<=wy<=y+im.height:hits.append((p[n]['z_order'],n))
        if hits:self._select(max(hits)[1]);self.drag_last=(e.x,e.y)
    def _drag(self,e):
        if self.selected is None or self.drag_last is None:return
        dx=round((e.x-self.drag_last[0])/self.zoom);dy=round((e.y-self.drag_last[1])/self.zoom);self.pose()[self.selected]['x']+=dx;self.pose()[self.selected]['y']+=dy;self.drag_last=(e.x,e.y);self._fields();self._render()
    def _list_select(self,e=None):
        s=self.listbox.curselection();
        if s:self._select(self.listbox.get(s[0]))
    def _select(self,n):
        self.selected=n;i=PART_ORDER.index(n);self.listbox.selection_clear(0,tk.END);self.listbox.selection_set(i);self._fields();self._render()
    def _fields(self):
        if not self.selected:return
        p=self.pose()[self.selected];self.sel.set(self.selected);self.xv.set(str(round(p['x'])));self.yv.set(str(round(p['y'])));self.rv.set(f"{p['rotation']:.2f}");self.sv.set(f"{p['scale']:.4f}")
    def _apply(self):
        if not self.selected:return
        try:p=self.pose()[self.selected];p['x']=int(float(self.xv.get()));p['y']=int(float(self.yv.get()));p['rotation']=float(self.rv.get());p['scale']=max(.1,float(self.sv.get()));self._render()
        except ValueError:messagebox.showerror('Invalid values','Use numeric values.')
    def _reset(self):
        if self.selected:self.pose()[self.selected]=copy.deepcopy(self.base_pose[self.selected]);self._fields();self._render()
    def _step(self,e):return 10 if e.state&1 else 1
    def _nudge(self,dx,dy):
        if self.selected:self.pose()[self.selected]['x']+=dx;self.pose()[self.selected]['y']+=dy;self._fields();self._render()
    def _rotate(self,d):
        if self.selected:self.pose()[self.selected]['rotation']+=d;self._fields();self._render()
    def _key_up(self,e):
        if e.state&4:self._scale(1.01)
        else:self._nudge(0,-self._step(e))
    def _key_down(self,e):
        if e.state&4:self._scale(.99)
        else:self._nudge(0,self._step(e))
    def _scale(self,f):
        if self.selected:self.pose()[self.selected]['scale']*=f;self._fields();self._render()
    def _zoom(self,f):self.zoom=max(.25,min(2,self.zoom*f));self._render()
    def _refresh_timeline(self):
        if not hasattr(self,'timeline'):return
        for w in self.timeline.winfo_children():w.destroy()
        for i,fr in enumerate(self.frames):tk.Button(self.timeline,text=f'{i+1}\n{fr["name"]}',width=9,relief=tk.SUNKEN if i==self.current else tk.RAISED,command=lambda j=i:self._goto(j)).pack(side=tk.LEFT,padx=2)
    def _goto(self,i):self.current=max(0,min(i,len(self.frames)-1));self._fields();self._refresh_timeline();self._render()
    def _prev(self):self._goto((self.current-1)%len(self.frames))
    def _next(self):self._goto((self.current+1)%len(self.frames))
    def _add(self):self.frames.append({'name':f'Frame {len(self.frames)+1}','parts':copy.deepcopy(self.base_pose)});self._goto(len(self.frames)-1)
    def _dup(self):fr=copy.deepcopy(self.frames[self.current]);fr['name']=f'Frame {len(self.frames)+1}';self.frames.insert(self.current+1,fr);self._goto(self.current+1)
    def _delete(self):
        if len(self.frames)<=1:return
        self.frames.pop(self.current);self.current=min(self.current,len(self.frames)-1);self._refresh_timeline();self._render()
    def _play(self):
        if self.playing:return
        self.playing=True;self._playstep()
    def _playstep(self):
        if not self.playing:return
        self._next();self.play_after=self.after(max(1,int(1000/max(1,self.fps.get()))),self._playstep)
    def _stop(self):
        self.playing=False
        if self.play_after:self.after_cancel(self.play_after);self.play_after=None
    def outdir(self):return self.repo/'Production'/ASSET_ID/'06_Animations'/(self.anim_name.get().strip() or 'Animation_v001')
    def _save(self):
        d=self.outdir();d.mkdir(parents=True,exist_ok=True);data={'metadata':{'asset_id':ASSET_ID,'document':'AnimationStudioAnimation','version':'v001','studio_version':APP_VERSION,'status':'WORKING','approved_art_modified':False},'animation':{'name':self.anim_name.get(),'fps':int(self.fps.get()),'frame_count':len(self.frames),'frames':[]}}
        for i,fr in enumerate(self.frames):data['animation']['frames'].append({'index':i,'name':fr['name'],'parts':{n:{'x':p['x'],'y':p['y'],'rotation_deg':p['rotation'],'scale':p['scale']} for n,p in fr['parts'].items()}})
        save_yaml(d/'Animation.yaml',data);self.status.set(f'Saved {d/"Animation.yaml"}')
    def _load(self):
        p=self.outdir()/'Animation.yaml'
        if not p.is_file():messagebox.showerror('Not found',str(p));return
        data=load_yaml(p);frames=[]
        for fr in data['animation']['frames']:
            pose=copy.deepcopy(self.base_pose)
            for n,t in fr['parts'].items():pose[n]['x']=t['x'];pose[n]['y']=t['y'];pose[n]['rotation']=t['rotation_deg'];pose[n]['scale']=t['scale']
            frames.append({'name':fr['name'],'parts':pose})
        self.frames=frames;self.fps.set(data['animation'].get('fps',8));self._goto(0)
    def _export_frames(self):
        d=self.outdir()/'Frames';d.mkdir(parents=True,exist_ok=True)
        for i,fr in enumerate(self.frames):self._render_pose_image(fr['parts']).save(d/f'frame_{i:03d}.png')
        self.status.set(f'Frames exported: {d}')
    def _export_strip(self):
        d=self.outdir();d.mkdir(parents=True,exist_ok=True);ims=[self._render_pose_image(f['parts']) for f in self.frames];out=Image.new('RGBA',(1024*len(ims),1024),(0,0,0,0))
        for i,im in enumerate(ims):out.alpha_composite(im,(i*1024,0))
        out.save(d/'SpriteStrip.png');self.status.set(f'Sprite strip exported: {d/"SpriteStrip.png"}')
    def _export_gif(self):
        d=self.outdir();d.mkdir(parents=True,exist_ok=True);ims=[self._render_pose_image(f['parts']).convert('P',palette=Image.ADAPTIVE) for f in self.frames];dur=max(1,int(1000/max(1,self.fps.get())));ims[0].save(d/'Preview.gif',save_all=True,append_images=ims[1:],duration=dur,loop=0,disposal=2);self.status.set(f'GIF exported: {d/"Preview.gif"}')

def main(): AnimationStudio().mainloop()
if __name__=='__main__': main()
