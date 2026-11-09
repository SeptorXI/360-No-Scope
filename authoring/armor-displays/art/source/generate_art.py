import os
"""Author original cuboid furniture, pixel atlases and editable Blockbench sources.

All furniture geometry and painted pixels are original. Only the optional empty
equipment skeleton retains the game's named attachment bones, without its mesh.
"""
from pathlib import Path
import base64, hashlib, itertools, json, math, random, uuid, zipfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ATLAS = 512
ROOT_OFFSET = [-16, 0, 0]
PALETTE = {
    'walnut':'#705039','edge':'#a17b50','darkwood':'#453225',
    'iron':'#29343b','rivet':'#a49b86','brass':'#c1a269',
    'steel':'#657781','bright':'#a2b6bc','gunmetal':'#33444d',
    'rubber':'#192b31','leather':'#6d5140','blue':'#476a79',
    'cyan':'#80c7ce','ink':'#15242a',
}
FACES = {'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}
BBFACES = dict(front='north',back='south',left='west',right='east',top='up',bottom='down')
IDENTITY = dict(x=0,y=0,z=0,w=1)

def vec(v): return dict(zip('xyz', v))
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
def uid(name): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'steven-armor-displays/'+name))
def quaternion(rotation):
    q=IDENTITY.copy()
    axes=[(a,v) for a,v in zip('xyz',rotation) if v]
    assert len(axes)<=1
    if axes:
        axis,angle=axes[0]; q[axis]=math.sin(math.radians(angle/2)); q['w']=math.cos(math.radians(angle/2))
    return q

class Geometry:
    def __init__(self): self.parts=[]
    def box(self,name,center,size,material,detail='',rotation=(0,0,0)):
        assert all(isinstance(v,int) and v>0 for v in size),(name,size)
        self.parts.append(dict(name=name,center=list(center),size=list(size),material=material,
                               detail=detail,rotation=list(rotation),shading_mode='standard'))
    def rivet(self,name,center,material='rivet'): self.box(name,center,(1,1,1),material)

