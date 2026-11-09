"""Original Gunsmith Bench art; Python3 + Pillow, no external art inputs.

Native furniture convention:32 model pixels per block/metre. Root=(-16,0,0),
local X width, +Y up, -Z working/front edge. Geometry and textures are original.
"""
from pathlib import Path
import base64, hashlib, json, math, random, uuid
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NAME = "360 Gunsmith Bench"
STEM = "RS_Gunsmith_Bench"
SIZE = 512
COLORS = {
    "walnut": "#68452e", "woodedge": "#a87948", "wooddark": "#403126",
    "steel": "#485762", "steelbright": "#8c9ba2", "iron": "#29353e",
    "copper": "#bf8053", "brass": "#d4b775", "leather": "#586b65",
    "mat": "#2c4f5c", "blueprint": "#385c6c", "paper": "#c6bd98",
    "rubber": "#232f35", "dark": "#14232c", "cyan": "#81ddea",
    "amber": "#ffcf78", "red": "#a65c45", "ink": "#769ca7",
}
FACES = {"front": (0,1), "back": (0,1), "left": (2,1),
         "right": (2,1), "top": (0,2), "bottom": (0,2)}
BBFACES = dict(front="north", back="south", left="west", right="east", top="up", bottom="down")
IDENTITY = dict(x=0,y=0,z=0,w=1)
def vec(v): return dict(zip("xyz", v))
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, "360-noscope-original-gunsmith-bench/"+s))
def quat(rotation):
    axes = [(a,v) for a,v in zip("xyz",rotation) if v]
    assert len(axes)<=1
    q=IDENTITY.copy()
    if axes:
        axis, angle=axes[0]; q[axis]=round(math.sin(math.radians(angle/2)),8);q["w"]=round(math.cos(math.radians(angle/2)),8)
    return q

class Bench:
    def __init__(self): self.parts=[]
    def box(self,name,center,size,material="steel",detail="",rotation=(0,0,0),glow=False):
        assert all(v>0 and v==int(v) for v in size), (name,size)
        self.parts.append(dict(name=name,center=list(center),size=list(size),material=material,
                               detail=detail,rotation=list(rotation),shading_mode="fullbright" if glow else "standard"))
    def bolt(self,name,center,face="front",material="steelbright"):
        self.box(name,center,(1,1,1),material)

