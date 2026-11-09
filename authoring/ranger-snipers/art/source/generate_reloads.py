"""Idempotent original rifle reload rigs and genuine 60fps player/item clips.

Original static art is cached before the first rig pass. Weapon nodes and player
arms share the same native blockyanim, as in the installed Dart Rifle/Eggzooka.
"""
from __future__ import annotations
import os
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
import base64,hashlib,json,math,shutil,uuid
import numpy as np
from PIL import Image,ImageDraw

ART=Path(__file__).resolve().parents[1]
ROOT=ART.parent
CACHE=ART/'source/reload-baselines'
IDENTITY=dict(x=0,y=0,z=0,w=1)
FPS=60
FACE_SIZE={'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}
BB_FACE={'front':'south','back':'north','left':'west','right':'east','top':'up','bottom':'down'}


def vec(v):return dict(zip('xyz',[round(float(x),7) for x in v]))
def uid(v):return str(uuid.uuid5(uuid.NAMESPACE_URL,'original-ranger-reload/'+v))
def qaxis(axis,angle):
    q=dict(IDENTITY);q[axis]=math.sin(math.radians(angle/2));q['w']=math.cos(math.radians(angle/2));return q
def qmul(a,b):
    x,y,z,w=[a[k] for k in 'xyzw'];X,Y,Z,W=[b[k] for k in 'xyzw']
    return dict(x=w*X+x*W+y*Z-z*Y,y=w*Y-x*Z+y*W+z*X,z=w*Z+x*Y-y*X+z*W,w=w*W-x*X-y*Y-z*Z)
def qmat(q):
    x,y,z,w=[q[k] for k in 'xyzw'];return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
def qeuler(q):
    m=qmat(q);y=math.asin(max(-1,min(1,-m[2,0])));x=math.atan2(m[2,1],m[2,2]);z=math.atan2(m[1,0],m[0,0]);return [math.degrees(v) for v in (x,y,z)]
def empty_shape():return dict(type='none',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(isPiece=True),textureLayout={},unwrapMode='custom',visible=True,doubleSided=False,shadingMode='flat')
def bone(name,position=(0,0,0),orientation=None,children=None):return dict(id='0',name=name,position=vec(position),orientation=orientation or dict(IDENTITY),shape=empty_shape(),children=children or [])
def traverse(nodes):
    for n in nodes:
        yield n
        yield from traverse(n.get('children',[]))
def channel():return dict(position=[],orientation=[],shapeStretch=[],shapeVisible=[],shapeUvOffset=[])
def kf(time,delta,interpolation='smooth'):return dict(time=round(time),delta=delta,interpolationType=interpolation)
def track(clip,name):return clip['nodeAnimations'].setdefault(name,channel())
def position_keys(clip,name,keys,duration):track(clip,name)['position']=[kf(p*duration,vec(v)) for p,v in keys]
def rotation_keys(clip,name,keys,duration,axis='x'):track(clip,name)['orientation']=[kf(p*duration,qaxis(axis,v)) for p,v in keys]
def visibility_keys(clip,name,start,end,duration):track(clip,name)['shapeVisible']=[kf(0,False,'linear'),kf(start*duration,True,'linear'),kf(end*duration,False,'linear'),kf(duration,False,'linear')]


RIGS={
 1:dict(style='field bolt',bolt=['Copper_Bolt','Bolt_Knob','Steel_Bolt_Receiver'],gate=[],energy=[],pivot=(5,3,-4),port=(-2,3,-4),travel=7.5,lift=26,gate_axis='x',gate_angle=-62,prop_scale=.29,prop_entry=(13,-8,-13),hand_roll=-18),
 2:dict(style='sand-seal side bolt',bolt=['Bolt_Lug'],gate=['Receiver_Plates_L'],energy=[],pivot=(8,3,-5),port=(-3,2,-4.5),travel=9,lift=34,gate_axis='y',gate_angle=58,prop_scale=.25,prop_entry=(17,-5,-12),hand_roll=-25),
 3:dict(style='frost straight-pull',bolt=['Bolt_Housing','Bolt_Pull'],gate=['White_Receiver_Plates_L'],energy=[],pivot=(8,3,-5),port=(-3,2,-4.5),travel=8.5,lift=18,gate_axis='y',gate_angle=-62,prop_scale=.26,prop_entry=(15,-7,-12),hand_roll=-13),
 4:dict(style='reliquary latch',bolt=[],gate=['Reliquary_Magazine','Magazine_Seals_L','Magazine_Seals_R'],energy=['Reliquary_Core_L','Reliquary_Core_R'],pivot=(5,2,-5),port=(-3,-3,-5),travel=6,lift=40,gate_axis='z',gate_angle=42,prop_scale=.27,prop_entry=(10,-14,-12),hand_roll=18),
 5:dict(style='rail-slug feed and coil prime',bolt=[],gate=['Battery_Box','Battery_Cage_L','Battery_Cage_R','Battery_Hazard_L','Battery_Hazard_R'],energy=['Rail_Core']+[f'Coil_Windings_{i}_{s}' for i in range(4) for s in ['L','R']],pivot=(4,3,-5),port=(-3,-2,-5),travel=7,lift=20,gate_axis='x',gate_angle=-30,prop_scale=.26,prop_entry=(16,-13,-13),hand_roll=-30),
 6:dict(style='prism feed and focus recharge',bolt=[],gate=['Power_Cell','Cell_Crystal_L','Cell_Crystal_R','Cell_End_Cap'],energy=['Muzzle_Focusing_Crystal'],pivot=(3,3,-5),port=(-3,-2,-5),travel=6,lift=32,gate_axis='z',gate_angle=30,prop_scale=.27,prop_entry=(14,-15,-11),hand_roll=24),
 7:dict(style='penance eye-cage latch',bolt=['Bolt_Prayer_Lever'],gate=[f'Silver_Cage_Bar_{i}_{s}' for i in range(2) for s in ['L','R']],energy=['Caged_Violet_Eye_L','Caged_Violet_Eye_R'],pivot=(8,2,-6),port=(-2,1,-5),travel=6.5,lift=38,gate_axis='x',gate_angle=-75,prop_scale=.26,prop_entry=(13,-10,-14),hand_roll=28),
 8:dict(style='induction breech and sabot feed',bolt=['Crystal_Breech'],gate=['Bullpup_Magazine','Magazine_Chrome_Foot'],energy=['Shroud_Crystal_Insert_L','Shroud_Crystal_Insert_R'],pivot=(-5,3,-4),port=(-3,1,-5),travel=9.5,lift=16,gate_axis='z',gate_angle=-14,prop_scale=.27,prop_entry=(17,-10,-12),hand_roll=-35),
 9:dict(style='skybound carved bolt',bolt=['Bolt_Red_Lever','Blue_Steel_Breech'],gate=['Artifact_Pale_Flanges_L'],energy=['Artifact_Green_Eye'],pivot=(8,3,-5),port=(-3,2,-4.5),travel=7,lift=30,gate_axis='y',gate_angle=52,prop_scale=.26,prop_entry=(14,-9,-12),hand_roll=12),
}


def cache_baselines():
    manifest=CACHE/'artcatalog.json'
    if manifest.exists():return json.loads(manifest.read_text())
    catalog=json.loads((ART/'artcatalog.json').read_text())
    for a in catalog['assets']:
        paths=['Common/'+a['model'],'Common/'+a['texture'],a['blockbench'],a['scene']]
        for relative in paths:
            source=ART/relative;dest=CACHE/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            if relative.endswith('.blockymodel'):
                d=json.loads(source.read_text());assert not any(n['name'].startswith('RS_Reload_') for n in traverse(d['nodes'])),'Refusing to cache an already-rigged model'
            shutil.copyfile(source,dest)
    CACHE.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps(catalog,indent=2)+'\n')
    return catalog