def stand(metal):
    g=Geometry(); b=g.box
    if not metal:
        for i,x in enumerate((-10,0,10)): b(f'Foot_Plank_{i}',(x,2,0),(9,4,24),'walnut','wood')
        for z in (-12,12):
            b(f'Forged_Base_Rim_{z}',(0,2,z),(29,4,2),'iron','metal')
            for x in (-11,11): g.rivet(f'Base_Rivet_{z}_{x}',(x,3,z-1.1),'brass')
        for x in (-14,14):b(f'Base_End_Cap_{x}',(x,2,0),(2,4,24),'iron','metal')
        b('Square_Pedestal_Socket',(0,5,3),(10,4,10),'darkwood','wood')
        b('Socket_Iron_Collar',(0,7,3),(8,2,8),'iron','metal')
        b('Main_Timber_Spine',(0,28,3),(4,42,4),'walnut','wood')
        for y in (12,29,43):
            b(f'Spine_Collar_{y}',(0,y,3),(6,3,6),'iron','metal')
            g.rivet(f'Spine_Front_Rivet_{y}',(0,y,-.1),'brass')
        b('Hip_Hanger',(0,28,2),(20,3,4),'edge','wood')
        b('Left_Trouser_Support',(-7,22,2),(3,12,4),'walnut','wood')
        b('Right_Trouser_Support',(7,22,2),(3,12,4),'walnut','wood')
        b('Shoulder_Crossbar',(0,47,2),(22,4,5),'edge','wood')
        for side in (-1,1):
            b(f'Shoulder_Tip_{side}',(side*12,45.8,2),(7,4,5),'walnut','wood',rotation=(0,0,-side*20))
            b(f'Shoulder_Leather_Pad_{side}',(side*10,49,2),(8,1,6),'leather','leather')
            b(f'Sleeve_Peg_{side}',(side*13,41,2),(3,8,4),'walnut','wood')
            g.rivet(f'Shoulder_Pin_{side}',(side*10,47,-1),'brass')
        b('Neck_Support',(0,53,2),(4,9,4),'walnut','wood')
        b('Helmet_Cushion_Base',(0,58,2),(8,2,8),'darkwood','wood')
        b('Helmet_Cushion',(0,61,2),(6,4,6),'leather','leather')
        b('Makers_Plate',(0,4.2,-7),(9,1,5),'brass','label')
    else:
        b('Weighted_Octagonal_Base',(0,1.5,0),(24,3,24),'gunmetal','metal')
        b('Base_Top_Slab',(0,3.5,0),(22,1,22),'steel','metal')
        for x in (-10,10):
            for z in (-10,10):
                b(f'Rubber_Foot_{x}_{z}',(x,.5,z),(4,1,4),'rubber','rubber')
                g.rivet(f'Base_Captive_Bolt_{x}_{z}',(x,4.2,z),'bright')
        b('Telescoping_Socket',(0,8,3),(8,8,8),'steel','metal')
        b('Socket_Dark_Face',(0,8,-1.1),(5,5,1),'gunmetal','metal')
        b('Socket_Adjust_Knob',(3.9,9,3),(3,3,4),'rubber','rubber')
        b('Lower_Telescopic_Post',(0,24,3),(4,28,4),'gunmetal','metal')
        b('Upper_Telescopic_Post',(0,43,3),(3,20,3),'bright','metal')
        b('Post_Lock_Collar',(0,35,3),(6,3,6),'steel','metal')
        b('Post_Collar_Latch',(0,35,-.8),(4,2,2),'rubber','rubber')
        b('Hip_Clamp',(0,28,2),(20,3,4),'gunmetal','metal')
        for side in (-1,1):
            b(f'Hip_Pad_{side}',(side*7,30,2),(6,1,5),'rubber','rubber')
            b(f'Shoulder_Arm_{side}',(side*7,47,2),(14,3,4),'steel','metal',rotation=(0,0,-side*9))
            b(f'Shoulder_End_{side}',(side*13,45.5,2),(3,6,5),'gunmetal','metal')
            b(f'Shoulder_Rubber_{side}',(side*9,49,2),(10,1,6),'rubber','rubber',rotation=(0,0,-side*9))
            g.rivet(f'Shoulder_Captive_Bolt_{side}',(side*10,47,-1),'bright')
            b(f'Trouser_Rail_{side}',(side*7,22,2),(2,11,3),'steel','metal')
        b('Helmet_Neck',(0,55,2),(3,10,3),'bright','metal')
        b('Helmet_Pad_Tray',(0,60,2),(9,2,8),'gunmetal','metal')
        b('Helmet_Rubber_Pad',(0,62,2),(7,2,6),'rubber','rubber')
        b('Base_Status_Inset',(0,4.2,-7),(8,1,4),'rubber','rubber')
        b('Base_Blue_Accent',(0,4.8,-7),(6,1,1),'blue')
    return g

def holder(metal):
    g=Geometry(); b=g.box
    if not metal:
        b('Carved_Wall_Plaque',(0,12,14),(28,20,4),'walnut','wood')
        b('Plaque_Crown',(0,23,14),(22,2,4),'edge','wood')
        b('Plaque_Lower_Lip',(0,1,14),(22,2,4),'darkwood','wood')
        for x in (-14,14):
            b(f'Plaque_End_Strap_{x}',(x,12,13.5),(2,22,5),'iron','metal')
            for y in (5,19):g.rivet(f'Strap_Rivet_{x}_{y}',(x,y,10.6),'brass')
        b('Plaque_Center_Plate',(0,17,11.5),(10,3,1),'brass','label')
    else:
        b('Steel_Mounting_Plate',(0,12,14.5),(28,24,3),'gunmetal','metal')
        b('Recessed_Panel',(0,12,12.5),(24,18,1),'steel','metal')
        for x in (-13,13):
            b(f'Raised_Edge_{x}',(x,12,12.5),(2,24,3),'steel','metal')
            for y in (3,21):g.rivet(f'Captive_Bolt_{x}_{y}',(x,y,10.6),'bright')
        b('Panel_Blue_Marker',(0,20,11.6),(10,1,1),'blue')
        for x in (-7,-3,1,5):b(f'Index_Hole_{x}',(x,6,11.6),(1,1,1),'ink')
    cradle(g,0,metal,halfwidth=9,level=10)
    return g

