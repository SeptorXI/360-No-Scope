"""Validate native rigs, matching reload props, editable sources and final icons."""
from pathlib import Path
import base64,hashlib,json,math
from PIL import Image

ART=Path(__file__).resolve().parent

def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get('children',[]))

def main():
    catalog=json.loads((ART/'artcatalog.json').read_text());spec=json.loads((ART.parent/'content/arsenal-spec.json').read_text());tiers={w['id']:w for w in spec['tiers']};checks=[];failures=[];hashes={}
    def check(ok,label):
        checks.append(label)
        if not ok:failures.append(label)
    check(len(catalog['assets'])==45 and len(catalog['ammo'])==45,'45 guns and45 dedicatedammo')
    for a in catalog['assets']+catalog['ammo']:
        ident=a['item_id'];model=json.loads((ART/'Common'/a['model']).read_text());nodes=list(walk(model['nodes']));names=[n['name'] for n in nodes];texture=Image.open(ART/'Common'/a['texture']).convert('RGBA')
        check(len(names)==len(set(names)),ident+' unique namednative nodes')
        check(len({n['id'] for n in nodes})==len(nodes),ident+' unique nodeIDs')
        check(texture.size in ((512,512),(512,1024)),ident+' source atlasdimensions')
        for n in nodes:
            if n['shape']['type']!='box':continue
            s=n['shape'];size=s['settings']['size']
            check(all(size[k]>0 and int(size[k])==size[k] for k in 'xyz'),ident+'/'+n['name']+' integer positive cube')
            q=n['orientation'];check(abs(sum(q[k]**2 for k in 'xyzw')-1)<.0001,ident+'/'+n['name']+' normalizedrotation')
            for face,(i,j) in {'front':(0,1),'back':(0,1),'left':(2,1),'right':(2,1),'top':(0,2),'bottom':(0,2)}.items():
                uv=s['textureLayout'][face]['offset'];check(0<=uv['x']<=texture.width-size['xyz'[i]] and 0<=uv['y']<=texture.height-size['xyz'[j]],ident+'/'+n['name']+'/'+face+' UVbounds')
        bb=json.loads((ART/a['blockbench']).read_text());embedded=base64.b64decode(bb['textures'][0]['source'].split(',',1)[1]);check(embedded==(ART/'Common'/a['texture']).read_bytes(),ident+' editableembedded textureparity')
        check(len(bb['elements'])==sum(n['shape']['type']=='box' for n in nodes),ident+' editablecube count')
        icon=Image.open(ART/'Common'/a['icon']);check(icon.mode=='RGBA' and icon.size==(64,64),ident+'64x64RGBA icon')
        bounds=icon.getchannel('A').point(lambda v:255 if v>32 else 0).getbbox();check(bounds is not None and min(bounds[:2])>=2 and max(bounds[2:])<=62,ident+' iconnotblank andmargins')
        digest=hashlib.sha256((ART/'Common'/a['icon']).read_bytes()).hexdigest();check(digest not in hashes,ident+' unique icon');hashes[digest]=ident
        if ident not in tiers:continue
        w=tiers[ident];attach=model['nodes'][0];handle=attach['children'][0];base=handle['children'][0]
        check(attach['name']=='R-Attachment' and attach['position']==dict(x=0,y=18,z=-20),ident+' nativeattachment')
        check(handle['name']=='Handle' and handle['orientation']==dict(x=.18301,y=.68301,z=.18301,w=.68301),ident+' nativegrip')
        check(base['name']=='Base' and base['position']==dict(x=-3,y=16,z=0),ident+' nativebase')
        scene=json.loads((ART/a['scene']).read_text());corners=[]
        for p in scene['parts']:
            axes=[(axis,v) for axis,v in enumerate(p['rotation']) if v];axis,angle=axes[0] if axes else (2,0);c=math.cos(math.radians(angle));s=math.sin(math.radians(angle));j,k=((1,2),(2,0),(0,1))[axis]
            for x in (-.5,.5):
                for y in (-.5,.5):
                    for z in (-.5,.5):
                        v=[x*p['size'][0],y*p['size'][1],z*p['size'][2]];v[j],v[k]=c*v[j]-s*v[k],s*v[j]+c*v[k];corners.append([v[b]+p['center'][b] for b in range(3)])
        lo=[min(v[b] for v in corners) for b in range(3)];hi=[max(v[b] for v in corners) for b in range(3)]
        check(all(lo[b]>=(-49.5,-25,-4.7)[b] and hi[b]<=(30.2,14.2,4.7)[b] for b in range(3)),ident+' visiblegeometryfitsnativeenvelope')
        props=[n for n in nodes if n['name'].startswith('AS_Prop_') and n['shape']['type']=='box'];check(bool(props) and all(not n['shape']['visible'] for n in props),ident+' matchingpropshiddenatrest')
        visible_bright=[n for n in nodes if n['shape']['type']=='box' and n['shape']['visible'] and n['shape']['shadingMode']=='fullbright'];check(bool(visible_bright)==(w['quality']=='Legendary'),ident+' selectiveLegendaryglow')
        mapping=json.loads((ART/'generated/Server/Item/Animations'/f"{a['playerAnimationsId']}.json").read_text());check(mapping['Parent']=='Rifle',ident+' nativeRiflefamily')
        for action in ('Reload','Shoot'):
            for view,key in [('FPS','FirstPerson'),('TPS','ThirdPerson')]:
                clip=json.loads((ART/'Common'/mapping['Animations'][action][key]).read_text());duration=clip['duration'];check(duration>0 and not clip['holdLastKeyframe'],ident+'/'+action+'/'+view+' finiteclip')
                if action=='Reload':
                    check(duration==round(w['reload']['durationSeconds']*60),ident+'/'+view+' canonicalreloadduration')
                    for prop in props:
                        track=clip['nodeAnimations'][prop['name']]['shapeVisible'];check(track[0]['delta'] is False and track[-1]['delta'] is False and track[-1]['time']==duration,ident+'/'+view+'/'+prop['name']+' resetspropvisibility')
                    if w['family']=='shotgun' and w['artIndex'] not in (5,6):
                        p=next(p for p in props if p['name']=='AS_Prop_Case');track=clip['nodeAnimations'][p['name']]['shapeVisible'];check(sum(k['delta'] is True for k in track)==w['reload']['capacity'],ident+'/'+view+' visibleonefeedpershell')
                        for count,partial in a['reload']['partialAnimations'].items():
                            key='first_person' if view=='FPS' else 'third_person';part=json.loads((ART/'Common'/partial[key]).read_text());keys=part['nodeAnimations'][p['name']]['shapeVisible'];check(sum(k['delta'] is True for k in keys)==int(count) and part['duration']==duration,ident+'/'+view+'/Reload'+count+' exactpartialshellcount')
                for name,channels in clip['nodeAnimations'].items():
                    for kind,keys in channels.items():
                        if not keys:continue
                        check(all(0<=k['time']<=duration for k in keys) and all(a['time']<=b['time'] for a,b in zip(keys,keys[1:])),ident+'/'+action+'/'+view+'/'+name+'/'+kind+' orderedkeytimes')
        if w['quality']=='Legendary' and w['artIndex']==5:
            for key in ('FirstPerson','ThirdPerson'):
                charge=json.loads((ART/'Common'/mapping['Animations']['ShootFlintlockCharging'][key]).read_text());check(charge['duration']==max(6,round(w['ability']['chargeSeconds']*60)),ident+'/'+key+' chargeexactduration')
                check('AS_Character' in charge['nodeAnimations'],ident+'/'+key+' chargephysicalassembly')
                for name,channels in charge['nodeAnimations'].items():
                    for kind,keys in channels.items():
                        if keys and kind in ('position','orientation'):check(keys[0]['delta']==keys[-1]['delta'],ident+'/'+key+'/'+name+' chargeresets')
    clipcount=sum(4+2*len(a['reload']['partialAnimations'])+(2 if a['quality']=='Legendary' and a['artIndex']==5 else 0) for a in catalog['assets'])
    report=dict(passed=not failures,checks=len(checks),failures=failures,guns=45,ammo=45,clips=clipcount,inventoryIcons=90,scope='Offline native schema,editable parity, animationreset and renderedicon checks. Multiplayer heldalignment and audiovisualplaytest remain.',source='Original cube and procedural pixel art; no imported model geometry or raster artwork.')
    (ART/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 1 if failures else 0

if __name__=='__main__':raise SystemExit(main())
