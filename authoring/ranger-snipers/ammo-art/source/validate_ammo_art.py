"""Validate all new ammunition assets, and prove existing rifle art is unchanged."""
from pathlib import Path
import hashlib,itertools,json,math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'artcatalog.json').read_text());results=[];all_ids=set()
for a in catalog['assets']:
    assert a['item_id']==a['ammo_id'] and a['item_id'] not in all_ids;all_ids.add(a['item_id'])
    model=json.loads((ROOT/'Common'/a['model']).read_text());texture=Image.open(ROOT/'Common'/a['texture'])
    bb=json.loads((ROOT/a['source']).read_text());scene=json.loads((ROOT/a['scene']).read_text());icon=Image.open(ROOT/'Common'/a['icon'])
    assert model['format']=='character' and len(model['nodes'])==a['cube_count']==len(bb['elements'])==len(scene['parts'])<255
    assert len({n['id'] for n in model['nodes']})==len(model['nodes'])
    assert len({n['name'] for n in model['nodes']})==len(model['nodes'])
    assert len({n['uuid'] for n in bb['elements']})==len(model['nodes'])
    points=[];fullbright=[];uv_count=0
    for n,e,p in zip(model['nodes'],bb['elements'],scene['parts']):
        assert n['name']==e['name']==p['name'];s=n['shape'];sz=[s['settings']['size'][k] for k in 'xyz']
        assert all(v>0 and math.isfinite(v) for v in sz) and s['type']=='box'
        assert s['shadingMode']==e['shading_mode']==p['shading_mode']
        if s['shadingMode']=='fullbright':fullbright.append(n['name'])
        for face,(i,j) in {'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}.items():
            o=s['textureLayout'][face]['offset'];x,y=o['x'],o['y'];w,h=sz[i],sz[j]
            assert x>=0 and y>=0 and x+w<=texture.width and y+h<=texture.height
            assert texture.crop((x,y,x+w,y+h)).getextrema()[3]==(255,255);uv_count+=1
        q=n['orientation'];x,y,z,w=[q[k] for k in 'xyzw'];assert abs(x*x+y*y+z*z+w*w-1)<1e-6
        rot=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
        for signs in itertools.product((-.5,.5),repeat=3):points.append(rot@np.array([signs[i]*sz[i] for i in range(3)])+np.array(p['center']))
    assert set(fullbright)==set(a['fullbright_parts'])
    assert len(fullbright)<len(model['nodes'])/2
    assert not fullbright or a['index'] in (5,6)
    assert icon.mode=='RGBA' and icon.size==(256,256);bbox=icon.getbbox()
    assert bbox and min(bbox)>0 and bbox[2]<256 and bbox[3]<256
    array=np.array(points);results.append(dict(index=a['index'],item_id=a['item_id'],name=a['name'],rifle_id=a['rifle_id'],cubes=len(model['nodes']),uv_faces=uv_count,fullbright_parts=fullbright,bounds=dict(min=array.min(axis=0).round(5).tolist(),max=array.max(axis=0).round(5).tolist()),editable_source_matches=True,transparent_icon_margins=True))
files=[]
for p in sorted((ROOT/'Common').rglob('*')):
    if p.is_file():files.append(dict(path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
rifle_root=ROOT.parent/'art';rifle_validation=json.loads((rifle_root/'validation.json').read_text())
for f in rifle_validation['files']:assert hashlib.sha256((rifle_root/f['path']).read_bytes()).hexdigest()==f['sha256'],('rifle art changed',f['path'])
protected=json.loads((rifle_root/'legendary-preservation.json').read_text())['sha256']
for f,expected in protected.items():assert hashlib.sha256((rifle_root/f).read_bytes()).hexdigest()==expected,('rifle source/preview changed',f)
report=dict(passed=True,original_art=True,models=len(results),runtime_files=len(files),cube_uv_faces=sum(a['uv_faces'] for a in results),unchanged_rifle_runtime_files=len(rifle_validation['files']),unchanged_protected_rifle_source_and_preview_files=len(protected),assets=results,files=files,scope='Offline native cube/UV/source/render checks. Item recipes, ammo family tags, firing stats, client loading and actual combat belong to the assembled-pack tests.')
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','models','runtime_files','cube_uv_faces','unchanged_rifle_runtime_files']}))