def cradle(g,row,metal,halfwidth,level):
    iron='steel' if metal else 'iron'; pad='rubber' if metal else 'leather'
    # The center saddle supports short handguns/knives without inflating their
    # actual native size; the outer saddles continue to support long weapons.
    for x in (-halfwidth,0,halfwidth):
        suffix=f'{row}_{x}'
        g.box('Hook_Wall_Bracket_'+suffix,(x,level+1,11),(4,7,3),iron,'metal')
        g.box('Hook_Seat_'+suffix,(x,level-1,7.5),(4,3,9),iron,'metal')
        g.box('Hook_Padded_Seat_'+suffix,(x,level+.8,7.5),(5,1,6),pad,pad)
        g.box('Hook_Retaining_Lip_'+suffix,(x,level+1,3.5),(4,5,2),iron,'metal')
        g.box('Hook_Lip_Pad_'+suffix,(x,level+1,4.8),(4,3,1),pad,pad)
        g.rivet('Hook_Bolt_'+suffix,(x,level+3,9.1),'bright' if metal else 'brass')

def rack(metal):
    g=Geometry(); b=g.box
    if not metal:
        for i,y in enumerate(range(5,60,10)):
            b(f'Walnut_Backboard_Slat_{i}',(0,y,14),(58,9,4),'walnut','wood')
            if i in (0,5):b(f'Slat_Edge_Trim_{i}',(0,y,11.6),(55,2,1),'edge','wood')
        for x in (-29,29):
            b(f'Forged_Upright_{x}',(x,30,13.5),(4,60,5),'iron','metal')
            for y in (5,22,39,55):g.rivet(f'Upright_Bolt_{x}_{y}',(x,y,10.6),'brass')
        for y in (1,59):b(f'Rack_Rim_{y}',(0,y,13),(58,2,6),'darkwood','wood')
        b('Makers_Plaque',(0,56,11),(13,3,1),'brass','label')
    else:
        b('Reinforced_Back_Panel',(0,30,14.5),(58,58,3),'gunmetal','metal')
        b('Recessed_Pegboard',(0,30,12.6),(54,54,1),'steel','metal')
        for x in (-29,29):
            b(f'Extruded_Side_Rail_{x}',(x,30,12.5),(4,60,7),'gunmetal','metal')
            b(f'Rail_Highlight_{x}',(x+(-1 if x<0 else 1),30,8.6),(1,54,1),'bright')
            for y in (5,55):g.rivet(f'Rail_Captive_Bolt_{x}_{y}',(x,y,8.6),'bright')
        for y in (1,59):b(f'Extruded_End_Rail_{y}',(0,y,12.5),(58,2,7),'gunmetal','metal')
        # Physical low-profile inserts complement the painted perforated panel.
        for y in (7,25,43):
            for x in range(-24,25,6):b(f'Pegboard_Hole_{x}_{y}',(x,y,11.7),(2,2,1),'ink')
        b('Upper_Identification_Strip',(0,56,11.4),(24,3,1),'rubber','rubber')
        for x in (-8,-4,0,4,8):b(f'Index_Tick_{x}',(x,56,10.8),(1,1,1),'blue')
    for i,y in enumerate((10,28,46)):
        cradle(g,i,metal,halfwidth=18,level=y)
        if metal:
            b(f'Slot_Label_{i}',(-24,y-3,11.5),(5,3,1),'rubber','rubber')
            for n in range(i+1):b(f'Slot_Tick_{i}_{n}',(-25+n*2,y-3,10.9),(1,1,1),'bright')
        else:
            b(f'Slot_Label_{i}',(-25,y+1,11.4),(3,4,1),'brass','label')
    return g