def geometry():
    b=Bench(); add=b.box
    # Four splayed-looking, steel-shod timber posts; open middle keeps it a bench.
    for x in (-27,27):
        for z in (-11,11):
            suffix=f"{x}_{z}"
            add("Walnut_Leg_"+suffix,(x,14,z),(5,26,5),"walnut","wood")
            add("Steel_Foot_"+suffix,(x,2,z),(7,4,7),"iron","panel")
            add("Copper_Leg_Collar_"+suffix,(x,25,z),(6,3,6),"copper","panel")
            for y in (8,23): b.bolt("Leg_Pin_"+suffix+str(y),(x,y,z-2.6),material="brass")
    for z in (-11,11):
        add("Lower_Stretcher_"+str(z),(0,6,z),(54,4,4),"walnut","wood")
        add("Worktop_Rail_"+str(z),(0,27,z),(59,4,4),"wooddark","wood")
    for x in (-27,27): add("End_Stretcher_"+str(x),(x,7,0),(4,4,21),"walnut","wood")
    for i in range(4): add("Shelf_Plank_"+str(i),(0,9,-8+i*5),(51,2,5),"walnut","wood")
    # Three thick slabs, a shaped front lip and bolted corners.
    for i,z in enumerate((-10,0,10)):
        add("Butcherblock_Top_"+str(i),(0,30,z),(62,5,10),"woodedge","worktop")
    for x in (-31,31):
        add("Forged_End_Cap_"+str(x),(x,30,0),(2,6,32),"steel","panel")
        for z in (-12,12): b.bolt("Top_Rivet_"+str(x)+str(z),(x,33.1,z),material="brass")
    add("Front_Iron_Apron",(0,26,-14.5),(58,5,2),"iron","panel")
    add("Rear_Iron_Apron",(0,26,14.5),(58,5,2),"iron","panel")
    add("Brass_Makers_Plate",(1,26,-15.6),(14,3,1),"brass","makers")
    # Right drawers, left open ammunition crate and a visible steel tool case.
    add("Drawer_Cabinet",(18,19,1),(18,17,22),"wooddark","wood")
    for i,y in enumerate((15,21)):
        add("Drawer_Front_"+str(i),(18,y,-10.7),(17,5,2),"walnut","panel")
        add("Drawer_Brass_Label_"+str(i),(18,y,-11.8),(5,2,1),"brass","label")
        add("Drawer_Pull_"+str(i),(18,y-1,-12.6),(7,1,2),"iron")
        for x in (12,24):b.bolt("Drawer_Pin_"+str(i)+str(x),(x,y,-11.8))
    add("Crate_Floor",(-17,11,0),(19,2,19),"wooddark","wood")
    for z in (-9,9):
        for y in (13,17):add("Crate_Slat_"+str(z)+str(y),(-17,y,z),(20,3,2),"walnut","wood")
    for x in (-26,-8):
        for y in (13,17):add("Crate_End_"+str(x)+str(y),(x,y,0),(2,3,17),"woodedge","wood")
    for x in (-22,-17,-12):
        add("Crated_Copper_Rounds_"+str(x),(x,19,1),(3,6,3),"copper","cartridge")
        add("Crated_Round_Tip_"+str(x),(x,22.5,1),(2,1,2),"brass")
    add("Steel_Tool_Case",(-1,13,6),(12,5,12),"steel","panel")
    add("Tool_Case_Lid",(-1,16,6),(13,2,13),"iron","panel")
    add("Tool_Case_Latch",(-1,14,-.7),(3,3,1),"copper","panel")
    # A useful open work surface, with a rifle between padded jaws.
    add("Cutting_Mat",(1,33,-4),(32,1,16),"mat","grid")
    add("Calibration_Blueprint",(2,33.6,6),(19,1,8),"blueprint","blueprint")
    add("Paper_Weight",(10,34.4,8),(3,1,3),"copper")
    add("Vise_Base",(-3,34.5,-2),(13,2,10),"iron","panel")
    add("Vise_Anvil",(-3,36.5,-2),(10,2,8),"steel","panel")
    for z in (-6,2):
        add("Vise_Jaw_"+str(z),(-3,39,z),(10,5,2),"steelbright","panel")
        add("Vise_Leather_Pad_"+str(z),(-3,39,z+(.65 if z<0 else -.65)),(8,3,1),"leather")
    add("Vise_Screw",(-3,36,-9),(3,3,10),"iron","thread")
    add("Vise_Screw_Collar",(-3,36,-13),(5,4,3),"copper")
    add("Vise_Cross_Handle",(-3,35,-14),(11,1,1),"steelbright")
    for x in (-9,3):add("Vise_Handle_Stop_"+str(x),(x,35,-14),(2,3,2),"iron")
    # A restrained unfinished rifle prop (not one of the usable inventory guns).
    add("Clamped_Rifle_Receiver",(-1,40,-2),(15,4,4),"steel","panel")
    add("Clamped_Rifle_Barrel",(-14,40,-2),(15,2,2),"iron")
    add("Clamped_Rifle_Bolt",(3,42,-2),(4,1,3),"copper")
    add("Clamped_Rifle_Stock",(11,39,-2),(10,5,3),"walnut","wood")
    add("Clamped_Rifle_Butt",(16,38,-2),(2,7,4),"wooddark")
    add("Clamped_Rifle_Trigger",(5,37,-2),(2,3,2),"copper")
    add("Clamped_Barrel_Collar",(-20,40,-2),(3,3,3),"copper")
    # Copper cartridge press, with unmistakable feed die and articulated lever.
    add("Press_Base",(-23,34,-2),(11,3,13),"iron","panel")
    add("Press_Foot_Copper_Inset",(-23,35.8,-2),(8,1,10),"copper","panel")
    for x in (-27,-19):add("Press_Upright_"+str(x),(x,43,1),(2,15,3),"copper","thread")
    add("Press_Top_Bridge",(-23,50.5,1),(11,3,5),"steel","panel")
    add("Press_Ram",(-23,43,1),(3,12,3),"steelbright","thread")
    add("Press_Die",(-23,39.5,1),(5,3,5),"iron","panel")
    add("Press_Loaded_Cartridge",(-23,37,-2),(2,3,2),"brass","cartridge")
    add("Press_Lever_Pivot",(-29,45,1),(3,4,4),"iron")
    add("Press_Lever",(-29,46,-4),(2,2,12),"steelbright",rotation=(28,0,0))
    add("Press_Lever_Grip",(-29,49,-10),(3,3,5),"wooddark","wood",rotation=(28,0,0))
    add("Press_Powder_Hopper",(-24,54,4),(5,5,5),"copper","panel")
    add("Press_Hopper_Lid",(-24,57,4),(6,1,6),"iron","panel")
    add("Press_Powder_Window",(-24,54,1.3),(3,3,1),"amber",glow=True)
    # Tray of ready cartridges along front-left work edge.
    add("Cartridge_Tray",(-18,34,-10),(9,2,7),"wooddark","panel")
    for i in range(3):
        for j in range(2):
            x,z=-21+i*3,-12+j*3
            add("Tray_Case_"+str(i)+str(j),(x,36,z),(2,3,2),"copper","cartridge")
            add("Tray_Tip_"+str(i)+str(j),(x,38,z),(1,1,1),"brass")
    # Right module: armoured power supply, shielded crystal and calibration rails.
    add("Calibrator_Foot",(24,34,6),(12,3,14),"iron","panel")
    add("Calibrator_Cabinet",(25,40,8),(10,10,11),"steel","panel")
    add("Calibrator_Copper_Lid",(25,46,8),(11,2,12),"copper","panel")
    add("Calibrator_Front_Recess",(25,40,1.9),(8,7,1),"dark","panel")
    for x in (22,25,28):
        add("Calibrator_Charge_Channel_"+str(x),(x,40,1.1),(1,5,1),"cyan",glow=True)
    add("Calibrator_Meter_Rim",(25,45,1),(7,4,2),"brass","panel")
    add("Calibrator_Meter_Face",(25,45,-.1),(5,2,1),"cyan","meter",glow=True)
    add("Calibrator_Knob",(28,36,-.2),(2,2,2),"iron")
    add("Calibrator_Status_Amber",(22,36,.3),(1,1,1),"amber",glow=True)
    for z in (6,10):
        add("Calibrator_Protective_Bar_"+str(z),(18.5,41,z),(2,10,2),"iron")
    add("Calibration_Cell",(18.5,41,8),(3,7,3),"cyan","crystal",glow=True)
    for y in (37,45):add("Calibration_Cell_Cap_"+str(y),(18.5,y,8),(4,2,5),"brass")
    for x in (19,23,27):
        add("Power_Coil_Fin_"+str(x),(x,48,8),(2,3,8),"copper","thread")
    # Cable/power conduit follows back of bench and vanishes into supply.
    add("Power_Conduit_Rear",(14,35,13),(18,2,2),"iron")
    add("Power_Conduit_Elbow",(6,36,13),(3,4,3),"copper")
    add("Power_Conduit_To_Vise",(6,35,9),(2,2,8),"iron")
    # Backboard and toolrail do not wall off the central silhouette.
    for x in (-28,28):
        add("Backboard_Post_"+str(x),(x,41,13.5),(3,24,3),"wooddark","wood")
        add("Backboard_Post_Cap_"+str(x),(x,54,13.5),(4,2,4),"copper")
    for i,y in enumerate((43,48,53)):
        add("Rear_Tool_Plank_"+str(i),(0,y,14),(54,4,2),"walnut","wood")
    add("Top_Tool_Rail",(0,55,13),(56,2,3),"iron","panel")
    for x in range(-24,25,6):b.bolt("Peg_"+str(x),(x,49,12.6),material="brass")
    # A mallet, a long wrench and two drivers; silhouette rather than painted tools.
    add("Hanging_Mallet_Handle",(-13,46,11.6),(2,11,2),"woodedge","wood",rotation=(0,0,-8))
    add("Hanging_Mallet_Head",(-13.6,51,11.6),(8,4,4),"steel","panel",rotation=(0,0,-8))
    add("Hanging_Wrench_Handle",(-3,47,11.4),(2,12,1),"steelbright")
    add("Hanging_Wrench_Neck",(-3,53,11.4),(5,2,2),"steel")
    for x in (-5,-1):add("Hanging_Wrench_Jaw_"+str(x),(x,55,11.4),(1,3,2),"steelbright")
    for i,x in enumerate((6,12)):
        add("Driver_Grip_"+str(i),(x,45.5,11.3),(3,5,2),"red" if i==0 else "leather","cloth")
        add("Driver_Shaft_"+str(i),(x,50,11.3),(1,5,1),"steelbright")
    add("Small_Parts_Cubby",(2,37,13),(15,4,4),"wooddark","panel")
    # Anglepoise tasklamp, warm only at its shielded underside.
    add("Lamp_Foot",(-12,34,10),(7,2,7),"iron","panel")
    add("Lamp_Lower_Arm",(-13,43,10),(2,17,2),"steel",rotation=(0,0,-12))
    add("Lamp_Elbow",(-15,51,10),(4,4,4),"copper")
    add("Lamp_Upper_Arm",(-10,56,6),(2,13,2),"steel",rotation=(0,0,-48))
    add("Lamp_Shade_Crown",(-4,59,6),(8,2,8),"copper","panel")
    add("Lamp_Shade_Brim",(-4,57.5,6),(11,1,10),"iron","panel")
    add("Lamp_Luminous_Underside",(-4,56.8,6),(7,1,6),"amber",glow=True)
    # Loose inspection tools on front-right corner; work top remains visible.
    add("Calipers_Bar",(15,34,-9),(10,1,1),"steelbright",rotation=(0,18,0))
    for x in (11,17):add("Calipers_Jaw_"+str(x),(x,34,-10),(1,1,4),"steelbright")
    add("Oil_Bottle_Base",(28,35,-10),(3,5,3),"iron","panel")
    add("Oil_Bottle_Cap",(28,38,-10),(2,1,2),"copper")
    add("Oil_Bottle_Nozzle",(27,39,-10),(3,1,1),"brass")
    return b