def idle_interfaces():
    dest=ART/'source/reload-idle-interface.json'
    if dest.exists():return json.loads(dest.read_text())
    out={}
    with ZipFile(os.environ['HYTALE_ASSETS_ZIP']) as z:
        for view,path in [('FPS','Idle_FPS'),('TPS','Idle')]:
            d=json.loads(z.read(f'Common/Characters/Animations/Items/Dual_Handed/Rifle/{path}.blockyanim'))
            out[view]={}
            for name,t in d['nodeAnimations'].items():
                if name not in ['R-Arm','L-Arm','R-Forearm','L-Forearm','R-Hand','L-Hand','Chest','Belly','Head']:continue
                out[view][name]={key:deepcopy(values[0]['delta']) for key,values in t.items() if values and key in ['position','orientation']}
    dest.write_text(json.dumps(dict(source='Native Rifle idle pose interface only; all reload trajectories are original',**out),indent=2)+'\n')
    return out


def make_hardware(name,center,size,tile,visible=False):
    uv={face:dict(offset=dict(x=tile,y=512),mirror=dict(x=False,y=False),angle=0) for face in FACE_SIZE}
    return dict(id='0',name=name,position=vec(center),orientation=dict(IDENTITY),shape=dict(type='box',offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(size=vec(size),isPiece=False),textureLayout=uv,unwrapMode='custom',visible=visible,doubleSided=False,shadingMode='flat'),children=[])