class PixelAtlas:
    def __init__(self):
        self.image=Image.new('RGBA',(ATLAS,ATLAS));self.cache={};self.x=self.y=1;self.row=0
    def face(self,mat,w,h,detail,face):
        key=(mat,w,h,detail,face)
        if key in self.cache:return self.cache[key]
        if self.x+w+1>ATLAS:self.x=1;self.y+=self.row+2;self.row=0
        if self.y+h+1>ATLAS:raise ValueError('Atlas overflow')
        u,v=self.x,self.y;self.x+=w+2;self.row=max(self.row,h)
        rgb=tuple(bytes.fromhex(PALETTE[mat][1:]));rng=random.Random(hashlib.sha256(str(key).encode()).digest())
        shade=dict(top=1.10,bottom=.75,front=1,back=.91,left=.94,right=1.04)[face]
        tile=Image.new('RGBA',(w,h)); pix=tile.load()
        for y in range(h):
            for x in range(w):
                noise=rng.choice((-3,-2,0,0,0,1,2,3))
                if detail=='wood':noise+=int(8*math.sin((x if face in ('top','bottom') else y)*.7+math.sin(y*.4)))
                if detail in ('rubber','leather'):noise+=2 if (x+y)%3==0 else -1
                pix[x,y]=tuple(max(0,min(255,int(c*shade+noise))) for c in rgb)+(255,)
        d=ImageDraw.Draw(tile)
        light=tuple(min(255,int(c*shade+19)) for c in rgb)+(255,)
        dark=tuple(max(0,int(c*shade-20)) for c in rgb)+(255,)
        if min(w,h)>=3:
            d.line((0,0,w-1,0),fill=light);d.line((0,0,0,h-1),fill=light)
            d.line((0,h-1,w-1,h-1),fill=dark);d.line((w-1,0,w-1,h-1),fill=dark)
        if detail=='metal' and min(w,h)>=6:
            d.rectangle((1,1,w-2,h-2),outline=dark)
        if mat=='steel' and w>=45 and h>=45:
            for y in range(3,h-2,6):
                for x in range(3,w-2,6):d.rectangle((x,y,x+1,y+1),fill=PALETTE['ink'])
        if detail=='label' and w>=5:
            for x in range(2,w-2,3):d.line((x,1,x,max(1,h-2)),fill=dark)
        self.image.paste(tile,(u,v));self.cache[key]=(u,v)
        return u,v

def measured_bounds(parts):
    pts=[]
    for p in parts:
        q=quaternion(p['rotation']); u=[q[a] for a in 'xyz'];s=q['w']
        for signs in itertools.product((-.5,.5),repeat=3):
            v=[p['size'][i]*signs[i] for i in range(3)];dot=sum(a*b for a,b in zip(u,v));uu=sum(a*a for a in u)
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            pts.append([2*dot*u[i]+(s*s-uu)*v[i]+2*s*cross[i]+p['center'][i] for i in range(3)])
    return dict(min=[min(p[i] for p in pts) for i in range(3)],max=[max(p[i] for p in pts) for i in range(3)])

