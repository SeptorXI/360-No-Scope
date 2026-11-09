"""Build the isolated 360 No Scope arsenal over an immutable, verified baseline."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import argparse, hashlib, html, json, shutil, subprocess, sys
from nameless_barter import apply as apply_nameless_exclusivity
from reload_controls import apply as apply_reload_controls
from aiming_fix import apply as apply_aiming_fix
from audio.spatial_profiles import generate as generate_spatial_profiles
from audio.cinematic_credits import apply as apply_cinematic_credits

ROOT = Path(__file__).resolve().parent
PACK = ROOT / 'pack'
VERSION = '2.0.5'
FAMILIES = {'handgun': 'Handguns', 'smg': 'Submachine Guns', 'semiauto': 'Semi-auto Rifles', 'automatic': 'Automatic Rifles', 'shotgun': 'Shotguns'}
BASE_HASH = '9459fda21ef57c8e4bb1ccc1410a13764f797d8be5f60f88abaa89c646fadd52'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
def run(p): subprocess.run([sys.executable, str(p)], check=True)

def recipe(row, quantity):
    return {'KnowledgeRequired': False, 'TimeSeconds': 3 if quantity == 1 else 2,
            'Input': [{'ItemId': k, 'Quantity': v} for k,v in row['ingredients'].items()],
            'OutputQuantity': quantity, 'BenchRequirement': [row['bench']],
            'RequiredMemoriesLevel': row.get('requiredMemoriesLevel', 1)}

def describe(t, a):
    n=t.get('pellets',1)
    dmg=f"{t['damage']:g}/{t['headDamage']:g} body/head" if n==1 else f"{n} pellets; {t['damage']:g}/{t['headDamage']:g} body/head per pellet (maximum {n*t['damage']:g}/{n*t['headDamage']:g} per shell)"
    mode='Hold primary for automatic fire' if t['automatic'] else 'Click primary once per shot'
    curve=t['falloff']['points']; start=curve[1]['distance']; end=curve[-1]
    s=(t['description']+f"\\n{dmg} before class, enchantments and armor. {t['cycleSeconds']:g}s cycle; {t['reload']['capacity']} rounds; F reload {t['reload']['durationSeconds']:g}s."
       +f"\\n{mode}; secondary aims. Uses only {a['name']}. Ammo transfers at reload completion."
       +f"\\nFull base damage through {start:g} blocks of actual projectile travel, falling to {end['multiplier']*100:g}% at {end['distance']:g}. Nominal travel limit {t['range']:g} blocks.")
    if t.get('ability'):
        q=t['ability']; s+=f"\\nQ — {q['name']}: {q['bodyDamage']:g}/{q['headDamage']:g} body/head, costs {q['ammoPerUse']} rounds; {q['cooldownSeconds']:g}s shared special cooldown; {q['shotRecoverySeconds']:g}s recovery."
        if q.get('description'): s+=' '+q['description']
    return s

def extend_shops(spec):
    original=read(ROOT/'baseline/acquisition-spec.json')
    old=read(ROOT/'baseline/sniper-spec.json')
    maps={t['id']:t for t in old['tiers']}
    ammo={a['id']:a for a in old['ammo']}
    by_index={i+1:t for i,t in enumerate(old['tiers'])}
    shops=[]
    for shop in original['Shops']:
        trades=[]
        for trade in shop['Trades']:
            out=trade['Output']['ItemId']; is_ammo=out in ammo
            old_t=maps.get(ammo[out]['compatibleWeapon'] if is_ammo else out)
            if old_t is None: continue
            index=next(i for i,t in by_index.items() if t['id']==old_t['id'])
            for t in spec['tiers']:
                if t['artIndex']!=index: continue
                if t.get('vendorOnly') and not is_ammo:continue
                tr=json.loads(json.dumps(trade)); new_id=t['ammo'] if is_ammo else t['id']
                tr['OperationId']='AS_sale_'+new_id
                tr['Output']['ItemId']=new_id
                if is_ammo: tr['Output']['Quantity']=next(a['output'] for a in spec['ammo'] if a['id']==new_id)
                trades.append(tr)
        if trades: shops.append({'PatchId':shop['PatchId'].replace('RS_','AS_',1),'Target':shop['Target'],'Trades':trades})
    acquisition={'version':VERSION,'Shops':shops}
    write(ROOT/'generated/acquisition.json',acquisition)
    subprocess.run([sys.executable,str(ROOT/'baseline/generate_shop_patches.py'),str(ROOT/'generated/acquisition.json'),str(PACK)],check=True,stdout=subprocess.DEVNULL)
    return acquisition

def guide(spec, art, acquisition):
    h=html.escape; ammo={a['id']:a for a in spec['ammo']}; assets={a['item_id']:a for a in art['assets']}
    text=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>360 No Scope — Arsenal</title><style>body{margin:0;background:#10171b;color:#e5eee8;font:16px/1.55 system-ui}main{max-width:1400px;margin:auto;padding:28px}h1{font-size:42px;margin-bottom:6px}h2{margin-top:48px;color:#e4bd78}p{max-width:950px;color:#bac9c2}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}article{background:#1b272c;border:1px solid #344448;border-radius:12px;padding:20px}article img{width:128px;height:128px;image-rendering:pixelated;float:right}h3{margin-top:0}.rarity{color:#e7c58c}small{color:#a9bcb4}details{margin:14px 0}summary{cursor:pointer}code{word-break:break-all}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #344448;text-align:left}.badge{display:inline-block;background:#30463e;padding:3px 10px;border-radius:16px}</style><main><h1>360 No Scope</h1><span class="badge">Arsenal expansion · 45 new guns · 54 total</span><p>Five new weapon families, nine regional designs each. Craft at the existing five-tier Gunsmith’s Bench. Every gun takes its own ammunition; matching rounds transfer only when F reloading finishes. Existing sniper rifles and their ammunition remain included.</p><p>Numbers are base values before class bonuses, enchantments and armor. Shotgun damage is per pellet; each shell pays once. Actual projectile travel determines damage falloff. Multiplayer aiming, sound, handling and final balance need an in-game playtest.</p>']
    for family,label in FAMILIES.items():
        text.append('<h2>'+label+'</h2><div class="grid">')
        for t in spec['tiers']:
            if t['family']!=family: continue
            a=ammo[t['ammo']]; asset=assets[t['id']]; rel='../pack/Common/'+asset['icon']
            n=t['pellets']; damage=f"{t['damage']:g} / {t['headDamage']:g}"
            if n>1: damage+=f" × {n} pellets"
            text.append(f'<article><img src="{h(rel)}" alt="{h(t["name"])}"><small class="rarity">{h(t["quality"])} · {h(str(t.get("region", t.get("theme", ""))))}</small><h3>{h(t["name"])}</h3><p>{h(t["description"])}</p><table><tr><th>Body / head</th><td>{damage}</td></tr><tr><th>Cycle / reload</th><td>{t["cycleSeconds"]:g}s / {t["reload"]["durationSeconds"]:g}s</td></tr><tr><th>Capacity / range</th><td>{t["reload"]["capacity"]} / {t["range"]:g} blocks</td></tr><tr><th>Ammo</th><td>{h(a["name"])}</td></tr><tr><th>Bench tier</th><td>{t["bench"]["RequiredTierLevel"]}</td></tr></table>')
            if t.get('ability'):
                q=t['ability'];text.append(f'<p><b>Q · {h(q["name"])}</b><br>{h(q.get("description",""))} {q["bodyDamage"]:g}/{q["headDamage"]:g} damage; {q["ammoPerUse"]} rounds; {q["cooldownSeconds"]:g}s shared cooldown.</p>')
            text.append('<details><summary>Crafting and item IDs</summary><p>'+h(', '.join(f'{v} × {k}' for k,v in t['ingredients'].items()))+'</p><p>Ammo batch: '+str(a['output'])+'<br>'+h(', '.join(f'{v} × {k}' for k,v in a['ingredients'].items()))+'</p><code>'+h(t['id'])+'</code></details></article>')
        text.append('</div>')
    text.append('<h2>Regional vendors</h2><p>Regional traders retain their other gun and ammunition offers. The six Nameless weapons are sold exclusively through The Nameless God’s Barter, Weapons tab, Tier 2. They have no Gunsmith recipe or other seller. Matching ammunition remains available from its existing sources.</p><h2>Installation</h2><p>Replace the previous 360 No Scope JAR on a stopped, backed-up server. Load one version only. Consult the saved deployment receipt for installation status; clients should rejoin after updating.</p></main></html>')
    contract=read(ROOT/'content/nameless-exclusives.json')
    names={'sniper':'Sniper rifle',**FAMILIES}
    exclusive='<h2>Nameless God exclusives</h2><p>Only through The Nameless God’s Barter → Weapons → Tier 2. Each costs <b>40 Dark Coins + 1 Silver Skull</b>.</p><table><tr><th>Weapon family</th><th>Exclusive weapon</th></tr>'
    for w in contract['weapons']:exclusive+=f'<tr><td>{h(names[w["family"]])}</td><td>{h(w["name"])}</td></tr>'
    exclusive+='</table>'
    document=''.join(text).replace('<h2>Handguns</h2>',exclusive+'<h2>Handguns</h2>',1)
    document=document.replace('Craft at the existing five-tier Gunsmith’s Bench.','Most guns craft at the five-tier Gunsmith’s Bench; the six Nameless guns are exclusive to his barter.')
    document=document.replace('<th>Bench tier</th>','<th>Acquisition tier</th>').replace('<summary>Crafting and item IDs</summary>','<summary>Acquisition, ammunition and item IDs</summary>')
    (ROOT/'release/360 No Scope Arsenal Guide.html').write_text(document,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assemble-only',action='store_true'); args=parser.parse_args()
    baseline=ROOT/'baseline/360-No-Scope-1.6.0.jar'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==BASE_HASH,'Frozen baseline changed'
    if not args.assemble_only:
        run(ROOT/'content/generate_spec.py');run(ROOT/'art/build_art.py');run(ROOT/'audio/generate_audio.py');run(ROOT/'runtime/generate_mechanics.py')
        run(ROOT/'audio/enhance_core.py')
        run(ROOT/'audio/generate_cinematic_core.py')
        run(ROOT/'audio/cinematic-arsenal/generate.py')
        generate_spatial_profiles()
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'runtime/build.ps1')],check=True)
    spec=read(ROOT/'content/arsenal-spec.json'); art=read(ROOT/'art/artcatalog.json')
    assert len(spec['tiers'])==len(spec['ammo'])==45
    assert PACK.resolve().parent==ROOT and PACK.name=='pack'
    if PACK.exists(): shutil.rmtree(PACK)
    PACK.mkdir()
    with ZipFile(baseline) as z: z.extractall(PACK)
    # A separately frozen sound revision may advance while gameplay source
    # remains the immutable1.6 baseline. Never import its old runtime classes.
    revision_path=ROOT/'baseline/audio-revision.json'
    audio_revision=None
    if revision_path.exists():
        audio_revision=read(revision_path);revision_jar=(ROOT/'baseline'/audio_revision['artifact']).resolve()
        assert revision_jar.is_relative_to((ROOT/'baseline').resolve()),'Audio revision path escapes baseline'
        assert hashlib.sha256(revision_jar.read_bytes()).hexdigest()==audio_revision['sha256'],'Frozen audio revision changed'
        if audio_revision.get('catalog'):
            catalog_path=(ROOT/'baseline'/audio_revision['catalog']).resolve()
            assert catalog_path.is_relative_to((ROOT/'baseline').resolve())
            assert hashlib.sha256(catalog_path.read_bytes()).hexdigest()==audio_revision['catalogSha256'],'Frozen audio catalog changed'
        handoff_path=ROOT/'baseline/audio-handoff-1.7.0.json'
        expected_payload=read(handoff_path)['payload'] if handoff_path.exists() else None
        with ZipFile(revision_jar) as z:
            payload=[]
            source_names=[r['path'] for r in expected_payload] if expected_payload else z.namelist()
            for name in source_names:
                if name.startswith(('Common/Sounds/','Server/Audio/','Audio Credits/')) and not name.endswith('/'):
                    target=PACK/name
                    assert target.resolve().is_relative_to(PACK.resolve())
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name));payload.append(name)
            if expected_payload:
                assert len(payload)==len(expected_payload)==247,'Unexpected audio handoff payload'
                for row in expected_payload:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256'],'Accepted sound payload changed'
            write(ROOT/'generated/audio-overlay.json',{'source':audio_revision,'entries':payload})
    for source in (ROOT/'art/Common', ROOT/'audio/Common'): shutil.copytree(source,PACK/'Common',dirs_exist_ok=True)
    for source in (ROOT/'art/generated/Server', ROOT/'generated/mechanics/Server', ROOT/'audio/generated/Server'):
        shutil.copytree(source,PACK/'Server',dirs_exist_ok=True)
    core_validation=read(ROOT/'audio/core-enhanced/validation.json')
    assert core_validation['passed'] and core_validation['version']=='2.0.4','Frozen core audio remaster has not passed validation'
    core_catalog=read(ROOT/'audio/core-enhanced/catalog.json')
    for row in [*core_catalog['clips'],*core_catalog['events']]:
        relative=row.get('runtimePath',row.get('path'))
        assert hashlib.sha256((ROOT/'audio/core-enhanced'/relative).read_bytes()).hexdigest()==row['sha256'],'Core audio output changed after validation: '+relative
    for folder in ('Common','Server'):
        shutil.copytree(ROOT/'audio/core-enhanced'/folder,PACK/folder,dirs_exist_ok=True)
    for bank in ('cinematic-core','cinematic-arsenal'):
        directory=ROOT/'audio'/bank;validation=read(directory/'validation.json');catalog=read(directory/'catalog.json')
        assert validation['passed'] and catalog['version']==VERSION,bank+' is not validated for this release'
        for row in [*catalog['clips'],*catalog['events']]:
            relative=row.get('runtimePath',row.get('path'))
            assert hashlib.sha256((directory/relative).read_bytes()).hexdigest()==row['sha256'],bank+' changed after validation: '+relative
        for folder in ('Common','Server'):
            shutil.copytree(directory/folder,PACK/folder,dirs_exist_ok=True)
        if (directory/'Audio Credits').is_dir():
            shutil.copytree(directory/'Audio Credits',PACK/'Audio Credits',dirs_exist_ok=True)
    spatial_path,spatial_profiles=generate_spatial_profiles()
    shutil.copytree(ROOT/'audio/credits',PACK/'Audio Credits/Arsenal',dirs_exist_ok=True)
    apply_cinematic_credits(PACK)
    classes=ROOT/'runtime/classes'
    for p in classes.rglob('*'):
        if p.is_file():
            target=PACK/p.relative_to(classes); target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.copy2(spatial_path,PACK/'ranger-snipers-owner-tail-profiles.json')
    # Keep unchanged gameplay resources byte-identical despite PowerShell's
    # version-dependent JSON formatting in the runtime build helper.
    with ZipFile(ROOT/'release/360-No-Scope-2.0.4.jar') as previous:
        name='ranger-snipers-reload-profiles.json'
        accepted=previous.read(name)
        assert json.loads(accepted)==read(PACK/name),'Unexpected magazine/falloff profile change'
        (PACK/name).write_bytes(accepted)
    assets={a['item_id']:a for a in art['assets']}
    ammo_assets={a['item_id']:a for a in art.get('ammo', art.get('ammunition', []))}
    ammo={a['id']:a for a in spec['ammo']};lang=[]
    for t in spec['tiers']:
        a=assets[t['id']]; template=ROOT/f'generated/mechanics/item-templates/{t["id"]}.json'
        item=read(template)
        item.update({'TranslationProperties':{'Name':f'server.items.{t["id"]}.name','Description':f'server.items.{t["id"]}.description'},'Model':a['model'],'Texture':a['texture'],'Icon':a['icon'],'Quality':t['quality'],'ItemLevel':t['itemLevel'],'MaxDurability':200+t['tier']*50,'DurabilityLossOnHit':1,'ItemSoundSetId':'ISS_Weapons_Arrows'})
        if not t.get('vendorOnly'):item['Recipe']=recipe(t,1)
        if a.get('playerAnimationsId'): item['PlayerAnimationsId']=a['playerAnimationsId']
        write(PACK/f'Server/Item/Items/Arsenal/{t["id"]}.json',item)
        lang += [f'items.{t["id"]}.name = {t["name"]}',f'items.{t["id"]}.description = {describe(t,ammo[t["ammo"]])}']
    for a in spec['ammo']:
        icon=ammo_assets[a['id']]
        item={'TranslationProperties':{'Name':f'server.items.{a["id"]}.name','Description':f'server.items.{a["id"]}.description'},'Icon':icon['icon'],'Model':icon['model'],'Texture':icon['texture'],'Quality':a['quality'],'MaxStack':100,'Categories':['Items.Weapons'],'Tags':{'Type':['Ammo'],'Family':['Arrow']},'Recipe':recipe(a,a['output']),'PlayerAnimationsId':'Item','ItemSoundSetId':'ISS_Weapons_Arrows'}
        write(PACK/f'Server/Item/Items/Arsenal/{a["id"]}.json',item)
        w=next(t for t in spec['tiers'] if t['id']==a['compatibleWeapon']);s=a['stats']
        unit='per pellet' if w['pellets']>1 else 'per shot'
        details=(a['description']+f"\\nFits {w['name']} only. Ammo contribution: +{s['damage']:g} body / +{s['headDamage']:g} head {unit}."
                 +f"\\nVelocity {s['speed']:g} blocks/s | Drop rating {s['gravity']:g} | Nominal travel {s['range']:g} blocks. Craft {a['output']} per batch. One round per normal discharge; Q costs two.")
        lang += [f'items.{a["id"]}.name = {a["name"]}',f'items.{a["id"]}.description = {details}']
    bench_path=PACK/'Server/Item/Items/RangerSnipers/Bench/RS_Gunsmith_Bench.json'
    if not bench_path.exists(): bench_path=next(PACK.glob('Server/Item/Items/**/RS_Gunsmith_Bench.json'))
    bench=read(bench_path);categories=bench['BlockType']['Bench']['Categories']
    for family,label in FAMILIES.items():
        category='AS_Gunsmith_'+family; icon='Icons/CraftingCategories/'+category+'.png'
        first=next(t for t in spec['tiers'] if t['family']==family)
        source=PACK/'Common'/assets[first['id']]['icon']; target=PACK/'Common'/icon
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        categories.append({'Id':category,'Icon':icon,'Name':'server.benchCategories.'+category})
        lang.append(f'benchCategories.{category} = {label}')
    write(bench_path,bench)
    with (PACK/'Server/Languages/en-US/server.lang').open('a',encoding='utf-8') as f: f.write('\n'+'\n'.join(lang)+'\n')
    acquisition=extend_shops(spec)
    exclusivity=apply_nameless_exclusivity(PACK)
    controls=apply_reload_controls(PACK)
    write(ROOT/'generated/reload-controls.json',controls)
    write(ROOT/'generated/aiming-fix.json',apply_aiming_fix(PACK))
    manifest=read(PACK/'manifest.json');manifest['Version']=VERSION;manifest['Description']='54 themed guns: nine snipers plus handguns, SMGs, semi-auto rifles, automatic rifles and shotguns. Dedicated ammunition, persistent magazines and five-tier Gunsmith crafting.'
    write(PACK/'manifest.json',manifest)
    write(ROOT/'release/catalog.json',{'version':VERSION,'baselineVersion':'1.6.0','baselineSHA256':BASE_HASH,'audioRevision':audio_revision,'newWeapons':spec['tiers'],'newAmmo':spec['ammo'],'totalGuns':54,'vendors':acquisition['Shops'],'namelessExclusives':exclusivity,'limitations':['Native server and static checks are recorded separately in Validation Report.json.','Client aiming, held-fire handling, reload appearance, spatial sound and multiplayer balance require playtesting.']})
    guide(spec,art,acquisition)
    target=ROOT/f'release/360-No-Scope-{VERSION}.jar'
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(PACK.rglob('*')):
            if p.is_file():
                info=ZipInfo(p.relative_to(PACK).as_posix(),(2026,11,9,0,0,0));info.compress_type=ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (ROOT/'release/SHA256SUMS.txt').write_text(digest+'  '+target.name+'\n',encoding='utf-8')
    print(json.dumps({'artifact':str(target),'sha256':digest,'newGuns':45,'newAmmo':45,'totalGuns':54}))

if __name__=='__main__':main()
