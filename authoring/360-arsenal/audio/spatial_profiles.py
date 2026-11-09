"""Bind the exact authored tail events to the existing 54 projectile markers."""
from pathlib import Path
import json

PROJECT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def generate():
    core=read(PROJECT/'audio/cinematic-core/catalog.json')
    arsenal=read(PROJECT/'audio/cinematic-arsenal/catalog.json')
    originals=read(PROJECT/'baseline/sniper-spec.json')['tiers']
    weapons=originals+read(PROJECT/'content/arsenal-spec.json')['tiers']
    by_id={t['id']:t for t in weapons};normal={};special={};delays={}
    for catalog in (core,arsenal):
        assert catalog['version']=='2.0.5'
        for row in catalog['ownerTailBindings']:
            weapon=row['itemId'];action=row['action'];event=row['ownerTailEventId']
            assert weapon in by_id and event and row['worldTailDelaySeconds']>=0
            if action=='Fire':
                assert weapon not in normal,'Duplicate normal tail '+weapon
                normal[weapon]=event
            elif action=='SpecialFire':
                source=by_id[weapon]['audio']['events']['SpecialFire']['Local']
                assert source not in special,'Duplicate special tail '+source
                special[source]=event
            else:raise ValueError('Unsupported tail action '+action)
            delays[event]=row['worldTailDelaySeconds']
    assert len(weapons)==len(normal)==54 and len(special)==2
    rows=[]
    for weapon in weapons:
        slug=weapon['id'].removeprefix('Weapon_Crossbow_')
        row={'WeaponId':weapon['id'],'FlightMarker':'Root_RS_'+slug+'_FlightOrigin','PrimaryEventId':normal[weapon['id']]}
        if weapon.get('ability'):
            row['AbilityEventId']=special[weapon['audio']['events']['SpecialFire']['Local']]
        rows.append(row)
    assert len({r['FlightMarker']for r in rows})==54 and sum('AbilityEventId'in r for r in rows)==12
    result={'Version':1,'Profiles':rows,'Scope':'Optional owner-only positional tail; native Local dry and World report routes remain responsible for the initial shot.'}
    target=PROJECT/'generated/ranger-snipers-owner-tail-profiles.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return target,result

if __name__=='__main__':
    path,data=generate();print(json.dumps({'profiles':len(data['Profiles']),'abilities':sum('AbilityEventId'in r for r in data['Profiles']),'path':str(path)}))
