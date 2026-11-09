"""Reproducible original Arsenal art. No downloads, external models or raster art.

Native attachment transforms and cube/animation exporters are carried forward
from Steven's original sniper pipeline; family geometry and motion are new.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import base64, hashlib, importlib.util, json, math, shutil
from PIL import Image, ImageDraw, ImageFont

ART=Path(__file__).resolve().parent
ROOT=ART.parent
FPS=60

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
N=module('arsenal_native_art',ART/'source/lib/native_art.py')
R=module('arsenal_native_reload',ART/'source/lib/native_reload.py')
V=N.vec
I=N.IDENTITY

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def empty(name,position=(0,0,0),orientation=None,children=None):
    return dict(id='0',name=name,position=V(position),orientation=orientation or dict(I),shape=N.shape_none(),children=children or [])

def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get('children',[]))

def theme(w):
    t=deepcopy(N.THEMES[w['artIndex']-1]);t.update(id=w['id'],name=w['name'],seed=t['seed']+1000*['handgun','smg','semiauto','automatic','shotgun'].index(w['family']))
    return t

def ring(r,name,center,radius,segments=8,plane='yz',material='trim',width=3,thickness=2,skip=()):
    for j in range(segments):
        if j in skip:continue
        angle=360*j/segments;a=math.radians(angle);x,y,z=center
        if plane=='yz':
            position=(x,y+radius*math.cos(a),z+radius*math.sin(a));size=(width,thickness,max(3,round(2*radius*math.sin(math.pi/segments)+1)));rotation=(angle,0,0)
        else:
            position=(x+radius*math.cos(a),y+radius*math.sin(a),z);size=(max(3,round(2*radius*math.sin(math.pi/segments)+1)),thickness,width);rotation=(0,0,angle+90)
        r.box(name+'_'+str(j),position,size,material,rotation,detail='energy' if material in ('glow','railglow') else '')

def make_legendary(w):
    """Ten separately authored silhouettes. No base-family receiver is reused."""
    r=N.Rifle(theme(w));f=w['family'];deep=w['artIndex']==5
    # The inherited grip is the sole shared interface, below each new chassis.
    r.box('Trigger',(5,-8,0),(1,4,2),'trim',(0,0,12))
    r.box('Guard_Spar',(3,-13,0),(8,2,4),'dark')
    if f=='handgun' and deep:
        # Break-action industrial handcannon: exposed eight-chamber turret,
        # forward brake, hanging counterweight and hammer, no pistol slide.
        r.box('Handcannon_Yoke',(3,-2,0),(16,5,9),'dark')
        r.box('Slide',(-5,3,0),(15,5,5),'steel')
        for j in range(8):
            a=math.radians(j*45);r.box('Turret_Chamber_'+str(j),(-5,3+5*math.cos(a),5*math.sin(a)),(16,3,3),'steel',(j*45,0,0))
            r.box('Turret_Amber_Window_'+str(j),(-5,3+5.7*math.cos(a),5.7*math.sin(a)),(7,1,2),'glow',(j*45,0,0),detail='energy')
        ring(r,'Turret_Copper_Clamp',(-13,3,0),6,8,'yz','trim',2,2)
        r.box('Heavy_Barrel',(-23,3,0),(20,6,6),'dark')
        r.box('Maw_Brake',(-34,3,0),(8,10,10),'steel')
        for j in range(3):r.paired('Brake_Sawtooth_'+str(j),(-36+j*3,6,0),(2,6,2),'trim',5.5,(0,0,-18))
        r.box('Counterweight_Arm',(-15,-7,0),(20,3,5),'steel')
        r.box('Counterweight',(-23,-10,0),(12,7,9),'trim',detail='hazard')
        r.box('Magazine',(-4,-3,0),(10,5,8),'steel')
        r.box('Hammer',(8,8,0),(5,8,4),'dark',(0,0,-22))
        r.box('Energy_Core',(-6,3,-7),(7,4,2),'glow',detail='energy')
    elif f=='handgun':
        # Crescent fork projector: open negative space, floating prism and
        # swept forward tines instead of a solid slide/receiver block.
        r.box('Prism_Grip_Bridge',(6,-3,0),(14,4,5),'dark',(0,0,-12))
        ring(r,'Crescent_Frame',(-9,4,0),11,10,'xy','trim',4,2,skip=(3,4,5))
        ring(r,'Crescent_Light',(-9,4,-2.6),9,10,'xy','glow',1,1,skip=(3,4,5))
        r.paired('Fork_Upper',(-23,9,0),(21,3,3),'pale',4,(0,0,12))
        r.paired('Fork_Lower',(-24,-1,0),(18,3,3),'steel',4,(0,0,-12))
        r.box('Slide',(-16,4,0),(10,4,4),'glass',(45,0,0),detail='crystal')
        r.box('Floating_Nose_Prism',(-28,4,0),(5,5,5),'glow',(0,45,0),detail='crystal')
        r.box('Magazine',(7,-5,0),(8,5,6),'dark')
        r.box('Prism_Cell_Heel',(10,-10,0),(6,4,6),'trim')
        r.box('Energy_Core',(-7,4,0),(5,6,4),'glow',(0,0,45),detail='crystal')
        r.box('Crescent_Crown',(-8,17,0),(7,2,4),'pale')
    elif f=='smg' and deep:
        # A compact twin-rail winding machine, asymmetric rear brace, side drum.
        r.box('Open_Chassis',(0,0,0),(21,6,8),'dark')
        r.paired('Twin_Winding_Rail',(-21,4,0),(31,3,3),'steel',4.5)
        r.paired('Rail_Inner_Current',(-21,4,0),(26,1,1),'railglow',2.6,detail='energy')
        for j,x in enumerate((-10,-19,-28)):ring(r,'Winding_Cage_'+str(j),(x,4,0),5,6,'yz','trim',2,2)
        r.box('Magazine',(-2,-10,-5),(12,13,8),'dark')
        ring(r,'Winding_Drum',(-2,-10,-6),7,8,'xy','steel',9,3)
        ring(r,'Drum_Copper_Teeth',(-2,-10,-11),7,8,'xy','trim',2,2)
        r.box('Drum_Hub',(-2,-10,-12),(6,6,2),'glow',detail='energy')
        r.box('Asymmetric_Stock_Upper',(20,7,3),(24,3,3),'steel',(0,0,14))
        r.box('Asymmetric_Stock_Lower',(23,-4,3),(19,3,3),'trim',(0,0,-12))
        r.box('Stock_Hook',(34,0,3),(4,17,5),'dark',(0,0,-10))
        r.box('Bolt',(3,6,0),(9,4,6),'trim')
        r.box('Charging_Handle',(6,7,-7),(3,3,6),'steel')
        r.box('Forward_Grip',(-20,-5,0),(5,11,6),'rubber',(0,0,-15))
        r.box('Energy_Core',(-20,4,0),(24,2,2),'glow',detail='energy')
        r.box('Iron_Rake_Muzzle',(-39,4,0),(6,8,12),'steel')
    elif f=='smg':
        # Winged halo bullpup, receiver behind the hand and a narrow open nose.
        r.box('Bullpup_Spine',(10,1,0),(31,5,6),'dark')
        r.box('Magazine',(18,-8,0),(12,14,7),'pale',(0,0,12))
        ring(r,'Rear_Halo',(21,4,0),11,10,'xy','trim',4,2)
        ring(r,'Halo_Light',(21,4,-2.5),8.5,10,'xy','glow',1,1)
        r.paired('Swept_Wings',(-4,10,0),(23,4,3),'pale',4.5,(0,0,26))
        r.paired('Wing_Feather_1',(-12,13,0),(10,2,3),'trim',6,(0,0,30))
        r.paired('Wing_Feather_2',(-3,16,0),(11,2,3),'glass',6,(0,0,25))
        r.paired('Nose_Rail',(-24,4,0),(30,3,3),'steel',3.5)
        r.paired('Nose_Light',(-24,4,0),(24,1,1),'glow',1.5,detail='energy')
        r.box('Bolt',(1,5,0),(7,3,4),'trim')
        r.box('Charging_Handle',(1,7,-4),(3,3,3),'pale')
        r.box('Breastplate',(-7,-4,0),(12,4,6),'pale',(0,0,-16))
        r.box('Energy_Core',(-12,4,0),(6,6,6),'glow',(45,0,0),detail='crystal')
        r.box('Emitter_Beak',(-40,4,0),(7,4,4),'pale',(0,0,12))
    elif f=='semiauto' and deep:
        # Exposed piston spine with an offset high optic and a skeletal crutch.
        r.box('Skeleton_Receiver',(1,-1,0),(27,6,7),'dark')
        r.box('Piston_Main',(-24,3,0),(48,6,6),'steel')
        r.box('Piston_Upper_Spine',(-19,10,0),(41,3,4),'trim')
        for j,x in enumerate((-35,-25,-15,-5)):r.box('Exposed_Spine_Rib_'+str(j),(x,6,0),(3,12,10),'steel')
        r.paired('Piston_Current',(-23,3,0),(40,2,1),'glow',3.5,detail='energy')
        r.box('Bolt',(6,5,0),(11,5,7),'trim')
        r.box('Charging_Handle',(10,7,-8),(4,4,5),'steel')
        r.box('Offset_Optic_Bracket',(0,13,-8),(17,3,3),'steel')
        r.box('Offset_Optic',(-1,17,-9),(19,6,6),'dark')
        r.box('Optic_Amber_Lens',(-11,17,-9),(1,4,4),'glass',detail='lens')
        r.box('Magazine',(-5,-9,0),(11,9,7),'trim',detail='hazard')
        r.box('Crutch_Stock_Upper',(25,4,0),(29,4,5),'steel',(0,0,8))
        r.box('Crutch_Stock_Lower',(25,-8,0),(27,3,4),'dark',(0,0,-15))
        r.box('Stock_Piston_Pad',(41,-2,0),(5,20,9),'rubber')
        ring(r,'Piston_Muzzle_Cage',(-51,3,0),6,8,'yz','trim',4,2)
        r.box('Energy_Core',(-23,3,-4),(18,3,1),'railglow',detail='energy')
    elif f=='semiauto':
        # Trident tuning fork, floating long prism and a crescent shoulder ring.
        r.box('Long_Prism',(-20,4,0),(52,4,4),'glass',(45,0,0),detail='crystal')
        r.box('Golden_Keel',(-12,-2,0),(36,3,5),'trim')
        r.paired('Trident_Outer_Tine',(-38,7,0),(46,3,3),'pale',5.5,(0,0,5))
        r.box('Trident_Center_Tine',(-45,4,0),(36,2,2),'glow',detail='energy')
        r.paired('Trident_Lower_Prongs',(-43,-1,0),(25,2,3),'steel',5.5,(0,0,-7))
        ring(r,'Shoulder_Crescent',(29,2,0),14,10,'xy','pale',5,2,skip=(4,5,6))
        ring(r,'Shoulder_Light',(29,2,-3),11,10,'xy','glow',1,1,skip=(4,5,6))
        r.box('Magazine',(0,-8,0),(8,12,5),'dark',(0,0,-12))
        r.box('Bolt',(4,7,0),(10,3,5),'pale')
        r.box('Charging_Handle',(8,7,-5),(3,3,4),'trim')
        r.box('Hanging_Prism_Optic',(-5,14,0),(15,4,5),'dark')
        r.box('Optic_Prism',(-13,14,0),(3,5,5),'glow',(45,0,0),detail='lens')
        r.box('Energy_Core',(-19,4,0),(11,6,6),'glow',(45,0,0),detail='crystal')
    elif f=='automatic' and deep:
        # Rotary barrel crown, belt-fed box and an exposed overhead flywheel.
        r.box('Iron_Engine_Block',(1,-1,0),(25,12,11),'steel')
        r.box('Barrel_Axle',(-29,3,0),(40,3,3),'dark')
        for j in range(6):
            a=math.radians(j*60);r.box('Rotary_Barrel_'+str(j),(-29,3+5*math.cos(a),5*math.sin(a)),(36,3,3),'steel',(j*60,0,0))
            r.box('Rotary_Amber_Line_'+str(j),(-26,3+5*math.cos(a),5*math.sin(a)),(20,1,1),'glow',(j*60,0,0),detail='energy')
        for x in (-13,-42):ring(r,'Rotary_Crown_'+str(x),(x,3,0),7,8,'yz','trim',3,2)
        r.box('Magazine',(-5,-13,-3),(18,15,12),'dark')
        r.paired('Belt_Box_Hazard',(-5,-13,-3),(12,6,1),'warning',6.1,detail='hazard')
        for j in range(5):r.box('Belt_Link_'+str(j),(3+j*3,-3-j, -8),(2,4,3),'trim',(0,0,15))
        ring(r,'Upper_Flywheel',(6,16,0),9,10,'xy','steel',5,3)
        ring(r,'Flywheel_Amber',(6,16,-3),6,10,'xy','glow',1,1)
        r.box('Flywheel_Axle',(6,16,0),(4,4,10),'trim')
        r.box('Bolt',(9,7,0),(7,3,7),'dark');r.box('Charging_Handle',(10,8,-8),(3,3,6),'trim')
        r.box('Industrial_Stock',(27,0,0),(29,7,6),'steel');r.box('Stock_Butt',(43,-4,0),(5,19,10),'rubber')
        r.box('Energy_Core',(-4,3,-6),(12,5,1),'glow',detail='energy')
    elif f=='automatic':
        # A suspended sun-ring carbine, solar vanes and a crystal arch stock.
        ring(r,'Sunring',(-13,7,0),14,12,'xy','trim',4,2)
        ring(r,'Sunring_Light',(-13,7,-2.7),11,12,'xy','glow',1,1)
        for j in range(6):
            a=math.radians(j*60);r.box('Solar_Vane_'+str(j),(-13+18*math.cos(a),7+18*math.sin(a),0),(8,3,4),'pale',(0,0,j*60))
        r.box('Suspended_Laser',(-31,7,0),(26,3,3),'glass',(45,0,0),detail='crystal')
        r.paired('Emitter_Talon',(-41,8,0),(14,3,3),'pale',4,(0,0,10))
        r.box('Keel_Receiver',(3,-2,0),(22,5,7),'dark')
        r.box('Magazine',(-3,-10,0),(9,14,6),'pale',(0,0,-12))
        r.box('Cell_Prism',(-5,-10,-3.3),(4,9,1),'glow',detail='crystal')
        r.box('Crystal_Stock_Arch_1',(23,8,0),(22,4,5),'glass',(0,0,25),detail='crystal')
        r.box('Crystal_Stock_Arch_2',(38,9,0),(16,4,5),'pale',(0,0,-20))
        r.box('Crystal_Stock_Foot',(44,-1,0),(4,18,7),'trim')
        r.box('Bolt',(6,3,0),(6,3,4),'trim');r.box('Charging_Handle',(9,4,-5),(3,3,4),'pale')
        r.box('Energy_Core',(-13,7,0),(8,8,5),'glow',(0,0,45),detail='crystal')
    elif deep:
        # Twin-breach battering maul with shield fangs and a broad impact crown.
        r.box('Breach_Block',(0,1,0),(27,14,14),'steel')
        r.paired('Maul_Barrel',(-31,4,0),(40,8,7),'dark',5)
        r.paired('Muzzle_Clamp',(-48,4,0),(7,12,10),'trim',5)
        r.box('Fanged_Shield',(-14,-3,0),(5,23,24),'steel',detail='hazard')
        for j,z in enumerate((-10,-5,0,5,10)):r.box('Shield_Fang_'+str(j),(-16,-14,z),(8,7,3),'trim',(0,0,-22))
        r.box('Pump',(-30,-6,0),(18,6,10),'rubber')
        for x in (-34,-28,-22):r.box('Maul_Pump_Stud_'+str(x),(x,-7,0),(2,9,12),'steel')
        r.box('Bolt',(6,9,0),(12,5,12),'trim');r.box('Charging_Handle',(10,7,-10),(4,5,7),'steel')
        r.box('Loading_Gate',(-4,-8,0),(14,3,10),'dark')
        r.box('Stock_Industrial_Beam',(27,0,0),(28,8,8),'steel');r.box('Stock_Ram_Pad',(43,-5,0),(7,21,12),'rubber')
        r.paired('Shield_Current',(-16,-1,0),(2,10,2),'glow',11,detail='energy')
        r.box('Energy_Core',(-1,2,-8),(11,7,2),'glow',detail='energy')
    else:
        # Seven-emitter sunburst, each independent gold rail ending in a prism.
        r.box('Prism_Chamber',(0,1,0),(18,9,9),'dark')
        ring(r,'Prism_Chamber_Crown',(-6,2,0),9,10,'yz','trim',3,2)
        for j in range(7):
            angle=(j-3)*8;y=3+(j-3)*3.4
            r.box('Sunburst_Rail_'+str(j),(-30,y,0),(39,2,4),'pale',(0,0,-angle))
            r.box('Sunburst_Inner_'+str(j),(-31,y,-2.5),(28,1,1),'glow',(0,0,-angle),detail='energy')
            r.box('Emitter_Prism_'+str(j),(-49,y+(j-3)*2,0),(5,5,5),'glass',(45,0,0),detail='crystal')
        r.box('Halo_Stock_Upper',(24,10,0),(27,3,5),'pale',(0,0,17));r.box('Halo_Stock_Lower',(25,-6,0),(29,3,5),'trim',(0,0,-16))
        r.box('Stock_Prism_Butt',(42,0,0),(4,21,7),'glass',detail='crystal')
        r.box('Loading_Gate',(0,-8,0),(10,4,7),'pale')
        r.box('Pump',(-13,-6,0),(11,3,7),'trim')
        r.box('Bolt',(5,6,0),(9,3,6),'pale');r.box('Charging_Handle',(8,7,-5),(3,3,5),'trim')
        r.box('Energy_Core',(-5,2,0),(10,10,7),'glow',(0,0,45),detail='crystal')
    for p in r.parts:
        p['shading_mode']='fullbright' if p['material'] in ('glow','railglow') else 'flat'
    return r

def make_gun(w):
    if w['artIndex'] in (5,6):return make_legendary(w)
    t=theme(w);r=N.Rifle(t);f=w['family'];i=w['artIndex'];energy=i in (5,6);charged=i in (4,7,8)
    lengths={'handgun':18,'smg':31,'semiauto':47,'automatic':39,'shotgun':48};front=lengths[f]
    # All receivers share the inherited native grip anchor. Family silhouettes
    # keep their own lengths instead of scaling every gun to sniper dimensions.
    if f=='handgun':
        r.box('Pistol_Frame',(-2,-2,0),(27,7,7),'wood' if i==1 else 'steel',detail='wood' if i==1 else 'panel')
        r.box('Slide',(-6,3,0),(29,6,7),'steel')
        r.box('Slide_Rear', (6,3,0),(5,7,8),'trim')
        r.box('Barrel',(-16,2,0),(16,3,3),'dark')
        r.box('Magazine',(10,-15,0),(5,13,5),'dark',(0,0,18))
        r.box('Magazine_Floor',(12,-22,0),(8,2,7),'trim',(0,0,18))
        for x in (1,4):r.paired('Slide_Serration_'+str(x),(x,3,0),(1,4,1),'dark',3.6)
        r.box('Front_Sight',(-18,7,0),(2,2,2),'trim');r.box('Rear_Sight',(7,8,0),(3,2,5),'dark')
        r.box('Trigger_Guard_Front',(0,-9,0),(2,8,4),'dark')
        r.box('Trigger_Guard_Bow',(5,-13,0),(10,2,4),'dark')
        r.box('Trigger',(5,-7,0),(1,4,2),'trim',(0,0,12))
        r.muzzle(-22,2,7,3,'trim',energy)
    else:
        receiver_len=25 if f in ('smg','automatic') else 29
        receiver_width=8 if f=='smg' else 9
        r.box('Receiver',(0,0,0),(receiver_len,10,receiver_width),'wood' if i==1 else 'steel',detail='wood' if i==1 else 'panel')
        r.paired('Receiver_Plate',(-1,0,0),(receiver_len-4,6,1),'trim',receiver_width/2+.1,detail='panel')
        r.box('Bolt',(6,4,-5),(7,3,3),'dark')
        r.box('Charging_Handle',(7,3,-7),(3,3,5),'trim')
        r.box('Barrel',(-front+8,2,0),(2*(front-21),4 if f!='shotgun' else 6,4 if f!='shotgun' else 6),'dark')
        r.box('Handguard',(-23 if f!='smg' else -18,-1,0),(21 if f!='smg' else 15,7,8),'woodlight' if i==1 else 'steel',detail='wood' if i==1 else 'panel')
        r.box('Trigger_Guard_Front',(2,-10,0),(2,7,4),'dark');r.box('Trigger_Guard_Bow',(6,-13,0),(9,2,4),'dark');r.box('Trigger',(5,-8,0),(1,4,2),'trim',(0,0,12))
        if f=='smg':
            r.box('Magazine',(-5,-14,0),(7,23,5),'dark',(0,0,-7));r.box('Magazine_Floor',(-6,-26,0),(10,2,7),'trim')
            r.paired('Wire_Stock_Rail',(20,0,0),(20,2,2),'trim',3);r.box('Wire_Stock_Butt',(30,-3,0),(3,13,8),'rubber')
            r.box('Support_Grip',(-22,-9,0),(5,11,6),'rubber',(0,0,-8))
        elif f=='automatic':
            r.box('Magazine',(-6,-13,0),(10,18,7),'dark',(0,0,-9));r.box('Magazine_Floor',(-8,-23,0),(12,3,8),'trim',(0,0,-9))
            r.box('Stock_Spine',(21,1,0),(22,5,6),'steel');r.box('Stock_Cheek',(23,3,0),(15,4,7),'cloth');r.box('Stock_Butt',(33,-4,0),(4,16,8),'rubber')
            r.box('Foregrip',(-23,-8,0),(5,10,6),'rubber')
        elif f=='semiauto':
            r.box('Magazine',(-4,-10,0),(10,10,6),'dark');r.box('Magazine_Floor',(-4,-16,0),(12,2,7),'trim')
            r.box('Stock_Neck',(20,-2,0),(18,7,7),'wood' if i==1 else 'steel',(0,0,-8),detail='wood' if i==1 else '')
            r.box('Stock_Body',(30,-4,0),(14,12,8),'wood' if i==1 else 'cloth',detail='wood' if i==1 else 'cloth');r.box('Stock_Butt',(39,-4,0),(3,16,9),'rubber')
            r.scope(-1,13,20,6,'trim',energy)
        else:
            r.box('Magazine_Tube',(-26,-4,0),(38,4,4),'steel')
            r.box('Pump',(-27,-5,0),(17,8,9),'wood' if i==1 else 'rubber',detail='wood' if i==1 else '')
            for x in (-32,-28,-24):r.box('Pump_Rib_'+str(x),(x,-5,0),(1,9,10),'trim')
            r.box('Stock_Neck',(20,-2,0),(18,7,7),'wood' if i==1 else 'steel',(0,0,-10))
            r.box('Stock_Body',(30,-5,0),(16,12,8),'wood' if i==1 else 'cloth');r.box('Stock_Butt',(40,-5,0),(3,17,9),'rubber')
            r.box('Loading_Gate',(-5,-5,0),(12,2,7),'trim')
            r.box('Front_Bead',(-front,6,0),(2,2,2),'pale')
        if f not in ('semiauto','shotgun'):
            r.box('Sight_Rail',(-2,7,0),(15,2,5),'dark');r.box('Reflex_Frame',(-2,11,0),(4,7,7),'trim');r.box('Reflex_Lens',(-3,11,0),(1,5,5),'glass',detail='lens')
        r.muzzle(-front-2,2,9 if f=='shotgun' else 7,4,'trim',energy)
    # Nine region-specific constructions, not a palette swap of one mesh.
    extent=front if f!='handgun' else 18
    if i==1:
        r.paired('Field_Copper_Inlay',(-4,0,0),(12,2,1),'trim',4.7,detail='inlay')
        r.box('Field_Cloth_Binding',(-extent+7,0,0),(4,8,8),'cloth',detail='cloth')
    elif i==2:
        for j in range(4):r.paired('Sand_Vent_'+str(j),(-extent+4+j*3,2,0),(1,4,1),'dark',4.6)
        r.box('Sand_Seal',(-extent+4,-1,0),(4,9,9),'cloth',detail='cloth')
    elif i==3:
        r.paired('Frost_Pale_Armor',(-5,1,0),(18,4,1),'pale',5,detail='panel')
        r.box('Frost_Crown',(-extent+7,3,0),(10,3,7),'pale')
        for j in range(3):r.paired('Cold_Fin_'+str(j),(-extent+4+j*3,3,0),(1,5,1),'trim',4.8)
    elif i==4:
        r.paired('Reliquary_Core',(-6,1,0),(10,4,1),'glow',5.2,detail='energy')
        for j,x in enumerate((-12,-5,2)):r.box('Reliquary_Rib_'+str(j),(x,1,0),(2,12,12),'trim')
        r.paired('Bone_Sigil',(4,1,0),(5,6,1),'pale',5.9,detail='skull')
    elif i==5:
        r.paired('Industrial_Hazard',(-3,0,0),(10,4,1),'warning',5.3,detail='hazard')
        for j in range(3):
            x=-extent+4+j*5;r.box('Coil_Collar_'+str(j),(x,2,0),(3,10,11),'trim');r.paired('Coil_Glow_'+str(j),(x,2,0),(3,6,1),'glow',5.6,detail='energy')
        r.box('Energy_Core',(-8,-1,0),(8,3,3),'railglow',detail='energy')
    elif i==6:
        r.paired('Ivory_Casing',(-5,1,0),(18,5,1),'pale',5.3,detail='panel')
        r.paired('Split_Emitter',(-extent+3,2,0),(14,4,3),'steel',4)
        r.paired('Emitter_Energy',(-extent+3,2,0),(12,2,1),'glow',2.4,detail='energy')
        r.box('Energy_Core',(-8,1,-5.8),(7,3,1),'glow',detail='crystal')
        r.box('Prism_Crest',(-extent+3,7,0),(3,3,3),'woodlight',(0,0,45),detail='crystal')
    elif i==7:
        r.paired('Caged_Violet_Eye',(-4,1,0),(8,7,1),'glow',5.3,detail='eye')
        for j,x in enumerate((-10,2)):r.paired('Fear_Cage_'+str(j),(x,1,0),(2,12,2),'trim',6)
        r.box('Crimson_Prayer_Seal',(-6,8,0),(4,4,3),'warning',(0,0,45))
    elif i==8:
        r.paired('Maze_Plate',(-5,1,0),(17,7,1),'steel',5.5,detail='maze')
        r.paired('Crystal_Brace',(-extent+5,2,0),(9,3,2),'glass',4.9,detail='crystal')
        r.box('Crystal_Breech',(7,5,0),(6,4,5),'trim')
    else:
        r.paired('Carved_Artifact',(-2,1,0),(11,7,1),'pale',5.3,detail='carved')
        r.box('Green_Relic_Eye',(-2,1,-6.1),(4,4,1),'glow',(0,0,45),detail='crystal')
        r.box('Red_Sail_Fin',(-extent+7,7,0),(7,6,2),'cloth',(0,0,-18),detail='cloth')
        r.box('Skybound_Binding',(-extent+4,0,0),(3,9,9),'warning')
    for p in r.parts:p['shading_mode']='fullbright' if energy and p['material'] in ('glow','railglow') else 'flat'
    return r

def make_ammo(w):
    r=N.Rifle(theme(w));f=w['family'];i=w['artIndex'];energy=i in (5,6)
    height={'handgun':10,'smg':12,'semiauto':21,'automatic':17,'shotgun':14}[f];width=7 if f=='shotgun' else 5
    r.box('Case',(0,0,0),(width,height,width),'woodlight' if i==1 else 'steel',detail='wood' if i==9 else 'panel')
    r.box('Extractor_Rim',(0,-height/2,0),(width+2,2,width+2),'trim')
    r.box('Primer',(0,-height/2-1.3,0),(3,1,3),'dark')
    if f=='shotgun':
        r.box('Crimp',(0,height/2,0),(width+1,2,width+1),'cloth')
        r.paired('Shell_Gauge_Mark',(0,0,0),(3,5,1),'warning',width/2+.1,detail='inlay')
        for x in (-2,2):r.box('Shell_Pellet_Emboss_'+str(x),(x,1,-width/2-.2),(1,1,1),'trim')
    else:
        r.box('Shoulder',(0,height/2,0),(width,2,width),'trim')
        r.box('Projectile',(0,height/2+3,0),(3,4,3),'pale' if i==3 else 'edge')
        r.box('Nose',(0,height/2+5.5,0),(2,2,2),'edge')
    r.paired('Regional_Seal',(0,0,0),(3,4,1),'cloth' if i<4 else 'glow',width/2+.1,detail='eye' if i==7 else 'maze' if i==8 else 'carved' if i==9 else 'inlay')
    if energy:
        for j,y in enumerate((-height*.25,0,height*.25)):r.box('Energy_Band_'+str(j),(0,y,0),(width+1,1,width+1),'glow',detail='energy')
    for p in r.parts:p['shading_mode']='fullbright' if energy and p['material']=='glow' else 'flat'
    return r

def export_parts(r,slug,weapon):
    atlas=N.Atlas(r.theme);nodes=[];scene=[]
    parts=deepcopy(r.parts)
    fit=[1,1,1]
    if weapon:
        corners=[]
        for p in parts:
            q=dict(I);axes=[(axis,v) for axis,v in zip('xyz',p['rotation']) if v]
            if axes:q=N.quaternion(*axes[0])
            mat=R.qmat(q)
            for x in (-.5,.5):
                for y in (-.5,.5):
                    for z in (-.5,.5):
                        v=mat@([x*p['size'][0],y*p['size'][1],z*p['size'][2]])
                        corners.append([v[a]+p['center'][a] for a in range(3)])
        lo=[min(c[a] for c in corners) for a in range(3)];hi=[max(c[a] for c in corners) for a in range(3)]
        fit=[min(1,49/abs(lo[0]),30/hi[0]),min(1,24/abs(lo[1]),13.8/hi[1]),min(1,4.5/max(abs(lo[2]),abs(hi[2])))]
        if weapon['quality']=='Legendary':fit=[v*.975 for v in fit]
    for index,p in enumerate(parts):
        uv={};layout={}
        for face,(a,b) in N.FACE_DIMS.items():
            width,height=p['size'][a],p['size'][b];u,v=atlas.face(p['material'],width,height,p['detail'],face)
            layout[face]=dict(offset=dict(x=u,y=v),mirror=dict(x=False,y=False),angle=0);uv[face]=[u,v,u+width,v+height]
        q=dict(I);axis=[(a,v) for a,v in zip('xyz',p['rotation']) if v]
        if axis:q=N.quaternion(*axis[0])
        center=[p['center'][a]*fit[a] for a in range(3)];actual_size=[p['size'][a]*fit[a] for a in range(3)]
        shape=dict(type='box',offset=V((0,0,0)),stretch=V(fit),settings=dict(size=V(p['size']),isPiece=False),textureLayout=layout,unwrapMode='custom',visible=True,doubleSided=False,shadingMode=p['shading_mode'])
        nodes.append(dict(id=str(index+4),name=p['name'],position=V(center),orientation=q,shape=shape,children=[]));scene.append(dict(p,center=center,size=actual_size,uv=uv))
    if weapon:
        # Native grip geometry, native R-Attachment/Handle/Base interfaces.
        grip=N.Rifle(r.theme);grip.box('Handle',(11.098076,-13.222432,0),(4,14,6),'wood' if r.theme['id'].endswith('Wildwood') else 'rubber',(0,0,30))
        gp=grip.parts[0];layout={};uv={}
        for face,(a,b) in N.FACE_DIMS.items():
            u,v=atlas.face(gp['material'],gp['size'][a],gp['size'][b],'',face);layout[face]=dict(offset=dict(x=u,y=v),mirror=dict(x=False,y=False),angle=0);uv[face]=[u,v,u+gp['size'][a],v+gp['size'][b]]
        handle=dict(id='2',name='Handle',position=V((0,0,0)),orientation=N.HANDLE_Q,shape=dict(type='box',offset=V((0,-1,0)),stretch=V((1,1.1,.975)),settings=dict(size=V((4,14,6)),isPiece=False),textureLayout=layout,unwrapMode='custom',visible=True,doubleSided=False,shadingMode='flat'),children=[])
        muzzle_x=(lo[0]+.5)*fit[0] if weapon['quality']=='Legendary' else -{'handgun':24,'smg':35,'semiauto':51,'automatic':43,'shotgun':52}[weapon['family']]*fit[0]
        nodes.append(empty('Muzzle',(muzzle_x,2*fit[1],0)))
        if weapon['quality']=='Legendary':nodes.append(empty('Energy_Core_Anchor',(-8*fit[0],fit[1],-4*fit[2])))
        base=empty('Base',(-3,16,0),N.quaternion('z',-30),nodes);handle['children']=[base]
        model=dict(nodes=[empty('R-Attachment',(0,18,-20),children=[handle])],format='character',lod='auto')
        gp['size']=[4,15.4,5.85];scene.append(dict(gp,uv=uv,shading_mode='flat'))
    else:model=dict(nodes=nodes,format='character',lod='auto')
    for index,n in enumerate(walk(model['nodes']),1):n['id']=str(index)
    directory=ART/'Common/Items/Arsenal'/slug;directory.mkdir(parents=True,exist_ok=True)
    texture=directory/(slug+'.png');atlas.image.save(texture)
    write(directory/(slug+'.blockymodel'),model)
    write(ART/'source'/f'{slug}.scene.json',dict(theme=r.theme,texture=str(texture),parts=scene))
    return model,texture,scene,fit

def regroup(base,names,group):
    selected=[n for n in base['children'] if n['name'] in names];base['children']=[n for n in base['children'] if n not in selected]
    bone=empty(group,children=selected);base['children'].append(bone);return bone

def regroup_pivot(base,prefixes,group,pivot):
    selected=[n for n in base['children'] if any(n['name'].startswith(p) for p in prefixes)]
    base['children']=[n for n in base['children'] if n not in selected]
    for n in selected:n['position']=V([n['position'][axis]-pivot[a] for a,axis in enumerate('xyz')])
    base['children'].append(empty(group,pivot,children=selected))
    return selected

def shell_feed(clip,prop,count,duration):
    positions=[(0,(0,0,0))];visible=[]
    for j in range(count):
        start=.25+.45*j/count;end=start+.40/count
        positions.extend([(start,(8,-9,-10)),(start+(end-start)*.55,(4,-4,-5)),(end,(0,0,0))]);visible.extend([(start,True),(end,False)])
    positions.append((1,(0,0,0)));R.position_keys(clip,'AS_Reload_Ammo',positions,duration)
    for n in walk(prop['children']):
        if n['shape']['type']=='box':R.track(clip,n['name'])['shapeVisible']=[R.kf(0,False,'linear')]+[R.kf(p*duration,v,'linear') for p,v in visible]+[R.kf(duration,False,'linear')]

def add_reload(w,m,texture,ammo_model,ammo_texture,fit):
    slug=w['id'].removeprefix('Weapon_Crossbow_');base=m['nodes'][0]['children'][0]['children'][0];f=w['family'];energy=w['artIndex'] in (5,6)
    slide_names=['Slide','Slide_Rear'] if f=='handgun' else ['Bolt','Charging_Handle']
    if f=='shotgun':slide_names+=['Pump']+[f'Pump_Rib_{x}' for x in (-32,-28,-24)]
    regroup(base,slide_names,'AS_Reload_Action')
    mags=[n['name'] for n in base['children'] if n['name'].startswith('Magazine') and n['name']!='Magazine_Tube']
    if f=='shotgun':mags=['Loading_Gate']
    magazine=regroup(base,mags,'AS_Reload_Magazine')
    character_axis='x';character_angle=0;character_position=False
    if w['quality']=='Legendary':
        if w['artIndex']==5:
            prefixes,pivot,character_axis,character_angle={
                'handgun':(('Turret_',),(-5,3,0),'x',65),
                'smg':(('Winding_Drum','Drum_Copper','Drum_Hub'),(-2,-10,-6),'z',70),
                'semiauto':(('Piston_Main','Piston_Upper','Exposed_Spine','Piston_Current'),(-24,3,0),'x',0),
                'automatic':(('Rotary_Barrel','Rotary_Amber','Rotary_Crown'),(-29,3,0),'x',60),
                'shotgun':(('Breach_Block','Maul_Barrel','Muzzle_Clamp'),(8,-4,0),'z',-13),
            }[f]
            character_position=f=='semiauto'
            if f=='automatic':regroup_pivot(base,('Upper_Flywheel','Flywheel_Amber','Flywheel_Axle'),'AS_Flywheel',tuple(v*fit[a] for a,v in enumerate((6,16,0))))
        else:
            prefixes,pivot,character_axis,character_angle={
                'handgun':(('Crescent_Frame','Crescent_Light','Crescent_Crown'),(-9,4,0),'z',12),
                'smg':(('Rear_Halo','Halo_Light'),(21,4,0),'z',18),
                'semiauto':(('Trident_','Long_Prism'),(-20,4,0),'x',8),
                'automatic':(('Sunring','Solar_Vane'),(-13,7,0),'z',20),
                'shotgun':(('Sunburst_','Emitter_Prism'),(-30,3,0),'x',8),
            }[f]
        regroup_pivot(base,prefixes,'AS_Character',tuple(pivot[a]*fit[a] for a in range(3)))
    reg_energy=[n['name'] for n in base['children'] if n['shape'].get('shadingMode')=='fullbright']
    regroup(base,reg_energy,'AS_Reload_Energy')
    atlas=Image.new('RGBA',(512,1024));atlas.paste(Image.open(texture).convert('RGBA'),(0,0));atlas.paste(Image.open(ammo_texture).convert('RGBA'),(0,512));atlas.save(texture)
    raw_port=(0,-6,-4) if f=='shotgun' else (10,-9,0) if f=='handgun' else (-5,-6,0)
    port=tuple(raw_port[a]*fit[a] for a in range(3))
    prop=empty('AS_Reload_Ammo',(0,0,0),children=[])
    cartridge=empty('AS_Reload_Matching_Cartridge',port,N.quaternion('z',90) if f=='shotgun' else dict(I),deepcopy(ammo_model['nodes']))
    for n in walk(cartridge['children']):
        n['name']='AS_Prop_'+n['name'];n['position']=V([n['position'][axis]*.38 for axis in 'xyz']);n['shape']['stretch']=V((.38,.38,.38));n['shape']['visible']=False
        for uv in n['shape']['textureLayout'].values():uv['offset']['y']+=512
    prop['children'].append(cartridge)
    if f!='shotgun':
        for n in deepcopy(magazine['children']):
            for child in walk([n]):child['name']='AS_Prop_Replacement_'+child['name'];child['shape']['visible']=False
            prop['children'].append(n)
    base['children'].append(prop)
    duration=round(w['reload']['durationSeconds']*FPS);interface=json.loads((ART/'source/native-idle-interface.json').read_text());clips={}
    for view in ('FPS','TPS'):
        clip=dict(formatVersion=1,duration=duration,holdLastKeyframe=False,nodeAnimations={})
        # Weapon handling and player-arm reaches share the clip as native Rifle.
        rig=dict(hand_roll=-12 if f=='handgun' else 12 if energy else -22)
        R.player_tracks(clip,view,rig,duration,interface)
        R.position_keys(clip,'AS_Reload_Action',[(0,(0,0,0)),(.10,(0,0,0)),(.25,(5 if f!='shotgun' else 8,0,0)),(.72,(5 if f!='shotgun' else 8,0,0)),(.88,(0,0,0)),(1,(0,0,0))],duration)
        if w['quality']=='Legendary':
            if character_position:R.position_keys(clip,'AS_Character',[(0,(0,0,0)),(.20,(0,0,0)),(.40,(4,0,0)),(.70,(4,0,0)),(.88,(0,0,0)),(1,(0,0,0))],duration)
            else:R.rotation_keys(clip,'AS_Character',[(0,0),(.20,0),(.40,character_angle),(.70,character_angle),(.88,0),(1,0)],duration,character_axis)
        R.position_keys(clip,'AS_Reload_Magazine',[(0,(0,0,0)),(.20,(0,0,0)),(.32,(0,-10,-3)),(.59,(0,-10,-3)),(.75,(0,0,0)),(1,(0,0,0))],duration)
        R.rotation_keys(clip,'AS_Reload_Magazine',[(0,0),(.22,0),(.37,15),(.65,15),(.80,0),(1,0)],duration,'z')
        if energy:
            R.rotation_keys(clip,'AS_Reload_Energy',[(0,0),(.35,0),(.57,15),(.76,-8),(.91,0),(1,0)],duration,'x')
            R.position_keys(clip,'AS_Reload_Energy',[(0,(0,0,0)),(.35,(0,0,0)),(.57,(-2,0,0)),(.91,(0,0,0)),(1,(0,0,0))],duration)
        if f=='shotgun' and not energy:
            # Tube reload visibly feeds one shell for each chamber capacity.
            # The gameplay transfer remains atomic and cancellation-safe.
            shell_feed(clip,prop,w['reload']['capacity'],duration)
        else:
            R.position_keys(clip,'AS_Reload_Ammo',[(0,(0,0,0)),(.34,(8,-13,-10)),(.50,(4,-6,-4)),(.70,(0,0,0)),(1,(0,0,0))],duration)
            for n in walk(prop['children']):
                if n['shape']['type']=='box':R.visibility_keys(clip,n['name'],.34,.72,duration)
            for n in walk(magazine['children']):R.track(clip,n['name'])['shapeVisible']=[R.kf(0,True,'linear'),R.kf(.34*duration,False,'linear'),R.kf(.72*duration,True,'linear'),R.kf(duration,True,'linear')]
        clips[view]=clip
        write(ART/'Common/Characters/Animations/Items/Dual_Handed/Arsenal'/slug/f'Reload_{view}.blockyanim',clip)
        if f=='shotgun' and not energy:
            for count in range(1,w['reload']['capacity']+1):
                partial=deepcopy(clip);shell_feed(partial,prop,count,duration);clips[f'Reload{count}_{view}']=partial
                write(ART/'Common/Characters/Animations/Items/Dual_Handed/Arsenal'/slug/f'Reload{count}_{view}.blockyanim',partial)
    # Distinct shot mechanics: slide cycle, automatic bolt travel, shotgun pump.
    shot_duration=max(5,round(min(.55,w['cycleSeconds'])*FPS))
    for view in ('FPS','TPS'):
        shot=dict(formatVersion=1,duration=shot_duration,holdLastKeyframe=False,nodeAnimations={})
        R.position_keys(shot,'AS_Reload_Action',[(0,(0,0,0)),(.14,(3.5 if f!='shotgun' else 7,0,0)),(.35,(3.5 if f!='shotgun' else 7,0,0)),(.82,(0,0,0)),(1,(0,0,0))],shot_duration)
        if w['quality']=='Legendary':
            if character_position:R.position_keys(shot,'AS_Character',[(0,(0,0,0)),(.20,(3,0,0)),(.65,(1,0,0)),(1,(0,0,0))],shot_duration)
            else:R.rotation_keys(shot,'AS_Character',[(0,0),(.25,character_angle),(.55,character_angle*.8),(1,0)],shot_duration,character_axis)
            if f=='automatic' and w['artIndex']==5:R.rotation_keys(shot,'AS_Flywheel',[(0,0),(.30,90),(.70,160),(1,0)],shot_duration,'z')
        for name in ('R-Arm','R-Hand','L-Hand'):
            baseline=interface[view][name].get('orientation')
            if baseline:
                recoil=R.qmul(baseline,R.qaxis('x',-4 if f=='handgun' else -2))
                R.track(shot,name)['orientation']=[R.kf(0,baseline),R.kf(.18*shot_duration,recoil),R.kf(shot_duration,baseline)]
        write(ART/'Common/Characters/Animations/Items/Dual_Handed/Arsenal'/slug/f'Shoot_{view}.blockyanim',shot)
        if w['quality']=='Legendary':clips['Shoot_'+view]=shot
    if w['quality']=='Legendary' and w['artIndex']==5:
        charge_duration=max(6,round(w['ability']['chargeSeconds']*FPS))
        for view in ('FPS','TPS'):
            charge=dict(formatVersion=1,duration=charge_duration,holdLastKeyframe=False,nodeAnimations={})
            R.rotation_keys(charge,'AS_Reload_Energy',[(0,0),(.20,10),(.50,-8),(.80,15),(1,0)],charge_duration,'x')
            if character_position:R.position_keys(charge,'AS_Character',[(0,(0,0,0)),(.30,(2,0,0)),(.75,(5,0,0)),(1,(0,0,0))],charge_duration)
            else:R.rotation_keys(charge,'AS_Character',[(0,0),(.25,character_angle*.5),(.65,character_angle*1.8),(.90,character_angle),(1,0)],charge_duration,character_axis)
            if f=='automatic':R.rotation_keys(charge,'AS_Flywheel',[(0,0),(.25,40),(.50,100),(.75,200),(1,0)],charge_duration,'z')
            for name in ('R-Arm','R-Hand'):
                baseline=interface[view][name].get('orientation')
                if baseline:R.track(charge,name)['orientation']=[R.kf(0,baseline),R.kf(.6*charge_duration,R.qmul(baseline,R.qaxis('x',-3))),R.kf(charge_duration,baseline)]
            write(ART/'Common/Characters/Animations/Items/Dual_Handed/Arsenal'/slug/f'Charge_{view}.blockyanim',charge)
            clips['Charge_'+view]=charge
    player_id=w['reload'].get('playerAnimationsId','AS_'+slug+'_Player')
    anims={}
    for action in ('Reload','Shoot'):
        prefix=f'Characters/Animations/Items/Dual_Handed/Arsenal/{slug}/{action}'
        anims[action]=dict(FirstPerson=prefix+'_FPS.blockyanim',ThirdPerson=prefix+'_TPS.blockyanim',ThirdPersonMoving=prefix+'_TPS.blockyanim',Speed=1,Looping=False,BlendingDuration=.05 if action=='Shoot' else .08,ClipsGeometry=True)
    if w['quality']=='Legendary' and w['artIndex']==5:
        prefix=f'Characters/Animations/Items/Dual_Handed/Arsenal/{slug}/Charge'
        anims['ShootFlintlockCharging']=dict(FirstPerson=prefix+'_FPS.blockyanim',ThirdPerson=prefix+'_TPS.blockyanim',ThirdPersonMoving=prefix+'_TPS.blockyanim',Speed=1,Looping=False,BlendingDuration=.05,ClipsGeometry=True)
    partials={}
    if f=='shotgun' and not energy:
        for count in range(1,w['reload']['capacity']+1):
            action=f'Reload{count}';prefix=f'Characters/Animations/Items/Dual_Handed/Arsenal/{slug}/{action}'
            anims[action]=dict(FirstPerson=prefix+'_FPS.blockyanim',ThirdPerson=prefix+'_TPS.blockyanim',ThirdPersonMoving=prefix+'_TPS.blockyanim',Speed=1,Looping=False,BlendingDuration=.08,ClipsGeometry=True)
            partials[str(count)]=dict(animationId=action,first_person=prefix+'_FPS.blockyanim',third_person=prefix+'_TPS.blockyanim',shells=count)
    write(ART/'generated/Server/Item/Animations'/f'{player_id}.json',dict(Parent='Rifle',Animations=anims))
    for index,n in enumerate(walk(m['nodes']),1):n['id']=str(index)
    write(ART/'Common/Items/Arsenal'/slug/f'{slug}.blockymodel',m)
    entry=dict(item_id=w['id'],name=w['name'])
    bb=R.bb_export(m,texture,clips['FPS'],entry)
    for count in partials:bb['animations'].append(R.bb_export(m,texture,clips[f'Reload{count}_FPS'],entry,f'Reload{count}')['animations'][0])
    if w['quality']=='Legendary':
        bb['animations'].append(R.bb_export(m,texture,clips['Shoot_FPS'],entry,'Shoot')['animations'][0])
        if w['artIndex']==5:bb['animations'].append(R.bb_export(m,texture,clips['Charge_FPS'],entry,'Charge')['animations'][0])
    write(ART/'source'/f'{slug}.bbmodel',bb)
    return dict(animationId='Reload',playerAnimationsId=player_id,frames=duration,durationSeconds=w['reload']['durationSeconds'],capacity=w['reload']['capacity'],style='energy cartridge recharge' if energy else 'tube feed and pump' if f=='shotgun' else 'slide and grip magazine' if f=='handgun' else 'box magazine and bolt',first_person=f'Characters/Animations/Items/Dual_Handed/Arsenal/{slug}/Reload_FPS.blockyanim',third_person=f'Characters/Animations/Items/Dual_Handed/Arsenal/{slug}/Reload_TPS.blockyanim',ammo_prop=w['ammo'],atomic_magazine_feed=True,partialAnimations=partials)

def export_ammo_bb(model,texture,entry):
    elements=[];groups=[]
    for n in walk(model['nodes']):
        shape=n['shape'];size=[shape['settings']['size'][k] for k in 'xyz'];center=[n['position'][k] for k in 'xyz'];faces={}
        for face,(a,b) in N.FACE_DIMS.items():
            p=shape['textureLayout'][face]['offset'];faces[N.BB_FACE[face]]=dict(uv=[p['x'],p['y'],p['x']+size[a],p['y']+size[b]],texture=0)
        e=dict(name=n['name'],uuid=N.uid(entry['item_id']+'/'+n['name']),type='cube',origin=center,rotation=R.qeuler(n['orientation']),faces=faces,shading_mode=shape['shadingMode'],shade=shape['shadingMode']!='fullbright',autouv=0)
        e['from']=[center[a]-size[a]/2 for a in range(3)];e['to']=[center[a]+size[a]/2 for a in range(3)];elements.append(e);groups.append(e['uuid'])
    return dict(meta=dict(format_version='4.10',model_format='free',box_uv=False),name=entry['name'],resolution=dict(width=512,height=512),elements=elements,outliner=[dict(name=entry['name'],uuid=N.uid(entry['item_id']+'/root'),origin=[0,0,0],children=groups)],textures=[dict(name=texture.name,id='0',uuid=N.uid(entry['item_id']+'/texture'),source='data:image/png;base64,'+base64.b64encode(texture.read_bytes()).decode(),width=512,height=512,uv_width=512,uv_height=512,internal=True,saved=True)])

def main():
    spec=json.loads((ROOT/'content/arsenal-spec.json').read_text(encoding='utf-8-sig'));ammo={a['id']:a for a in spec['ammo']};guns=[];ammunition=[]
    # Remove only the two known, unreleased Crown spellings from owned runtime
    # trees. Source projects stay available; the pack must not load stale IDs.
    if any(w['id']=='Weapon_Crossbow_AS_Automatic_Crown_Of_Rivets' for w in spec['tiers']):
        obsolete=[ART/'Common/Items/Arsenal/AS_Automatic_Crown_of_Rivets',ART/'Common/Items/Arsenal/AS_Ammo_Automatic_Crown_of_Rivets',ART/'Common/Characters/Animations/Items/Dual_Handed/Arsenal/AS_Automatic_Crown_of_Rivets',ART/'Common/Icons/ItemsGenerated/AS_Automatic_Crown_of_Rivets.png',ART/'Common/Icons/ItemsGenerated/AS_Ammo_Automatic_Crown_of_Rivets.png',ART/'generated/Server/Item/Animations/AS_AS_Automatic_Crown_of_Rivets_Player.json']
        for p in obsolete:
            if not p.resolve().is_relative_to(ART.resolve()):raise ValueError('Unexpected obsolete path')
            if p.is_dir():shutil.rmtree(p)
            elif p.is_file():p.unlink()
    (ART/'source').mkdir(parents=True,exist_ok=True)
    for w in spec['tiers']:
        slug=w['id'].removeprefix('Weapon_Crossbow_');ammo_slug=w['ammo'];a=ammo[w['ammo']]
        am,at,_,_=export_parts(make_ammo(w),ammo_slug,False)
        ae=dict(item_id=w['ammo'],name=a['name'],family=w['family'],model=f'Items/Arsenal/{ammo_slug}/{ammo_slug}.blockymodel',texture=f'Items/Arsenal/{ammo_slug}/{ammo_slug}.png',icon=f'Icons/ItemsGenerated/{ammo_slug}.png',blockbench=f'source/{ammo_slug}.bbmodel',scene=f'source/{ammo_slug}.scene.json')
        write(ART/'source'/f'{ammo_slug}.bbmodel',export_ammo_bb(am,at,ae));ammunition.append(ae)
        m,texture,_,fit=export_parts(make_gun(w),slug,w);reload=add_reload(w,m,texture,am,at,fit)
        guns.append(dict(item_id=w['id'],name=w['name'],family=w['family'],quality=w['quality'],artIndex=w['artIndex'],model=f'Items/Arsenal/{slug}/{slug}.blockymodel',texture=f'Items/Arsenal/{slug}/{slug}.png',icon=f'Icons/ItemsGenerated/{slug}.png',blockbench=f'source/{slug}.bbmodel',scene=f'source/{slug}.scene.json',body_fit_scale=fit,cube_count=sum(n['shape']['type']=='box' for n in walk(m['nodes'])),playerAnimationsId=reload['playerAnimationsId'],reload=reload,fullbright_parts=[n['name'] for n in walk(m['nodes']) if n['shape']['type']=='box' and n['shape']['shadingMode']=='fullbright']))
    catalog=dict(original_art=True,animation_parent='Rifle',attachment_root='R-Attachment',handle_node='Handle',muzzle_axis='Base local -X',assets=guns,ammo=ammunition)
    write(ART/'artcatalog.json',catalog)
    clips=sum(4+2*len(a['reload']['partialAnimations'])+(2 if a['quality']=='Legendary' and a['artIndex']==5 else 0) for a in guns)
    print(f'Generated {len(guns)} editable gun rigs, {len(ammunition)} matching cartridges, {clips} native animation clips.')

if __name__=='__main__':main()
