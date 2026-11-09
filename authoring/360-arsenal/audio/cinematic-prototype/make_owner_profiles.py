from pathlib import Path
from zipfile import ZipFile
import json
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]

def main():
    tiers=[]
    for p in [PROJECT/'baseline/sniper-spec.json',PROJECT/'content/arsenal-spec.json']:
        tiers+=json.loads(p.read_text(encoding='utf-8-sig'))['tiers']
    specs={t['id']:t for t in tiers}
    with ZipFile(PROJECT/'release/360-No-Scope-2.0.4.jar') as z:
        source=json.loads(z.read('ranger-snipers-reload-profiles.json'))['Profiles']
    rows=[]
    for p in source:
        t=specs[p['WeaponId']];events=t['audio']['events']
        r={'WeaponId':p['WeaponId'],'FlightMarker':p['FlightMarker'],'PrimaryEventId':events['Fire']['Local'].removesuffix('_Local')+'_Tail_Owner'}
        if t.get('ability'):
            r['AbilityEventId']=events['SpecialFire']['Local'].removesuffix('_Local')+'_Tail_Owner'
        rows.append(r)
    assert len(rows)==54 and len({r['FlightMarker'] for r in rows})==54
    result={'SchemaVersion':1,'Profiles':rows}
    (ROOT/'ranger-snipers-owner-tail-profiles.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'profiles':len(rows),'abilityProfiles':sum('AbilityEventId'in r for r in rows)}))

if __name__=='__main__':main()