class Atlas:
    def __init__(self):
        self.image=Image.new("RGBA",(SIZE,SIZE));self.cache={};self.x=self.y=1;self.row=0
    def face(self,material,w,h,detail,face):
        key=(material,w,h,detail,face)
        if key in self.cache:return self.cache[key]
        if self.x+w+1>SIZE:self.x=1;self.y+=self.row+2;self.row=0
        if self.y+h+1>SIZE:raise ValueError("Atlas overflow")
        u,v=self.x,self.y;self.x+=w+2;self.row=max(self.row,h)
        base=tuple(bytes.fromhex(COLORS[material][1:]));rng=random.Random(hashlib.sha256(str(key).encode()).digest())
        tile=Image.new("RGBA",(w,h));pix=tile.load();shade={"top":1.10,"bottom":.72,"front":1,"back":.90,"left":.94,"right":1.03}[face]
        if material in ("amber","cyan"):shade=1
        for y in range(h):
            for x in range(w):
                noise=rng.choice((-4,-2,-1,0,0,1,2,4))
                if detail in ("wood","worktop"):noise+=int(7*math.sin((y if face not in ('top','bottom') else x)*.92+math.sin(y*.3)))
                if detail=="cloth":noise+=(3 if (x+y)%3==0 else -2)
                pix[x,y]=tuple(max(0,min(255,int(c*shade+noise))) for c in base)+(255,)
        dr=ImageDraw.Draw(tile);light=tuple(min(255,int(c*shade+20)) for c in base)+(255,);dark=tuple(max(0,int(c*shade-23)) for c in base)+(255,)
        if min(w,h)>=3:
            dr.line((0,0,w-1,0),fill=light);dr.line((0,0,0,h-1),fill=light)
            dr.line((0,h-1,w-1,h-1),fill=dark);dr.line((w-1,1,w-1,h-1),fill=dark)
        if detail=="worktop" and face=='top':
            for x in range(6,w,11):dr.line((x,2,min(w-2,x+5),h-3),fill=dark)
        if detail=="panel" and w>=5 and h>=4:
            dr.rectangle((1,1,w-2,h-2),outline=dark)
            for x in (1,w-2):
                for y in (1,h-2):dr.point((x,y),fill=light)
        if detail=="grid" and face=='top':
            for x in range(2,w-1,4):dr.line((x,1,x,h-2),fill='#49717b')
            for y in range(2,h-1,4):dr.line((1,y,w-2,y),fill='#49717b')
            dr.rectangle((2,2,w-3,h-3),outline='#769b9d')
        if detail=="blueprint" and face=='top':
            dr.line((2,h//2,w-3,h//2),fill='#bdd3c5');dr.rectangle((6,2,11,h-3),outline='#bdd3c5')
            dr.line((w-5,h//2,w-3,h-2),fill='#bdd3c5')
            for x in range(2,w-2,4):dr.point((x,h-2),fill='#88b8b9')
        if detail=="makers" and face in ('front','back'):
            dr.rectangle((1,1,w-2,h-2),fill='#70482f')
            for x in (3,6,9):dr.point((x,1),fill='#e1c991')
        if detail=="label":dr.rectangle((1,0,max(1,w-2),h-1),fill='#88724c')
        if detail=="thread":
            for y in range(1,h,3):dr.line((0,y,w-1,y),fill=dark)
        if detail=="cartridge":
            dr.line((0,max(0,h-2),w-1,max(0,h-2)),fill=dark)
        if detail=='crystal' and min(w,h)>=3:dr.line((1,h-1,w//2,0,w-1,h-1),fill='#d8ffff')
        if detail=='meter' and w>=4:dr.line((1,h-1,w-2,0),fill='#193b4d')
        self.image.paste(tile,(u,v));self.cache[key]=(u,v)
        return u,v

def save():
    b=geometry();atlas=Atlas();nodes=[];elements=[];parts=[]
    for i,p in enumerate(b.parts):
        layout={};faces={};uv={}
        for face,(a,c) in FACES.items():
            w,h=p['size'][a],p['size'][c];u,v=atlas.face(p['material'],w,h,p['detail'],face)
            layout[face]=dict(offset=dict(x=u,y=v),mirror=dict(x=False,y=False),angle=0)
            faces[BBFACES[face]]=dict(uv=[u,v,u+w,v+h],texture=0);uv[face]=[u,v,u+w,v+h]
        shape=dict(type="box",offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(size=vec(p['size'])),
                   textureLayout=layout,unwrapMode="custom",visible=True,doubleSided=False,shadingMode=p['shading_mode'])
        nodes.append(dict(id=str(i+2),name=p['name'],position=vec(p['center']),orientation=quat(p['rotation']),shape=shape,children=[]))
        cube=dict(name=p['name'],uuid=uid(p['name']),type="cube",origin=p['center'],rotation=p['rotation'],autouv=0,
                  faces=faces,shading_mode=p['shading_mode'],shade=p['shading_mode']!='fullbright',double_sided=False)
        cube['from']=[p['center'][a]-p['size'][a]/2 for a in range(3)];cube['to']=[p['center'][a]+p['size'][a]/2 for a in range(3)]
        # Generic Blockbench cubes use world coordinates, while native child
        # nodes are relative to the furniture root. Bake that root translation
        # into the editable source without changing the runtime cube geometry.
        cube['origin']=[p['center'][0]-16,p['center'][1],p['center'][2]]
        cube['from'][0]-=16;cube['to'][0]-=16
        elements.append(cube);parts.append(dict(p,uv=uv))
    none=dict(type="none",offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(isPiece=True),textureLayout={},unwrapMode="custom",visible=True,doubleSided=False,shadingMode="standard")
    # Same furniture root convention as the installed native Weapon Bench.
    model=dict(lod="auto",nodes=[dict(id="1",name="R-Attachment",position=vec((-16,0,0)),orientation=IDENTITY,shape=none,children=nodes)])
    target=ROOT/'Common/Blocks/Benches/RangerSnipers';target.mkdir(parents=True,exist_ok=True)
    modelpath=target/(STEM+'.blockymodel');texturepath=target/(STEM+'.png')
    modelpath.write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8');atlas.image.save(texturepath)
    source=ROOT/'source';source.mkdir(exist_ok=True)
    scene=dict(name=NAME,texture=str(texturepath.resolve()),atlas_size=SIZE,parts=parts,root_translation=[-16,0,0])
    (source/(STEM+'.scene.json')).write_text(json.dumps(scene,indent=2)+'\n',encoding='utf-8')
    project=dict(meta=dict(format_version="4.10",model_format="free",box_uv=False),name=NAME,model_identifier=STEM,
                 resolution=dict(width=SIZE,height=SIZE),elements=elements,
                 outliner=[dict(name="R-Attachment",origin=[-16,0,0],uuid=uid('root'),children=[e['uuid'] for e in elements])],
                 textures=[dict(name=texturepath.name,id="0",internal=True,saved=True,uuid=uid('texture'),
                                source="data:image/png;base64,"+base64.b64encode(texturepath.read_bytes()).decode(),
                                width=SIZE,height=SIZE,uv_width=SIZE,uv_height=SIZE)])
    (source/(STEM+'.bbmodel')).write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
    catalog=dict(name=NAME,original_art=True,model='Blocks/Benches/RangerSnipers/'+modelpath.name,
                 texture='Blocks/Benches/RangerSnipers/'+texturepath.name,icon='Icons/ItemsGenerated/RS_Gunsmith_Bench.png',
                 cube_count=len(parts),atlas_size=[SIZE,SIZE],native_units_per_block=32,
                 root_position=[-16,0,0],front_axis='-Z',worktop_height_model_units=32.5,
                 fullbright_nodes=[p['name'] for p in parts if p['shading_mode']=='fullbright'],
                 integration=dict(no_seat=True,player_animations_id='Block',variant_rotation='NESW',
                                  animation_state='static; do not inherit Weapon_Crafting clip',
                                  suggested_icon_properties=dict(Scale=.37,Translation=[18.7,-15],Rotation=[22.5,45,22.5])))
    (ROOT/'bench-art-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cubes=len(parts),atlas_pixels_used=atlas.y+atlas.row,model=str(modelpath))))

if __name__=='__main__':save()
