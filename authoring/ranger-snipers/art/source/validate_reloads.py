"""Offline checks of original reload rigs, clips, source and idle preservation."""
from pathlib import Path
import hashlib,json,math
import numpy as np
from PIL import Image
import generate_reloads as g

ART=g.ART
def matrix(n):
    m=np.eye(4);m[:3,:3]=g.qmat(n['orientation']);m[:3,3]=[n['position'][k] for k in 'xyz'];return m
def world_nodes(model):
    out={}
    def walk(n,p):
        m=p@matrix(n);out[n['name']]=(n,m)
        for c in n.get('children',[]):walk(c,m)
    for n in model['nodes']:walk(n,np.eye(4))
    return out
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cat=json.loads((ART/'artcatalog.json').read_text());baseline=json.loads((g.CACHE/'artcatalog.json').read_text());old={a['item_id']:a for a in baseline['assets']};interface=g.idle_interfaces();reports=[];all_checks=0
    for a in cat['assets']:
        o=old[a['item_id']];before=json.loads((g.CACHE/'Common'/o['model']).read_text());m=json.loads((ART/'Common'/a['model']).read_text());bm=world_nodes(before);am=world_nodes(m);checks=0
        # Rest transforms/shapes of every preexisting part are byte-equivalent
        # in world space; adding parent groups must not move the idle weapon.
        for name,(n,transform) in bm.items():
            nn,at=am[name];assert np.allclose(transform,at,atol=1e-6),(a['name'],name,'rest transform');assert n['shape']==nn['shape'],(name,'shape changed');checks+=2
        for name in ['R-Attachment','Handle','Base','Energy_Core','Muzzle']:
            if name not in bm:continue
            assert bm[name][0]['position']==am[name][0]['position'] and bm[name][0]['orientation']==am[name][0]['orientation'];checks+=1
        texture=Image.open(ART/'Common'/a['texture']).convert('RGBA');oldtex=Image.open(g.CACHE/'Common'/o['texture']).convert('RGBA');assert texture.size==(512,1024);assert texture.crop((0,0,512,512)).tobytes()==oldtex.tobytes();checks+=2
        ids=set();cubes=0
        for name,(n,_) in am.items():
            assert n['id'] not in ids;ids.add(n['id']);assert abs(sum(n['orientation'][k]**2 for k in 'xyzw')-1)<1e-4
            s=n['shape'];checks+=2
            if s['type']!='box':continue
            cubes+=1;size=[s['settings']['size'][k] for k in 'xyz']
            for face,(i,j) in g.FACE_SIZE.items():
                uv=s['textureLayout'][face]['offset'];x,y=uv['x'],uv['y'];assert 0<=x<=texture.width-size[i] and 0<=y<=texture.height-size[j],(name,face,'UV bounds');assert texture.crop((x,y,x+size[i],y+size[j])).getextrema()[3]==(255,255);checks+=2
        assert cubes==a['cube_count']
        reload=a['reload'];player=json.loads((ART/'generated/Server/Item/Animations'/f"{reload['playerAnimationsId']}.json").read_text());assert player['Parent']=='Rifle';entry=player['Animations']['Reload'];assert entry['Speed']==1 and not entry['Looping'] and entry['ClipsGeometry'];checks+=3
        clips=[]
        tests=[(animation,view,key) for animation in player['Animations'] for view,key in [('FPS','FirstPerson'),('TPS','ThirdPerson')]]
        for animation,view,key in tests:
            entry=player['Animations'][animation]
            clip=json.loads((ART/'Common'/entry[key]).read_text());assert clip['duration']==round(reload['durationSeconds']*60) and not clip['holdLastKeyframe'];checks+=1
            allowed=set(am)|set(interface[view]);assert set(clip['nodeAnimations'])<=allowed
            animated_parts=[];keys_total=0
            for name,channels in clip['nodeAnimations'].items():
                for channel,keys in channels.items():
                    if not keys:continue
                    assert keys[0]['time']==0 and keys[-1]['time']==clip['duration'],(name,channel,'clip endpoints')
                    assert all(0<=k['time']<=clip['duration'] for k in keys) and all(keys[i]['time']<=keys[i+1]['time'] for i in range(len(keys)-1));checks+=2
                    for k in keys:
                        d=k['delta']
                        if isinstance(d,dict):
                            assert all(math.isfinite(x) for x in d.values());checks+=1
                            if channel=='orientation':assert abs(sum(v*v for v in d.values())-1)<1e-4;checks+=1
                    if name.startswith('RS_Reload_'):
                        if channel=='shapeVisible':assert keys[0]['delta'] is False and keys[-1]['delta'] is False
                        elif channel=='position':assert all(abs(v)<1e-7 for v in keys[0]['delta'].values()) and keys[-1]['delta']==keys[0]['delta']
                        elif channel=='orientation':assert abs(abs(keys[0]['delta']['w'])-1)<1e-7 and keys[-1]['delta']==keys[0]['delta']
                        animated_parts.append(name)
                    keys_total+=len(keys)
            assert 'L-Arm' in clip['nodeAnimations'] and 'R-Hand' in clip['nodeAnimations']
            visible_props={n.split('_')[2] for n,c in clip['nodeAnimations'].items() if n.startswith('RS_Reload_Round') and any(k['delta'] is True for k in c['shapeVisible'])}
            assert len(visible_props)==(1 if animation=='ReloadSingle' else reload['capacity']);checks+=1
            clips.append(dict(animation=animation,view=view,duration_frames=clip['duration'],duration_seconds=clip['duration']/60,tracks=len(clip['nodeAnimations']),keyframes=keys_total,weapon_parts=len(set(animated_parts)),visible_cartridges=len(visible_props)))
        # Prop geometry and pixels come from the matching newly authored ammo.
        ammo_catalog=json.loads((ART.parent/'ammo-art/artcatalog.json').read_text());ammo=next(x for x in ammo_catalog['assets'] if x['item_id']==reload['ammo_prop']);ammo_model=json.loads((ART.parent/'ammo-art/Common'/ammo['model']).read_text());ammo_tex=Image.open(ART.parent/'ammo-art/Common'/ammo['texture']).convert('RGBA');assert texture.crop((0,512,256,768)).tobytes()==ammo_tex.tobytes();checks+=1
        ammo_names={n['name'] for n in g.traverse(ammo_model['nodes'])}
        for j in range(reload['capacity']):
            prefix=f'RS_Reload_Round{j+1}_';props={n[len(prefix):]:v[0] for n,v in am.items() if n.startswith(prefix)};assert set(props)==ammo_names;assert all(n['shape']['visible'] is False for n in props.values());checks+=2
        bb=json.loads((ART/a['blockbench']).read_text());assert len(bb['elements'])==cubes and bb['resolution']==dict(width=512,height=1024) and len(bb['animations'])==(2 if reload['capacity']==2 else 1);checks+=3
        source_keys=[k['uuid'] for animation in bb['animations'] for animator in animation['animators'].values() for k in animator['keyframes']];assert len(source_keys)==len(set(source_keys));checks+=1
        for e in bb['elements']:
            name=e['name'].removesuffix('_Geo');assert e['shading_mode']==am[name][0]['shape']['shadingMode'];checks+=1
        all_checks+=checks;reports.append(dict(item_id=a['item_id'],name=a['name'],checks=checks,idle_parts_preserved=len(bm),visible_original_cubes=sum(v[0]['shape']['type']=='box' for v in bm.values()),total_cubes=cubes,ammo_prop=reload['ammo_prop'],prop_count=reload['capacity'],clips=clips))
    files={str(p.relative_to(ART)).replace('\\','/'):sha(p) for prefix in ['Common','generated/Server'] for p in sorted((ART/prefix).rglob('*')) if p.is_file()}
    report=dict(passed=True,checks=all_checks,rifles=len(reports),clips=sum(len(a['clips']) for a in reports),frame_rate=60,rigged_source_files=9,idle_geometry='Every original part retains its world rest transform, shape, original upper-atlas pixels and held anchors',scope='Offline generated-geometry/animation validation. Native asset-load and in-client avatar pose checks are separate.',assets=reports,files=files)
    (ART/'reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','checks','rifles','clips','frame_rate']}))
if __name__=='__main__':main()