def export(stem,name,style,kind,geometry):
    atlas=PixelAtlas();nodes=[];elements=[];parts=[]
    for i,p in enumerate(geometry.parts):
        layout={};bbfaces={};uv={}
        for face,(a,b) in FACES.items():
            w,h=p['size'][a],p['size'][b];u,v=atlas.face(p['material'],w,h,p['detail'],face)
            layout[face]=dict(offset=dict(x=u,y=v),mirror=dict(x=False,y=False),angle=0)
            bbfaces[BBFACES[face]]=dict(uv=[u,v,u+w,v+h],texture=0);uv[face]=[u,v,u+w,v+h]
        shape=dict(type='box',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(size=vec(p['size'])),
                   textureLayout=layout,unwrapMode='custom',visible=True,doubleSided=False,shadingMode='standard')
        nodes.append(dict(id=str(i+2),name=p['name'],position=vec(p['center']),orientation=quaternion(p['rotation']),shape=shape,children=[]))
        cube=dict(name=p['name'],uuid=uid(stem+'/'+p['name']),type='cube',origin=[p['center'][a]+ROOT_OFFSET[a] for a in range(3)],
                  rotation=p['rotation'],autouv=0,faces=bbfaces,shade=True,double_sided=False)
        cube['from']=[p['center'][a]-p['size'][a]/2+ROOT_OFFSET[a] for a in range(3)]
        cube['to']=[p['center'][a]+p['size'][a]/2+ROOT_OFFSET[a] for a in range(3)]
        elements.append(cube);parts.append(dict(p,uv=uv))
    none=dict(type='none',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(isPiece=True),textureLayout={},unwrapMode='custom',visible=True,doubleSided=False,shadingMode='standard')
    model=dict(lod='auto',nodes=[dict(id='1',name='R-Attachment',position=vec(ROOT_OFFSET),orientation=IDENTITY,shape=none,children=nodes)])
    relative='Blocks/ArmorDisplays/'+stem
    modelpath=ROOT/'Common'/(relative+'.blockymodel');texturepath=ROOT/'Common'/(relative+'.png')
    dump(modelpath,model);atlas.image.save(texturepath)
    dump(ROOT/'source'/(stem+'.scene.json'),dict(name=name,stem=stem,style=style,kind=kind,texture=str(texturepath.resolve()),
         atlas_size=ATLAS,parts=parts,root_translation=ROOT_OFFSET,native_units_per_block=32))
    dump(ROOT/'source'/(stem+'.bbmodel'),dict(meta=dict(format_version='4.10',model_format='free',box_uv=False),name=name,
        model_identifier=stem,resolution=dict(width=ATLAS,height=ATLAS),elements=elements,
        outliner=[dict(name='R-Attachment',origin=ROOT_OFFSET,uuid=uid(stem+'/root'),children=[e['uuid'] for e in elements])],
        textures=[dict(name=texturepath.name,id='0',internal=True,saved=True,uuid=uid(stem+'/texture'),
            source='data:image/png;base64,'+base64.b64encode(texturepath.read_bytes()).decode(),width=ATLAS,height=ATLAS,uv_width=ATLAS,uv_height=ATLAS)]))
    anchors={'stand':[[0,4,0]],'holder':[[0,12,8]],'rack':[[0,12,7],[0,30,7],[0,48,7]]}[kind]
    bounds=measured_bounds(parts)
    # Collision boxes use the conventional block-center frame, matching native
    # furniture hitboxes; R-Attachment's item attachment translation is separate.
    boxes={'stand':[([-15,0,-13],[15,8,13]),([-14,8,-2],[14,64,7])],
           'holder':[([-15,0,2],[15,24,16])], 'rack':[([-31,0,2],[31,60,16])]}[kind]
    hitbox={'Boxes':[{'Min':dict(zip('XYZ',[v/32 for v in lo])),'Max':dict(zip('XYZ',[v/32 for v in hi]))} for lo,hi in boxes]}
    hitboxpath=f'Server/Item/Block/Hitboxes/ArmorDisplays/{stem}.json';dump(ROOT/hitboxpath,hitbox)
    return dict(id=stem,name=name,style=style,kind=kind,model=relative+'.blockymodel',texture=relative+'.png',
                icon=f'Icons/ItemsGenerated/{stem}.png',hitboxType=stem,hitboxPath=hitboxpath,hitbox=hitbox,
                rootPosition=ROOT_OFFSET,frontAxis='-Z',unitsPerBlock=32,static=True,boundsCenteredModelUnits=bounds,
                rootAdjustedBoundsModelUnits={k:[v+ROOT_OFFSET[i] for i,v in enumerate(row)] for k,row in bounds.items()},
                dimensionsBlocks=[(b-a)/32 for a,b in zip(bounds['min'],bounds['max'])],
                displayAnchorsModelUnits=anchors,displayAnchorsBlocks=[[v/32 for v in row] for row in anchors],
                entityAnchorsBeforeRotationBlocks=[[(row[0]-16)/32,row[1]/32,row[2]/32] for row in anchors],
                anchorFrame='geometry coordinates before R-Attachment; entity world = block origin + (0.5,0,0.5) + yawRotate((anchor+rootPosition)/32)',
                wallBackFaceModelZ=16 if kind!='stand' else None,cubeCount=len(parts),atlasSize=[ATLAS,ATLAS],
                iconProperties=dict(Scale=.6,Translation=[16,-12],Rotation=[22.5,45,0]))