def group_parts(base,names,name,pivot):
    selected=[n for n in base['children'] if n['name'] in names]
    assert {n['name'] for n in selected}==set(names),('Unknown authored rig part',name,set(names)-{n['name'] for n in selected})
    base['children']=[n for n in base['children'] if n['name'] not in names]
    for n in selected:n['position']=vec([n['position'][axis]-pivot[i] for i,axis in enumerate('xyz')])
    g=bone(name,pivot,children=selected);base['children'].append(g);return g


def player_tracks(clip,view,rig,duration,interface):
    # Native idle transforms are pose interfaces. Every time-varying reach, pull,
    # insertion, wrist turn and return below is newly authored for this rig.
    phases=[0,.10,.22,.33,.46,.60,.73,.84,.94,1]
    activity=[0,.25,1,.8,1,.65,.9,.55,.15,0]
    for name,baseline in interface[view].items():
        for prop,value in baseline.items():
            if prop=='position':
                points=[]
                for p,f in zip(phases,activity):
                    extra=[0,0,0]
                    if name=='L-Arm':extra=[f*(4+rig['hand_roll']*.08),f*(-4 if view=='FPS' else -2),f*(-7 if p<.35 else 3)]
                    if name=='R-Arm':extra=[f*(-1.5),f*(-1.4),f*(-1)]
                    points.append(kf(p*duration,vec([value[k]+extra[i] for i,k in enumerate('xyz')])))
                track(clip,name)['position']=points
            elif prop=='orientation':
                points=[]
                for p,f in zip(phases,activity):
                    axis='x';angle=0
                    if name=='L-Arm':angle=f*(-15 if view=='FPS' else -10)
                    elif name=='L-Forearm':angle=f*(-22 if p<.35 else -10)
                    elif name=='L-Hand':axis='z';angle=f*rig['hand_roll']
                    elif name=='R-Hand':axis='z';angle=f*(-8 if view=='FPS' else -5)
                    elif name=='R-Arm':axis='y';angle=f*3
                    elif name=='Chest':axis='z';angle=f*(-3)
                    elif name=='Belly':axis='y';angle=f*2
                    elif name=='Head':angle=f*5
                    points.append(kf(p*duration,qmul(value,qaxis(axis,angle))))
                track(clip,name)['orientation']=points


