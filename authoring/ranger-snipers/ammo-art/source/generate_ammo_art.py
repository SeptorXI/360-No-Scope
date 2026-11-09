"""Nine original cube ammunition designs. Python + Pillow, no external art input."""
from pathlib import Path
import base64,hashlib,json,math,random,uuid
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SIZE=256
FACES={'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}
BB_FACES={'front':'south','back':'north','left':'west','right':'east','top':'up','bottom':'down'}

THEMES=[
 dict(index=1,name='Wildwood cartridge',rifle='Wildwood Surveyor',rifle_id='Weapon_Crossbow_Wildwood_Surveyor',region='Emerald Wilds',
      colors=dict(body='#9a7044',light='#d6a95a',dark='#3c3c39',trim='#be7950',tip='#737e82',glow='#bd8747',inlay='#526b41',pale='#d6c1a0')),
 dict(index=2,name='Dunewatch cartridge',rifle='Dunewatch Longshot',rifle_id='Weapon_Crossbow_Dunewatch_Longshot',region='Howling Sands',
      colors=dict(body='#b1955b',light='#dcca8f',dark='#494c40',trim='#728a5c',tip='#7a8b69',glow='#c6ad68',inlay='#5a624e',pale='#e7dcb4')),
 dict(index=3,name='Frostline cartridge',rifle='Frostline Sentinel',rifle_id='Weapon_Crossbow_Frostline_Sentinel',region='Whisperfrost',
      colors=dict(body='#34688e',light='#8eafc2',dark='#263e54',trim='#b4c2cc',tip='#c4dfed',glow='#76b7d6',inlay='#467c9b',pale='#e4eff4')),
 dict(index=4,name='Mournhollow reliquary round',rifle='Mournhollow Epitaph',rifle_id='Weapon_Crossbow_Mournhollow_Epitaph',region='Mournhollow',
      colors=dict(body='#3e3749',light='#83778e',dark='#242630',trim='#b1a7a1',tip='#a9a7b1',glow='#a47cce',inlay='#705085',pale='#d5c9b1')),
 dict(index=5,name='Deepworks rail slug',rifle="Gobliterator's Requiem",rifle_id='Weapon_Crossbow_Deepworks_Railspike',region='Deepworks',
      colors=dict(body='#4b5254',light='#9b9d94',dark='#242c2c',trim='#ba8251',tip='#7c878b',glow='#f4b35c',inlay='#6be0eb',pale='#d9c699')),
 dict(index=6,name='Luminia prism cartridge',rifle='Dawnpiercer, Last Light of Luminia',rifle_id='Weapon_Crossbow_Luminia_Dawnpiercer',region='Luminia',
      colors=dict(body='#d2dce3',light='#f3efd4',dark='#39445b',trim='#c6a358',tip='#e2edf3',glow='#8fe9f4',inlay='#b48aef',pale='#f1ead8')),
 dict(index=7,name='Nameless caged round',rifle='Nameless Covenant',rifle_id='Weapon_Crossbow_Nameless_Covenant',region='Dungeon of Fear',
      colors=dict(body='#45434e',light='#95959f',dark='#1f2931',trim='#b5b7bd',tip='#8e8c9c',glow='#a479cf',inlay='#8e4558',pale='#d7d6d2')),
 dict(index=8,name='Fullmetal crystal sabot',rifle='Labyrinth Threadkeeper',rifle_id='Weapon_Crossbow_Labyrinth_Threadkeeper',region='Fullmetal Labyrinth',
      colors=dict(body='#4b5b67',light='#c4d1d8',dark='#202d36',trim='#96aab9',tip='#7cdeef',glow='#4dcbe3',inlay='#527486',pale='#e3edf0')),
 dict(index=9,name='Skybound relic cartridge',rifle='Skybound Farwatch',rifle_id='Weapon_Crossbow_Skybound_Farwatch',region='Tritale',
      colors=dict(body='#644b35',light='#987046',dark='#354753',trim='#5b89a5',tip='#a3c9d9',glow='#8acb7a',inlay='#ac4a3b',pale='#d8cfac')),
]

NAMES=[
 ('Wayfinder Cartridges','RS_Ammo_Wayfinder'),
 ('Sirocco Longshot Rounds','RS_Ammo_Sirocco'),
 ('Rimeglass Match Rounds','RS_Ammo_Rimeglass'),
 ('Gravelight Reliquary Rounds','RS_Ammo_Gravelight'),
 ('Gobliterator Siege Slugs','RS_Ammo_SiegeSlug'),
 ('Firstlight Prism Cartridges','RS_Ammo_Firstlight'),
 ('Penance Rounds','RS_Ammo_Penance'),
 ('Threadline Sabots','RS_Ammo_Threadline'),
 ('Skyglass Scout Cartridges','RS_Ammo_Skyglass'),
]
for theme,(name,ammo_id) in zip(THEMES,NAMES):theme.update(name=name,ammo_id=ammo_id)


def vec(v):return dict(zip('xyz',v))
def uid(v):return str(uuid.uuid5(uuid.NAMESPACE_URL,'original-ranger-ammunition/'+v))
def quat(rotation):
    axes=[(i,a) for i,a in enumerate(rotation) if a];assert len(axes)<=1
    q=dict(x=0,y=0,z=0,w=1)
    if axes:
        i,a=axes[0];q['xyz'[i]]=round(math.sin(math.radians(a/2)),8);q['w']=round(math.cos(math.radians(a/2)),8)
    return q


class Ammo:
    def __init__(self,t):self.theme=t;self.parts=[]
    def box(self,name,center,size,material='body',rotation=(0,0,0),detail='',bright=False):
        assert all(v>0 and int(v)==v for v in size)
        self.parts.append(dict(name=name,center=list(center),size=list(size),material=material,rotation=list(rotation),detail=detail,shading_mode='fullbright' if bright else 'flat'))
    def pair(self,name,center,size,material,separation,axis=0,rotation=(0,0,0),detail='',bright=False):
        for sign in (-1,1):
            c=list(center);c[axis]+=sign*separation
            self.box(name+('_L' if sign<0 else '_R'),c,size,material,rotation,detail,bright)
    def body(self,name,center,height,width=7,material='body',detail='metal'):
        x,y,z=center;self.box(name,center,(width-2,height,width),material,detail=detail)
        self.box(name+'_Facets',center,(width,height,width-2),material,detail=detail)
    def band(self,name,y,width=8,material='trim',height=2,bright=False):
        self.box(name,(0,y,0),(width,height,width-2),material,bright=bright)
        self.box(name+'_Corners',(0,y,0),(width-2,height,width),material,bright=bright)


def build(t):
    a=Ammo(t);i=t['index']
    if i==1:
        a.body('Brass_Case',(0,-1,0),16,7,detail='grain')
        a.band('Copper_Rim',-9,9,height=2);a.band('Copper_Shoulder',7,7,height=2)
        a.body('Narrow_Neck',(0,9,0),4,5,'light')
        a.body('Ballistic_Tip',(0,13,0),5,4,'tip')
        a.box('Tip_Point',(0,16,0),(2,2,2),'tip')
        a.box('Primer',(0,-10.6,0),(3,1,3),'dark',detail='primer')
        a.pair('Field_Stamp',(0,-2,0),(4,5,1),'inlay',3.6,axis=2,detail='stamp')
        a.band('Case_Cannelure',-5,7,'dark',height=1)
    elif i==2:
        a.body('Long_Sand_Case',(0,1,0),22,6,detail='grain')
        a.band('Wide_Extractor_Rim',-10,9,'dark',height=2)
        a.band('Thorium_Lower_Ring',-7,7,'trim',height=2)
        a.band('Sealed_Shoulder',12,7,'light',height=2)
        a.body('Thorium_Neck',(0,15,0),4,4,'trim')
        a.box('Long_Penetrator',(0,19,0),(3,5,3),'tip')
        a.box('Sharp_Tip',(0,22,0),(1,2,1),'tip')
        a.pair('Side_Identification_Stripe',(0,1,0),(2,12,1),'pale',3.15,axis=2)
        a.pair('Sand_Seal_Lug',(0,10,0),(2,4,2),'dark',3.5)
        a.box('Base_Primer',(0,-11.4,0),(3,1,3),'trim',detail='primer')
    elif i==3:
        a.body('Cobalt_Case',(0,0,0),15,8,detail='metal')
        a.band('Silver_Base',-8,10,'trim',height=2)
        a.band('Silver_Neck',8,8,'trim',height=2)
        a.body('Frost_Pale_Tip',(0,12,0),6,6,'tip')
        a.box('Pale_Point',(0,16,0),(3,3,3),'pale')
        for k in range(3):
            a.pair('Cobalt_Tip_Flute_'+str(k),(0,10+k*2,0),(2,1,1),'inlay',3.2,axis=2)
        a.pair('Cold_Silver_Stabilizer',(0,-3,0),(2,10,3),'trim',4.3,rotation=(0,0,8))
        a.pair('Cobalt_ID',(0,1,0),(4,5,1),'light',4.1,axis=2,detail='frost')
        a.box('Primer',(0,-9.6,0),(3,1,3),'dark',detail='primer')
    elif i==4:
        a.body('Blackiron_Reliquary',(0,0,0),18,9,'dark')
        a.box('Violet_Sealed_Core',(0,1,-4.8),(6,10,1),'glow',detail='energy')
        a.pair('Bone_Cage',(0,0,-5.5),(2,16,2),'pale',4.2,rotation=(0,0,9))
        a.box('Bone_Upper_Seal',(0,8,-5.1),(10,3,2),'trim',detail='rune')
        a.box('Bone_Lower_Seal',(0,-7,-5.1),(10,3,2),'pale')
        a.band('Iron_Extractor',-10,11,'body',height=3)
        a.body('Bone_Projectile',(0,12,0),7,6,'pale')
        a.box('Iron_Nose',(0,16,0),(3,3,3),'tip')
        a.box('Prayer_Stud',(0,8,-6.5),(3,3,1),'glow',rotation=(0,0,45))
        a.pair('Bone_Rear_Brace',(0,1,0),(2,12,1),'trim',4.6,axis=2)
    elif i==5:
        a.body('Forged_Rail_Slug',(0,0,0),15,11,'body',detail='metal')
        a.band('Industrial_Base',-9,14,'dark',height=4)
        a.body('Steel_Penetrator',(0,12,0),9,8,'tip')
        a.box('Penetrator_Head',(0,17,0),(5,3,5),'light')
        for k,y in enumerate((-4,1,6)):
            a.band('Copper_Coil_'+str(k),y,12,'trim',height=2)
            a.pair('Charged_Winding_'+str(k),(0,y,0),(3,2,8),'glow',5.7,bright=True)
        a.box('Cyan_Rail_Insert',(0,1,-5.8),(4,11,1),'inlay',detail='energy',bright=True)
        a.pair('Black_Retention_Bar',(0,0,-6.4),(2,15,2),'dark',4.1)
        a.pair('Base_Fin',(0,-7,0),(3,7,4),'body',7.1,rotation=(0,0,12))
        a.box('Primer_Block',(0,-11.5,0),(5,1,5),'trim',detail='primer')
    elif i==6:
        a.body('Prisma_Optical_Cartridge',(0,0,0),20,8,'dark')
        a.pair('Ivory_Casing_Rails',(0,1,0),(3,21,5),'body',4.6)
        a.pair('Gold_Edge_Rails',(0,1,0),(1,18,6),'trim',6.2)
        a.band('Gold_Base',-11,12,'trim',height=3)
        a.band('Gold_Lens_Collar',12,11,'trim',height=3)
        a.box('Violet_Prism_Core',(0,0,-4.6),(5,12,2),'inlay',detail='crystal',bright=True)
        a.pair('Cyan_Channel',(0,0,0),(2,16,1),'glow',4.1,axis=2,detail='energy',bright=True)
        a.body('Focusing_Lens_Housing',(0,15,0),3,8,'body')
        a.box('Cyan_Optical_Lens',(0,17,0),(6,1,6),'glow',detail='lens',bright=True)
        a.pair('Lens_Tabs',(0,15,0),(2,5,3),'pale',4.7)
        a.box('Violet_Base_Contact',(0,-13,0),(4,1,4),'inlay',bright=True)
    elif i==7:
        a.body('DarkSilver_Case',(0,-1,0),17,8,'body')
        a.band('Blackiron_Base',-10,11,'dark',height=3)
        a.box('Violet_Eye_Chamber',(0,1,-4.6),(9,9,2),'glow',detail='eye')
        a.pair('Silver_Cage_Pillar',(0,1,-6),(2,13,2),'trim',5,rotation=(0,0,10))
        a.pair('Blackiron_Crown',(0,8,-4.5),(6,2,3),'dark',2.5,rotation=(0,0,22))
        a.box('Cage_Silver_Sill',(0,-6,-5.5),(11,2,2),'trim')
        a.box('Crimson_Crown_Seal',(0,10,-5.7),(3,3,1),'inlay',rotation=(0,0,45))
        a.body('DarkSilver_Penetrator',(0,12,0),6,5,'tip')
        a.box('Point',(0,16,0),(2,3,2),'trim')
        a.band('Red_Base_Binding',-7,9,'inlay',height=1)
        a.box('Silver_Primer',(0,-12,0),(4,1,4),'pale',detail='rune')
    elif i==8:
        a.body('Black_Sabot_Base',(0,-5,0),12,10,'dark')
        a.band('Chrome_Extractor',-12,13,'trim',height=3)
        a.pair('Angular_Sabot_Petals',(0,3,0),(3,15,6),'body',5.2,rotation=(0,0,14))
        a.pair('Chrome_Petal_Edge',(0,4,0),(1,13,7),'light',6.3,rotation=(0,0,14))
        a.box('Cyan_Crystal_Penetrator',(0,9,0),(5,14,5),'tip',rotation=(0,45,0),detail='crystal')
        a.box('Crystal_Point',(0,17,0),(3,3,3),'glow',rotation=(0,45,0))
        a.pair('Maze_Plate',(0,-4,0),(7,7,1),'body',5.2,axis=2,detail='maze')
        a.box('Sabot_Release_Seam',(0,-1,-5.8),(7,1,1),'glow')
        a.box('Dark_Primer',(0,-14,0),(4,1,4),'dark',detail='primer')
    else:
        a.body('Darkwood_Cartridge',(0,-1,0),16,8,'body',detail='wood')
        a.band('Blue_Metal_Base',-10,11,'trim',height=3)
        for k,y in enumerate((-6,0,6)):a.band('Red_Binding_'+str(k),y,9,'inlay',height=2)
        a.body('Blue_Metal_Shoulder',(0,9,0),4,7,'trim')
        a.body('Blue_Tipped_Projectile',(0,14,0),6,5,'tip')
        a.box('Point',(0,18,0),(2,3,2),'tip')
        a.box('Ivory_Relic_Frame',(0,2,-4.8),(7,9,2),'pale',detail='carved')
        a.box('Green_Relic_Heart',(0,3,-6.1),(4,4,1),'glow',rotation=(0,0,45),detail='crystal')
        a.pair('Blue_Shoulder_Sweeps',(0,9,0),(2,7,3),'trim',4.5,rotation=(0,0,18))
        a.box('Dark_Primer',(0,-12,0),(4,1,4),'dark',detail='primer')
    return a


class Atlas:
    def __init__(self,t):self.t=t;self.im=Image.new('RGBA',(SIZE,SIZE));self.x=self.y=1;self.row=0;self.cache={}
    def face(self,material,w,h,detail,face):
        key=(material,w,h,detail,face)
        if key in self.cache:return self.cache[key]
        if self.x+w+1>SIZE:self.x=1;self.y+=self.row+2;self.row=0
        assert self.y+h+1<=SIZE
        x,y=self.x,self.y;self.x+=w+2;self.row=max(self.row,h)
        base=tuple(bytes.fromhex(self.t['colors'][material][1:]));rng=random.Random(hashlib.sha256((str(self.t['index'])+str(key)).encode()).digest())
        tile=Image.new('RGBA',(w,h));d=ImageDraw.Draw(tile);shade={'top':1.10,'bottom':.76,'front':1,'back':.94,'left':.9,'right':1.04}[face]
        for py in range(h):
            for px in range(w):
                delta=rng.choice((-5,-3,-1,0,1,3,5))
                if detail in ('wood','grain'):delta+=round(5*math.sin(py*.9+px*.18))
                d.point((px,py),fill=tuple(max(0,min(255,round(v*shade+delta))) for v in base)+(255,))
        light=tuple(min(255,round(v*shade+23)) for v in base)+(255,);dark=tuple(max(0,round(v*shade-28)) for v in base)+(255,)
        if w>=3 and h>=3:
            d.line((0,0,w-1,0),fill=light);d.line((0,0,0,h-1),fill=light)
            d.line((0,h-1,w-1,h-1),fill=dark);d.line((w-1,0,w-1,h-1),fill=dark)
        if detail in ('stamp','rune','carved') and w>=4 and h>=4:
            d.line((1,h-2,1,1,w-2,1,w-2,h-2),fill=light)
            d.point((w//2,h//2),fill=dark)
        if detail=='primer' and w>=3 and h>=3:d.rectangle((1,1,w-2,h-2),outline=dark)
        if detail=='maze' and w>=6 and h>=6:d.line((1,1,w-2,1,w-2,h-2,2,h-2,2,3,w-4,3),fill=(77,213,235,255))
        if detail in ('crystal','lens','frost') and w>=3 and h>=3:d.line((1,h-2,w//2,1,w-2,h-2),fill=light)
        if detail=='eye' and w>=7 and h>=5:
            d.polygon(((1,h//2),(3,1),(w-4,1),(w-2,h//2),(w-4,h-2),(3,h-2)),fill=light)
            d.line((w//2,2,w//2,h-3),fill=(30,24,43,255),width=2)
        self.im.paste(tile,(x,y));self.cache[key]=(x,y);return x,y


def save(a):
    t=a.theme;index=t['index'];stem=f'Ranger_Ammo_{index:02}';atlas=Atlas(t);nodes=[];elements=[];scene=[]
    for i,p in enumerate(a.parts,1):
        layouts={};bbfaces={};uv={}
        for face,(j,k) in FACES.items():
            w,h=p['size'][j],p['size'][k];x,y=atlas.face(p['material'],w,h,p['detail'],face)
            layouts[face]=dict(offset=dict(x=x,y=y),mirror=dict(x=False,y=False),angle=0)
            bbfaces[BB_FACES[face]]=dict(uv=[x,y,x+w,y+h],texture=0);uv[face]=[x,y,x+w,y+h]
        shape=dict(type='box',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(size=vec(p['size']),isPiece=False),textureLayout=layouts,unwrapMode='custom',visible=True,doubleSided=False,shadingMode=p['shading_mode'])
        nodes.append(dict(id=str(i),name=p['name'],position=vec(p['center']),orientation=quat(p['rotation']),shape=shape,children=[]))
        cube=dict(name=p['name'],uuid=uid(stem+'/'+p['name']),type='cube',origin=p['center'],rotation=p['rotation'],faces=bbfaces,shading_mode=p['shading_mode'],double_sided=False,shade=p['shading_mode']!='fullbright',autouv=0,color=i%8)
        cube['from']=[p['center'][j]-p['size'][j]/2 for j in range(3)];cube['to']=[p['center'][j]+p['size'][j]/2 for j in range(3)];elements.append(cube);scene.append(dict(p,uv=uv))
    folder=ROOT/'Common/Items/RangerSnipers/Ammo'/f'{index:02}';folder.mkdir(parents=True,exist_ok=True)
    texture=folder/(stem+'.png');model=folder/(stem+'.blockymodel');atlas.im.save(texture)
    model.write_text(json.dumps(dict(format='character',lod='auto',nodes=nodes),indent=2)+'\n')
    bb=ROOT/'source'/(stem+'.bbmodel');sp=ROOT/'source'/(stem+'.scene.json')
    project=dict(meta=dict(format_version='4.10',model_format='free',box_uv=False),name=t['name'],model_identifier=stem,resolution=dict(width=SIZE,height=SIZE),elements=elements,outliner=[dict(name=t['name'],uuid=uid(stem+'/group'),origin=[0,0,0],children=[e['uuid'] for e in elements])],textures=[dict(name=texture.name,path=str(texture),id='0',uuid=uid(stem+'/texture'),source='data:image/png;base64,'+base64.b64encode(texture.read_bytes()).decode(),width=SIZE,height=SIZE,uv_width=SIZE,uv_height=SIZE,internal=True,saved=True)])
    bb.write_text(json.dumps(project,indent=2)+'\n');sp.write_text(json.dumps(dict(theme=t,texture=str(texture),parts=scene,atlas_size=SIZE),indent=2)+'\n')
    return dict(index=index,name=t['name'],item_id=t['ammo_id'],ammo_id=t['ammo_id'],rifle=t['rifle'],rifle_id=t['rifle_id'],region=t['region'],model=str(model.relative_to(ROOT/'Common')).replace('\\','/'),texture=str(texture.relative_to(ROOT/'Common')).replace('\\','/'),icon=f'Icons/ItemsGenerated/{stem}.png',source=str(bb.relative_to(ROOT)).replace('\\','/'),blockbench=str(bb.relative_to(ROOT)).replace('\\','/'),scene=str(sp.relative_to(ROOT)).replace('\\','/'),cube_count=len(nodes),texture_size=[SIZE,SIZE],fullbright_parts=[p['name'] for p in a.parts if p['shading_mode']=='fullbright'])


def main():
    (ROOT/'Common/Icons/ItemsGenerated').mkdir(parents=True,exist_ok=True)
    (ROOT/'previews').mkdir(exist_ok=True)
    assets=[save(build(t)) for t in THEMES]
    (ROOT/'artcatalog.json').write_text(json.dumps(dict(original_art=True,assets=assets),indent=2)+'\n')
    print(json.dumps(dict(models=len(assets),cubes=[a['cube_count'] for a in assets])))


if __name__=='__main__':main()
