"""Check native cuboid meshes, every UV, icon format, anchors and editable exports."""
from pathlib import Path
import hashlib,itertools,json,math
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
FACES={'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}

def main():
    c=json.loads((ROOT/'art-contract.json').read_text());rows=[];allfiles=[]
    assert len(c['assets'])==6
    assert {(a['style'],a['kind']) for a in c['assets']}==set(itertools.product(('Wood','Metal'),('stand','holder','rack')))
    for a in c['assets']:
        modelpath=ROOT/'Common'/a['model'];texturepath=ROOT/'Common'/a['texture'];iconpath=ROOT/'Common'/a['icon']
        model=json.loads(modelpath.read_text());tex=Image.open(texturepath);icon=Image.open(iconpath)
        assert tex.mode=='RGBA' and tex.size==(512,512)
        assert icon.mode=='RGBA' and icon.size==(64,64) and tuple(iconpath.read_bytes()[24:26])==(8,6)
        box=icon.getbbox();assert box and min(box[:2])>=2 and max(box[2:])<=62
        root=model['nodes'][0];assert root['name']=='R-Attachment' and root['position']==dict(x=-16,y=0,z=0)
        ids=set();names=set();faces=0
        for node in [root]+root['children']:
            assert node['id'] not in ids and node['name'] not in names
            ids.add(node['id']);names.add(node['name'])
            assert abs(sum(v*v for v in node['orientation'].values())-1)<1e-6
            shape=node['shape']
            if shape['type']=='none':continue
            assert shape['type']=='box' and shape['shadingMode']=='standard'
            size=[shape['settings']['size'][axis] for axis in 'xyz'];assert all(isinstance(v,int) and v>0 for v in size)
            for face,(x,y) in FACES.items():
                uv=shape['textureLayout'][face]['offset'];u,v=uv['x'],uv['y'];w,h=size[x],size[y]
                assert isinstance(u,int) and isinstance(v,int) and 0<=u<u+w<=512 and 0<=v<v+h<=512
                assert tex.crop((u,v,u+w,v+h)).getchannel('A').getextrema()==(255,255)
                faces+=1
        assert len(root['children'])==a['cubeCount'] and faces==a['cubeCount']*6
        bb=json.loads((ROOT/'source'/(a['id']+'.bbmodel')).read_text());assert len(bb['elements'])==a['cubeCount']
        scene=json.loads((ROOT/'source'/(a['id']+'.scene.json')).read_text())
        for node,part,cube in zip(root['children'],scene['parts'],bb['elements']):
            assert node['position']==dict(zip('xyz',part['center']))
            assert cube['origin']==[part['center'][0]-16,part['center'][1],part['center'][2]]
            assert cube['from']==[part['center'][i]-part['size'][i]/2+(-16 if i==0 else 0) for i in range(3)]
        expected={'stand':[[0,4,0]],'holder':[[0,12,8]],'rack':[[0,12,7],[0,30,7],[0,48,7]]}[a['kind']]
        assert a['displayAnchorsModelUnits']==expected
        assert a['displayAnchorsBlocks']==[[v/32 for v in row] for row in expected]
        assert a['entityAnchorsBeforeRotationBlocks']==[[(row[0]-16)/32,row[1]/32,row[2]/32] for row in expected]
        if a['kind']!='stand':
            for row in range(1 if a['kind']=='holder' else 3):
                assert any(p['name']==f'Hook_Seat_{row}_0' for p in scene['parts'])
        hit=json.loads((ROOT/a['hitboxPath']).read_text());assert hit==a['hitbox']
        for b in hit['Boxes']:assert all(b['Min'][axis]<b['Max'][axis] for axis in 'XYZ')
        assert all(v>0 for v in a['dimensionsBlocks'])
        assert a['dimensionsBlocks'][0] <= (1 if a['kind']=='stand' else 2)
        assert a['dimensionsBlocks'][1] <= 2.01
        allfiles.extend([modelpath,texturepath,iconpath,ROOT/a['hitboxPath']])
        rows.append(dict(id=a['id'],passed=True,cubes=a['cubeCount'],uvFaces=faces,iconSize=[64,64],dimensionsBlocks=a['dimensionsBlocks']))
    skeleton=c['equipmentSkeleton'];m=json.loads((ROOT/'Common'/skeleton['model']).read_text());bones=[]
    def walk(node):
        assert node['shape']['type']=='none';bones.append(node['name'])
        for child in node.get('children',[]):walk(child)
    for node in m['nodes']:walk(node)
    assert len(bones)==skeleton['boneCount'] and len(bones)==len(set(bones))
    for required in ('Head','Chest','Pelvis','R-Attachment','L-Attachment'):assert required in bones,(required,bones)
    for path in (skeleton['model'],skeleton['texture']):allfiles.append(ROOT/'Common'/path)
    allfiles.append(ROOT/skeleton['assetPath'])
    result=dict(passed=True,assets=rows,totalCuboids=sum(a['cubes'] for a in rows),equipmentBoneCount=len(bones),
                assetSHA256={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in allfiles},
                scope='Offline model/UV/source/icon contract validation. Native loading and equipment rendering are verified separately.')
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='assetSHA256'}))

if __name__=='__main__':main()