def empty_equipment_skeleton():
    with zipfile.ZipFile(os.environ['HYTALE_ASSETS_ZIP']) as z:
        source=json.loads(z.read('Common/NPC/MISC/Mannequin/Models/Model.blockymodel'))
    count=0
    def strip(node):
        nonlocal count
        count+=1
        node['shape']=dict(type='none',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(isPiece=True),
                           textureLayout={},unwrapMode='custom',visible=True,doubleSided=False,shadingMode='standard')
        for c in node.get('children',[]):strip(c)
    for node in source['nodes']:strip(node)
    source['lod']='auto'
    model='NPC/ArmorDisplays/Equipment_Mannequin.blockymodel'
    texture='NPC/ArmorDisplays/Equipment_Mannequin.png'
    dump(ROOT/'Common'/model,source)
    Image.new('RGBA',(2,2),(255,255,255,0)).save(ROOT/'Common'/texture)
    asset=dict(Parent='Player',Model=model,Texture=texture,EyeHeight=1.6,MinScale=1,MaxScale=1,DefaultAttachments=[],
               HitBox=dict(Min=dict(X=-.3,Y=0,Z=-.3),Max=dict(X=.3,Y=1.8,Z=.3)))
    path='Server/Models/ArmorDisplays/AD_Equipment_Mannequin.json';dump(ROOT/path,asset)
    return dict(id='AD_Equipment_Mannequin',model=model,texture=texture,assetPath=path,boneCount=count,
                provenance='Native Mannequin named skeleton and pivots only; every visible mesh removed; no native texture copied')

def main():
    assets=[]
    for metal in (False,True):
        style='Metal' if metal else 'Wood'
        prefix='Metal' if metal else 'Wood and Iron'
        for kind,stem,name,build in [('stand','Armor_Stand','Armor Stand',stand),('holder','Wall_Holder','Wall Weapon Holder',holder),('rack','Wall_Rack','Three-Weapon Wall Rack',rack)]:
            assets.append(export(f'AD_{stem}_{style}',f'{prefix} {name}',style,kind,build(metal)))
    contract=dict(schemaVersion=1,unitsPerBlock=32,frontAxis='-Z',wallBackAxis='+Z',rootPosition=ROOT_OFFSET,
                  furnitureOriginalArt=True,assets=assets,equipmentSkeleton=empty_equipment_skeleton(),
                  notes=['Furniture assets contain no example weapons or equipped armor.',
                         'DisplayAnchorsModelUnits use centered source geometry. EntityAnchorsBeforeRotationBlocks include R-Attachment X=-16. Rotate those about block center, then add block origin+(0.5,0,0.5).',
                         'Weapons lie horizontally along local X; runtime must orient each actual item model to suit its source grip/origin.',
                         'Wall racks occupy about two blocks horizontally and vertically; backing wall/support checks belong to runtime.',
                         'Empty equipment skeleton is attachment scaffolding, never an independent item owner.'])
    dump(ROOT/'art-contract.json',contract)
    print(json.dumps(dict(assets=len(assets),cubes=sum(a['cubeCount'] for a in assets),equipmentBones=contract['equipmentSkeleton']['boneCount'])))

if __name__=='__main__':main()