def weapon_tracks(clip,rig,duration,props,hardware,capacity,scale):
    travel=rig['travel']*scale[0]
    position_keys(clip,'RS_Reload_Bolt',[(0,(0,0,0)),(.12,(0,0,0)),(.25,(travel,0,0)),(.74,(travel,0,0)),(.86,(0,0,0)),(1,(0,0,0))],duration)
    rotation_keys(clip,'RS_Reload_Bolt',[(0,0),(.10,0),(.18,rig['lift']),(.78,rig['lift']),(.91,0),(1,0)],duration,'x')
    rotation_keys(clip,'RS_Reload_Gate',[(0,0),(.15,0),(.29,rig['gate_angle']),(.74,rig['gate_angle']),(.89,0),(1,0)],duration,rig['gate_axis'])
    position_keys(clip,'RS_Reload_Gate',[(0,(0,0,0)),(.25,(0,-3*scale[1],-2*scale[2])),(.73,(0,-3*scale[1],-2*scale[2])),(.90,(0,0,0)),(1,(0,0,0))],duration)
    for j,prop in enumerate(props):
        start,end=(.28,.65) if capacity==1 else ((.26,.49) if j==0 else (.49,.73))
        outside=[rig['prop_entry'][a]*scale[a] for a in range(3)]
        position_keys(clip,prop['name'],[(0,(0,0,0)),(start,outside),(start+(end-start)*.45,(outside[0]*.4,outside[1]*.3,outside[2]*.5)),(end,(0,0,0)),(1,(0,0,0))],duration)
        rotation_keys(clip,prop['name'],[(0,0),(start,-28+j*8),(end,0),(1,0)],duration,'y')
        for n in traverse(prop['children']):visibility_keys(clip,n['name'],start,end+.015,duration)
    for n in hardware:visibility_keys(clip,n['name'],.17,.88,duration)
    if rig['energy']:
        rotation_keys(clip,'RS_Reload_Energy',[(0,0),(.35,0),(.60,12),(.78,-8),(.91,0),(1,0)],duration,'x')


def bb_export(model,texture,clip,entry,animation_tag='Reload'):
    # Editable neutral Base-space rig, with real groups and weapon animation keys.
    elements=[];groups=[];by_name={};base=model['nodes'][0]['children'][0]['children'][0]
    def visit(n,parent_origin=(0,0,0),parent_children=None,parent_rotation=None):
        origin=np.array(parent_origin)+np.array([n['position'][k] for k in 'xyz'])
        group=dict(name=n['name'],uuid=uid(entry['item_id']+'/'+n['name']),origin=origin.tolist(),rotation=qeuler(n['orientation']),children=[],is_piece=n['shape']['settings'].get('isPiece',False))
        by_name[n['name']]=group['uuid'];(groups if parent_children is None else parent_children).append(group)
        s=n['shape']
        if s['type']=='box':
            center=origin+np.array([s['offset'][k] for k in 'xyz']);size=np.array([s['settings']['size'][k]*s['stretch'][k] for k in 'xyz'])
            faces={}
            for face,(i,j) in FACE_SIZE.items():
                p=s['textureLayout'][face]['offset'];faces[BB_FACE[face]]=dict(uv=[p['x'],p['y'],p['x']+s['settings']['size']['xyz'[i]],p['y']+s['settings']['size']['xyz'[j]]],texture=0)
            e=dict(name=n['name']+'_Geo',uuid=uid(entry['item_id']+'/'+n['name']+'/cube'),type='cube',origin=origin.tolist(),faces=faces,rotation=[0,0,0],shading_mode=s['shadingMode'],double_sided=False,visibility=s['visible'],autouv=0)
            e['from']=(center-size/2).tolist();e['to']=(center+size/2).tolist();elements.append(e);group['children'].append(e['uuid'])
        for c in n.get('children',[]):visit(c,origin,group['children'])
    # Keep native Handle grip in its correct neutral Base-space relation.
    for n in base['children']:visit(n)
    handle=model['nodes'][0]['children'][0];h=deepcopy(handle);h['children']=[];h['position']=vec((11.098076,-13.222432,0));h['orientation']=qaxis('z',30);visit(h)
    animation=dict(name=animation_tag+'_weapon_mechanics',uuid=uid(entry['item_id']+'/'+animation_tag+'/animation'),loop='once',override=False,length=clip['duration']/FPS,snapping=FPS,animators={})
    for name,channels in clip['nodeAnimations'].items():
        if name not in by_name:continue
        keys=[]
        for key,values in channels.items():
            for v in values:
                if key=='position':channel_name='position';data=vec([v['delta'][k] for k in 'xyz'])
                elif key=='orientation':channel_name='rotation';data=vec(qeuler(v['delta']))
                elif key=='shapeVisible':channel_name='visibility';data=dict(visibility=v['delta'])
                elif key=='shapeStretch':channel_name='scale';data=v['delta']
                else:continue
                keys.append(dict(channel=channel_name,data_points=[data],time=v['time']/FPS,interpolation='linear' if v['interpolationType']=='linear' else 'catmullrom',uuid=uid(entry['item_id']+'/'+animation_tag+'/'+name+'/'+key+'/'+str(v['time']))))
        animation['animators'][by_name[name]]=dict(name=name,type='bone',keyframes=keys)
    image=Image.open(texture)
    return dict(meta=dict(format_version='4.10',model_format='free',box_uv=False),name=entry['name']+' reload rig',resolution=dict(width=image.width,height=image.height),elements=elements,outliner=groups,animations=[animation],textures=[dict(name=texture.name,path=str(texture),id='0',uuid=uid(entry['item_id']+'/texture'),source='data:image/png;base64,'+base64.b64encode(texture.read_bytes()).decode(),width=image.width,height=image.height,uv_width=image.width,uv_height=image.height,internal=True,saved=True)])


