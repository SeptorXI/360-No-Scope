"""Suppress the native wielding progress shield during gun aim-down-sights.

RSAim derives from native Wielding so held secondary keeps zoom and movement
effects active while primary can fire. Wielding inherits the abstract charging
codec, which omits DisplayProgress. A subclass sets that flag in code instead.
"""
from pathlib import Path
from copy import deepcopy
import json

ROOT=Path(__file__).resolve().parent


def apply(pack):
    pack=Path(pack).resolve()
    if not pack.is_relative_to(ROOT):raise ValueError('Aim overlay is limited to the isolated arsenal staging directory')
    directory=pack/'Server/Item/RootInteractions/RangerSnipers'
    paths=sorted(directory.glob('Root_RS_*_ADS.json'))
    if len(paths)!=54:raise ValueError(f'Expected54 gun ADS roots, found{len(paths)}')
    changed=[];verified=[]
    for path in paths:
        before=json.loads(path.read_text(encoding='utf-8-sig'))
        interactions=before.get('Interactions',[])
        if len(interactions)!=1 or not isinstance(interactions[0],dict) or interactions[0].get('Type') not in ('Wielding','RSAim'):
            raise ValueError('Unexpected gun ADS interaction '+str(path))
        after=deepcopy(before)
        after['Interactions'][0]['Type']='RSAim'
        # Remove only the unshipped exploratory flag: native Wielding ignores it.
        after['Interactions'][0].pop('DisplayProgress',None)
        restored=deepcopy(after)
        restored['Interactions'][0]['Type']=before['Interactions'][0]['Type']
        if 'DisplayProgress' in before['Interactions'][0]:
            restored['Interactions'][0]['DisplayProgress']=before['Interactions'][0]['DisplayProgress']
        if restored!=before:raise AssertionError('Aim overlay changed more than the cosmetic indicator')
        relative=path.relative_to(pack).as_posix()
        if before!=after:
            path.write_text(json.dumps(after,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            changed.append(relative)
        verified.append(relative)
    return {'purpose':'Hide native Wielding shield/progress indicator during gun aiming',
            'roots':len(paths),'field':'/Interactions/0/Type','value':'RSAim',
            'changedPaths':changed,'verifiedPaths':verified,
            'preserved':'Wielding hold behavior, ADS rules, magnification, sensitivity, overlay texture, movement and sprint settings are unchanged.',
            'clientCheck':'The native packet flag is verified separately; scope appearance still needs a client check.'}


if __name__=='__main__':
    result=apply(ROOT/'pack')
    (ROOT/'qa/aiming-fix-static.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'roots':result['roots'],'changed':len(result['changedPaths']),'field':result['field'],'value':'RSAim'}))
