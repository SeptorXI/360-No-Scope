import os
"""Validate model structure, UV footprints, rig anchors, and native-envelope fit."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import itertools
import json
import math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
NATIVE='Common/Items/Hypixel/Minigames/GunPvP/Weapons/Assault_Rifles/Assault_Rifle.blockymodel'
ASSETS=Path(os.environ['HYTALE_ASSETS_ZIP'])
catalog=json.loads((ROOT/'artcatalog.json').read_text())


def transform(node):
    p,q=node['position'],node['orientation']
    x,y,z,w=[q[a] for a in 'xyzw']
    assert abs(sum(v*v for v in (x,y,z,w))-1)<.0001
    m=np.eye(4)
    m[:3,:3]=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
               [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
               [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
    m[:3,3]=[p[a] for a in 'xyz']
    return m


def model_bounds(d):
    root=d['nodes'][0];handle=root['children'][0];base=handle['children'][0]
    inv=np.linalg.inv(transform(root)@transform(handle)@transform(base))
    points=[]
    def walk(n,parent):
        m=parent@transform(n);s=n['shape'];sz=s['settings'].get('size')
        if sz and s.get('visible',True):
            for signs in itertools.product((-1,1),repeat=3):
                v=[s['offset'][a]+signs[i]*sz.get(a,0)*s['stretch'][a]/2 for i,a in enumerate('xyz')]+[1]
                points.append((inv@m@v)[:3])
        for c in n.get('children',[]):walk(c,m)
    walk(root,np.eye(4));a=np.array(points)
    return a.min(axis=0),a.max(axis=0)


with ZipFile(ASSETS) as z:native=json.loads(z.read(NATIVE))
native_lo,native_hi=model_bounds(native)
native_root=native['nodes'][0];native_handle=native_root['children'][0];native_base=native_handle['children'][0]
results=[]
for a in catalog['assets']:
    model=json.loads((ROOT/'Common'/a['model']).read_text())
    image=Image.open(ROOT/'Common'/a['texture'])
    icon=Image.open(ROOT/'Common'/a['icon'])
    root=model['nodes'][0];handle=root['children'][0];base=handle['children'][0]
    for original,authored in [(native_root,root),(native_handle,handle),(native_base,base)]:
        for field in ('name','position'):
            assert original[field]==authored[field],(a['name'],field)
        assert all(abs(original['orientation'][k]-authored['orientation'][k])<.00001 for k in 'xyzw')
    ids=set();count=0
    def inspect(n):
        global count
        assert n['id'] not in ids;ids.add(n['id'])
        assert n['shape']['type'] in ('box','none')
        s=n['shape']
        if s['type']=='box':
            count+=1
            size=[s['settings']['size'][k] for k in 'xyz']
            assert all(v>0 and math.isfinite(v) for v in size)
            assert all(s['stretch'][k]>0 for k in 'xyz')
            for face,(i,j) in {'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}.items():
                uv=s['textureLayout'][face]['offset'];x,y=uv['x'],uv['y']
                assert x>=0 and y>=0 and x+size[i]<=image.width and y+size[j]<=image.height
                tile=image.crop((x,y,x+size[i],y+size[j]));assert tile.getextrema()[3]==(255,255)
        for c in n.get('children',[]):inspect(c)
    inspect(root)
    assert count==a['cube_count']
    bb=json.loads((ROOT/a['blockbench']).read_text());assert len(bb['elements'])==count
    assert len({e['uuid'] for e in bb['elements']})==count
    assert icon.mode=='RGBA' and icon.size==(256,256)
    bbox=icon.getbbox();assert bbox and min(bbox)>0 and bbox[2]<256 and bbox[3]<256
    lo,hi=model_bounds(model)
    assert np.all(lo>=native_lo-.1) and np.all(hi<=native_hi+.1),(a['name'],lo,hi,native_lo,native_hi)
    results.append(dict(name=a['name'],cube_count=count,base_coordinate_bounds=dict(min=lo.round(5).tolist(),max=hi.round(5).tolist()),anchors='match native',uv='all six faces opaque and in atlas',icon='256x256 RGBA with transparent margins',blockbench='embedded texture, matching cube count'))
manifest=[]
for p in sorted((ROOT/'Common').rglob('*')):
    if p.is_file():manifest.append(dict(path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
preserved=ROOT/'original-six-preservation.json'
preservation=[]
legendary_baseline=ROOT/'legendary-preservation.json'
authorized=json.loads(legendary_baseline.read_text())['authorized_changed_art_indices'] if legendary_baseline.exists() else []
reload_changed={p for a in catalog['assets'] if a.get('reload') for p in ('Common/'+a['model'],'Common/'+a['texture'],a['blockbench'])}
if preserved.exists():
    for relative,expected in json.loads(preserved.read_text())['sha256'].items():
        if relative in reload_changed:continue
        if any(f'Tier{i:02}' in relative for i in authorized):continue
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected,('original changed',relative)
        preservation.append(relative)
protected=[]
if legendary_baseline.exists():
    for relative,expected in json.loads(legendary_baseline.read_text())['sha256'].items():
        if relative in reload_changed:continue
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected,('unrelated rifle changed',relative)
        protected.append(relative)
legendary=[]
for a in catalog['assets']:
    if a['tier'] not in (5,6):continue
    d=json.loads((ROOT/'Common'/a['model']).read_text());todo=list(d['nodes']);shades={};anchors={}
    while todo:
        n=todo.pop();todo+=n.get('children',[])
        if n['shape']['type']=='box':shades[n['name']]=n['shape']['shadingMode']
        if n['name'] in ('Energy_Core','Muzzle'):
            assert n['shape']['type']=='none';anchors[n['name']]=n['position']
    assert set(anchors)=={'Energy_Core','Muzzle'}
    bright={n for n,s in shades.items() if s=='fullbright'}
    assert bright==set(a['fullbright_parts']) and len(bright)<len(shades)/2
    bb=json.loads((ROOT/a['blockbench']).read_text())
    assert all(e['shading_mode']==shades[e['name'].removesuffix('_Geo')] for e in bb['elements'])
    legendary.append(dict(name=a['name'],unchanged_item_id=a['item_id'],fullbright_parts=sorted(bright),lit_structure_count=len(shades)-len(bright),anchors=anchors,editable_shading='CubeHytale.shading_mode matches native shadingMode'))
if reload_changed:
    from validate_reloads import main as validate_reloads
    validate_reloads()
report=dict(passed=True,original_six_unaffected_files_preserved=len(preservation),other_seven_files_preserved=len(protected),authorized_changed_art_indices=authorized,authorized_reload_model_texture_source_changes=len(reload_changed),reload_validation='reload-validation.json' if reload_changed else None,legendary_selected_shading=legendary,native_visible_bounds=dict(min=native_lo.round(5).tolist(),max=native_hi.round(5).tolist()),assets=results,files=manifest,scope='Offline art validation; player pose and client asset loading require game verification.')
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,models=len(results),runtime_files=len(manifest),report=str(ROOT/'validation.json'))))