def main():
    baseline=cache_baselines();interface=idle_interfaces();spec=json.loads((ROOT/'research/progression-spec.json').read_text());tiers={w['id']:w for w in spec['tiers']};ammo_catalog=json.loads((ROOT/'ammo-art/artcatalog.json').read_text());ammo_by_id={a['item_id']:a for a in ammo_catalog['assets']};result=[]
    for original in baseline['assets']:
        a=deepcopy(original);w=tiers[a['item_id']];reload=w['reload'];index=a['tier'];rig=RIGS[index];scale=a['body_fit_scale'];m=json.loads((CACHE/'Common'/a['model']).read_text());base=m['nodes'][0]['children'][0]['children'][0]
        native_idle=deepcopy(m);old_texture=Image.open(CACHE/'Common'/a['texture']).convert('RGBA');texture=Image.new('RGBA',(512,1024));texture.paste(old_texture,(0,0))
        ammo=ammo_by_id[w['ammo']];am=json.loads((ROOT/'ammo-art/Common'/ammo['model']).read_text());ammo_texture=Image.open(ROOT/'ammo-art/Common'/ammo['texture']).convert('RGBA');texture.paste(ammo_texture,(0,512))
        theme=json.loads((CACHE/a['scene']).read_text())['theme'];draw=ImageDraw.Draw(texture)
        for tile,color in [(288,theme['colors']['steel']),(320,theme['colors']['dark']),(352,theme['colors']['trim'])]:
            draw.rectangle((tile,512,tile+31,543),fill=color)
            for y in range(513,543,4):draw.line((tile,y,tile+31,y),fill=theme['colors']['edge'])
        pivot=[rig['pivot'][i]*scale[i] for i in range(3)];port=[rig['port'][i]*scale[i] for i in range(3)]
        bolt=group_parts(base,rig['bolt'],'RS_Reload_Bolt',pivot);gate=group_parts(base,rig['gate'],'RS_Reload_Gate',port)
        energy=group_parts(base,rig['energy'],'RS_Reload_Energy',port)
        hardware=[]
        shuttle=make_hardware('RS_Reload_Bolt_Shuttle',(-4,1,0),(8,2,5),288);bolt['children'].append(shuttle);hardware.append(shuttle)
        recess=make_hardware('RS_Reload_Open_Port',port,(10,5,1),320);base['children'].append(recess);hardware.append(recess)
        props=[]
        for j in range(reload['capacity']):
            prop=bone('RS_Reload_Cartridge_'+str(j+1),port,qaxis('z',90));prop['children']=deepcopy(am['nodes'])
            for n in traverse(prop['children']):
                n['name']=f"RS_Reload_Round{j+1}_"+n['name'];n['position']=vec([n['position'][axis]*rig['prop_scale'] for axis in 'xyz']);n['shape']['visible']=False
                n['shape']['stretch']=vec([n['shape']['stretch'][axis]*rig['prop_scale'] for axis in 'xyz'])
                for uv in n['shape']['textureLayout'].values():uv['offset']['y']+=512
            base['children'].append(prop);props.append(prop)
        for n,node in enumerate(traverse(m['nodes']),1):node['id']=str(n)
        duration=round(reload['durationSeconds']*FPS);clips={}
        slug=w['id'].removeprefix('Weapon_Crossbow_')
        for view in ['FPS','TPS']:
            clip=dict(formatVersion=1,duration=duration,holdLastKeyframe=False,nodeAnimations={});player_tracks(clip,view,rig,duration,interface);weapon_tracks(clip,rig,duration,props,hardware,reload['capacity'],scale);clips[view]=clip
            path=ART/'Common/Characters/Animations/Items/Dual_Handed/RangerSnipers'/slug/f'Reload_{view}.blockyanim';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(clip,indent=2)+'\n')
            if reload['capacity']==2:
                single=dict(formatVersion=1,duration=duration,holdLastKeyframe=False,nodeAnimations={});player_tracks(single,view,rig,duration,interface);weapon_tracks(single,rig,duration,props[:1],hardware,1,scale)
                for n in traverse(props[1]['children']):track(single,n['name'])['shapeVisible']=[kf(0,False,'linear'),kf(duration,False,'linear')]
                clips['Single_'+view]=single
                (path.parent/f'ReloadSingle_{view}.blockyanim').write_text(json.dumps(single,indent=2)+'\n')
        model_path=ART/'Common'/a['model'];model_path.write_text(json.dumps(m,indent=2)+'\n');texture_path=ART/'Common'/a['texture'];texture.save(texture_path)
        bb=bb_export(m,texture_path,clips['FPS'],a)
        if reload['capacity']==2:
            single_bb=bb_export(m,texture_path,clips['Single_FPS'],a,'ReloadSingle')['animations'][0];bb['animations'].append(single_bb)
        (ART/a['blockbench']).write_text(json.dumps(bb,indent=2)+'\n')
        player_asset=dict(Parent='Rifle',Animations={reload['animationId']:dict(FirstPerson=f'Characters/Animations/Items/Dual_Handed/RangerSnipers/{slug}/Reload_FPS.blockyanim',ThirdPerson=f'Characters/Animations/Items/Dual_Handed/RangerSnipers/{slug}/Reload_TPS.blockyanim',ThirdPersonMoving=f'Characters/Animations/Items/Dual_Handed/RangerSnipers/{slug}/Reload_TPS.blockyanim',Speed=1,Looping=False,BlendingDuration=.08,ClipsGeometry=True)})
        if reload['capacity']==2:
            player_asset['Animations']['ReloadSingle']=deepcopy(player_asset['Animations'][reload['animationId']])
            for key in ['FirstPerson','ThirdPerson','ThirdPersonMoving']:player_asset['Animations']['ReloadSingle'][key]=player_asset['Animations']['ReloadSingle'][key].replace('/Reload_','/ReloadSingle_')
        server=ART/'generated/Server/Item/Animations'/f"{reload['playerAnimationsId']}.json";server.parent.mkdir(parents=True,exist_ok=True);server.write_text(json.dumps(player_asset,indent=2)+'\n')
        a['cube_count']=sum(n['shape']['type']=='box' for n in traverse(m['nodes']));a['texture_size']=[512,1024]
        a['reload']=dict(**reload,fps=FPS,frames=duration,rig_style=rig['style'],ammo_prop=ammo['item_id'],first_person=player_asset['Animations'][reload['animationId']]['FirstPerson'],third_person=player_asset['Animations'][reload['animationId']]['ThirdPerson'])
        if reload['capacity']==2:a['reload']['partial_animation']=dict(animationId='ReloadSingle',first_person=player_asset['Animations']['ReloadSingle']['FirstPerson'],third_person=player_asset['Animations']['ReloadSingle']['ThirdPerson'],durationSeconds=reload['durationSeconds'],visible_cartridges=1)
        if index in (5,6):a['fullbright_parts']=[n['name'] for n in traverse(m['nodes']) if n['shape']['type']=='box' and n['shape']['shadingMode']=='fullbright']
        result.append(a)
    catalog=deepcopy(baseline);catalog['assets']=result;catalog['reload_rigs']=True;(ART/'artcatalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    (ART/'reloadcatalog.json').write_text(json.dumps(dict(fps=FPS,original_motion=True,baseline_cache='source/reload-baselines',rifles=[dict(item_id=a['item_id'],name=a['name'],**a['reload']) for a in result]),indent=2)+'\n')
    print(json.dumps(dict(rifles=len(result),clips=sum(4 if a['reload']['capacity']==2 else 2 for a in result),player_animation_assets=len(result),durations=[a['reload']['durationSeconds'] for a in result])))


if __name__=='__main__':main()
