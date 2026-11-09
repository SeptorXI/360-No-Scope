"""Validate actual native model, UVs, texture/icon and measured placement bounds."""
from pathlib import Path
import hashlib,itertools,json,math,struct
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
AXES='xyz';FACES={'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}
def rotate(q,p):
    # Unit quaternion vector rotation, no third-party math library.
    u=[q[a] for a in AXES];s=q['w'];dot=sum(a*b for a,b in zip(u,p));uu=sum(a*a for a in u)
    cross=[u[1]*p[2]-u[2]*p[1],u[2]*p[0]-u[0]*p[2],u[0]*p[1]-u[1]*p[0]]
    return [2*dot*u[i]+(s*s-uu)*p[i]+2*s*cross[i] for i in range(3)]

def main():
    catalog=json.loads((ROOT/'bench-art-catalog.json').read_text());common=ROOT/'Common'
    modelpath=common/catalog['model'];texpath=common/catalog['texture'];iconpath=common/catalog['icon']
    model=json.loads(modelpath.read_text());texture=Image.open(texpath);icon=Image.open(iconpath)
    assert texture.mode=='RGBA' and texture.size==(512,512)
    assert icon.mode=='RGBA' and icon.size==(64,64)
    assert tuple(iconpath.read_bytes()[24:26])==(8,6), 'Native PNG must be RGBA8'
    assert icon.getbbox() and min(icon.getbbox()[:2])>=2 and max(icon.getbbox()[2:])<=62
    root=model['nodes'][0];assert root['name']=='R-Attachment' and root['position']==dict(x=-16,y=0,z=0)
    assert root['orientation']==dict(x=0,y=0,z=0,w=1)
    ids=set();names=set();corners=[];faces=0;glows=[]
    for node in [root]+root['children']:
        assert node['id'] not in ids and node['name'] not in names
        ids.add(node['id']);names.add(node['name'])
        shape=node['shape'];q=node['orientation'];assert abs(sum(v*v for v in q.values())-1)<1e-6
        if shape['type']=='none':continue
        assert shape['type']=='box' and shape['shadingMode'] in ('standard','fullbright')
        if shape['shadingMode']=='fullbright':glows.append(node['name'])
        size=[shape['settings']['size'][a] for a in AXES]
        assert all(isinstance(v,int) and v>0 for v in size)
        for face,(a,b) in FACES.items():
            uv=shape['textureLayout'][face]['offset'];u,v=uv['x'],uv['y'];w,h=size[a],size[b]
            assert isinstance(u,int) and isinstance(v,int) and 0<=u<u+w<=texture.width and 0<=v<v+h<=texture.height
            assert texture.crop((u,v,u+w,v+h)).getchannel('A').getextrema()==(255,255),(node['name'],face)
            faces+=1
        for signs in itertools.product((-.5,.5),repeat=3):
            p=rotate(q,[size[i]*signs[i] for i in range(3)])
            corners.append([p[i]+node['position'][a]+root['position'][a] for i,a in enumerate(AXES)])
    assert len(ids)==183 and faces==1092 and glows==catalog['fullbright_nodes']
    low=[min(p[i] for p in corners) for i in range(3)];high=[max(p[i] for p in corners) for i in range(3)]
    dimensions=[(b-a)/32 for a,b in zip(low,high)]
    assert abs(low[1])<1e-8 and dimensions[0]<=2.01 and dimensions[2]<=1.01 and dimensions[1]<=1.92
    contract=json.loads((ROOT/'art-contract.json').read_text());assert all(contract[k]==catalog[k] for k in ('model','texture','icon'))
    assert contract['hitboxType']=='RS_Gunsmith' and len(contract['hitbox']['Boxes'])==5
    for box in contract['hitbox']['Boxes']:
        assert all(box['Min'][a]<box['Max'][a] for a in 'XYZ')
    bb=json.loads((ROOT/'source/RS_Gunsmith_Bench.bbmodel').read_text());assert len(bb['elements'])==182
    for cube,node in zip(bb['elements'],root['children']):
        assert cube['origin']==[node['position']['x']-16,node['position']['y'],node['position']['z']]
        assert cube['shading_mode']==node['shape']['shadingMode']
    catalog['measured_bounds_model_units']=dict(min=low,max=high)
    catalog['measured_dimensions_blocks']=dimensions
    (ROOT/'bench-art-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    files=[modelpath,texpath,iconpath,ROOT/contract['hitboxPath']]
    result=dict(passed=True,boxes=182,uv_faces=faces,fullbright_nodes=len(glows),icon_size=list(icon.size),
                bounds_model_units=dict(min=low,max=high),dimensions_blocks=dimensions,
                native_alignment='R-Attachment(-16,0,0);32units/block;front-Z;matches native Weapon Bench convention',
                asset_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
