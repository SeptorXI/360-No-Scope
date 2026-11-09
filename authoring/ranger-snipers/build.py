"""Assemble the private server's original Ranger sniper asset pack."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, zipfile

ROOT=Path(__file__).resolve().parent
PACK=ROOT/'pack'

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

def main():
    # Rebuild only this known generated directory; stale interactions from an
    # earlier version must never remain in the new archive.
    if PACK.resolve().parent != ROOT.resolve() or PACK.name != 'pack':
        raise RuntimeError('Refusing to clean an unexpected build directory')
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir()
    # The runtime helper registers the persistent-chamber interaction codecs.
    # Package code and assets together so a partial two-file install is impossible.
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                    '-File',str(ROOT/'reload/build.ps1')],check=True)
    subprocess.run([sys.executable,str(ROOT/'build-ammo.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'art/source/generate_reloads.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'audio/generate_audio.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'mechanics/generate_mechanics.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'audio/build_preview.py')],check=True)
    shutil.copytree(ROOT/'art/Common',PACK/'Common',dirs_exist_ok=True)
    shutil.copytree(ROOT/'art/generated/Server',PACK/'Server',dirs_exist_ok=True)
    shutil.copytree(ROOT/'audio/Common',PACK/'Common',dirs_exist_ok=True)
    shutil.copytree(ROOT/'audio/generated/Server',PACK/'Server',dirs_exist_ok=True)
    shutil.copytree(ROOT/'audio/credits',PACK/'Audio Credits',dirs_exist_ok=True)
    shutil.copytree(ROOT/'mechanics/generated/Server',PACK/'Server',dirs_exist_ok=True)
    spec=read(ROOT/'research/progression-spec.json')
    version=spec.get('version','1.0.0')
    mod_name=spec.get('modName','360 No Scope')
    artifact_stem=spec.get('artifactStem','360-No-Scope')
    acquisition=read(ROOT/'acquisition/acquisition-spec.json')
    # This superseded1.1 recipe must not remain a producer of legacy generic ammo.
    obsolete=PACK/'Server/Item/Recipes/RangerSnipers/RS_ChargedCartridge_Mjolnir.json'
    if obsolete.is_file():obsolete.unlink()
    subprocess.run([sys.executable,str(ROOT/'acquisition/generate_shop_patches.py'),str(ROOT/'acquisition/acquisition-spec.json'),str(PACK)],check=True,stdout=subprocess.DEVNULL)
    art={a['item_id']:a for a in read(ROOT/'art/artcatalog.json')['assets']}
    mechanics={a['item_id']:a for a in read(ROOT/'mechanics/generated/mechanics-catalog.json')['tiers']}
    ammo={a['id']:a for a in spec['ammo']}
    lang=(ROOT/'ammo-lang.txt').read_text(encoding='utf-8').splitlines()
    release_rows=[]
    for tier in spec['tiers']:
        item_id=tier['id'];a=art[item_id];m=mechanics[item_id]
        assert (tier['damage'],tier['headDamage'],tier['cycleSeconds'],tier['ammo']) == (m['body_damage'],m['head_damage'],m['cycle_seconds'],m['ammo_id'])
        item=read(ROOT/f'mechanics/generated/item-templates/{item_id}.json')
        item.update({
            'TranslationProperties':{'Name':f'server.items.{item_id}.name','Description':f'server.items.{item_id}.description'},
            'Model':a['model'],'Texture':a['texture'],'Icon':a['icon'],
            'Quality':tier['quality'],'ItemLevel':tier['itemLevel'],
            'MaxDurability':200+tier['tier']*50,'DurabilityLossOnHit':1,
            'ItemSoundSetId':'ISS_Weapons_Arrows',
            'IconProperties':{'Scale':0.37,'Translation':[-3.6,-20.4],'Rotation':[315,90,0]}
        })
        if not tier.get('vendorOnly'):
            item['Recipe']={'KnowledgeRequired':False,'TimeSeconds':3+tier['tier'],'Input':[{'ItemId':k,'Quantity':v} for k,v in tier['ingredients'].items()],
                            'OutputQuantity':1,'BenchRequirement':[tier['bench']]}
            if tier.get('requiredMemoriesLevel'):
                item['Recipe']['RequiredMemoriesLevel']=tier['requiredMemoriesLevel']
        write(PACK/f'Server/Item/Items/RangerSnipers/{item_id}.json',item)
        cartridge=ammo[tier['ammo']];payload=cartridge['stats']
        reload=tier['reload']
        description=tier['description']+f"\\nLoaded normal shot: {tier['damage']} body / {tier['headDamage']} head before modifiers. Rifle {tier['receiverDamage']}/{tier['receiverHeadDamage']} + ammo {payload['damage']}/{payload['headDamage']}. {tier['cycleSeconds']:g}s cycle | {m['scope_magnification']}x scope.\\nHold secondary to aim; click primary once to fire. Uses {cartridge['name']} (one per shot).\\nR: reload {reload['capacity']} round(s) in {reload['durationSeconds']:g}s. Matching ammo transfers only when reloading finishes."
        curve=tier.get('falloff')
        if curve:
            start,end=curve['points'][-2],curve['points'][-1]
            portion=max(0,min(1,(payload['range']-start['distance'])/(end['distance']-start['distance'])))
            edge=start['multiplier']+(end['multiplier']-start['multiplier'])*portion
            description+=f"\\nDistance: full base damage through {start['distance']:g} blocks, then gradual falloff; about {edge*100:.1f}% at the {payload['range']:g}-block nominal travel limit. Uses actual projectile path."
        ability=tier.get('ability')
        if ability:
            charge=f"Hold Q {ability['chargeSeconds']:g}s" if ability['chargeSeconds'] else 'Press Q'
            effect=f"0.5s NPC stagger" if ability['name']=='Reactor Break' else 'marks for 6s and slows eligible NPCs 20% for 4s'
            description+=f"\\n{ability['name']}: {charge}; {ability['bodyDamage']}/{ability['headDamage']} damage, {effect}. Costs {ability['ammoPerUse']} matching rounds. {ability['cooldownSeconds']:g}s shared special cooldown; {ability['shotRecoverySeconds']:g}s firing recovery."
        lang += [f'items.{item_id}.name = {tier["name"]}',f'items.{item_id}.description = {description}']
        release_rows.append({**tier,**m,'range':m['nominal_range_blocks'],'model':a['model'],'texture':a['texture'],'icon':a['icon']})
    for recipe in acquisition['AdditionalRecipes']:
        recipe_asset={
            'Input':[{'ItemId':k,'Quantity':v} for k,v in recipe['ingredients'].items()],
            'PrimaryOutput':{'ItemId':recipe['OutputId'],'Quantity':1},
            'OutputQuantity':recipe['OutputQuantity'],
            'Output':[{'ItemId':recipe['OutputId'],'Quantity':recipe['OutputQuantity']}],
            'BenchRequirement':[recipe['bench']],'KnowledgeRequired':False,
            'TimeSeconds':1 if recipe['OutputQuantity']==1 else 2}
        if recipe.get('requiredMemoriesLevel',1)>1:recipe_asset['RequiredMemoriesLevel']=recipe['requiredMemoriesLevel']
        write(PACK/f"Server/Item/Recipes/RangerSnipers/{recipe['Id']}.json",recipe_asset)
    subprocess.run([sys.executable,str(ROOT/'export-icons.py')],check=True)
    write(PACK/'manifest.json',{
        'Group':'Steven','Name':mod_name,'Version':version,
        'Main':'steven.rangersnipers.RangerSnipersPlugin',
        'Description':'Nine themed precision rifles and exclusive ammunition, crafted at an original five-tier Gunsmith Bench. Includes distance falloff, custom audio and persistent chambers.',
        'Authors':[{'Name':'Steven'}],
        'ServerVersion':'>=0.7.5 <0.8.0',
        'Dependencies':{'Hytale:ItemModule':'*','Hytale:InteractionModule':'*','Airijko:EndlessLevelingCore':'>=14.4.0 <15.0.0','Config:Endgame&QoL':'>=6.1.4 <7.0.0','Ziggfreed:MMOSkillTree':'>=1.7.4 <2.0.0','org.herolias:SimpleEnchantments':'=1.2.1',
                        "Alechilles:Alec's Tamework!":'>=5.9.0 <6.0.0','MAJOR76:MajorDungeons':'>=0.4.15 <0.5.0'},
        'IncludesAssetPack':True})
    # Asset-only packs are loaded after Java-plugin dependency resolution. Their
    # content is required and checked by the native recipe/asset QA, but placing
    # them in Java Dependencies prevents the server from reaching AssetModule.
    write(PACK/'ranger-snipers-content-requirements.json',{
        'RequiredAssetPacks':{'Lunaronin777:Fullmetal Labyrinth':'>=1.11.4 <2.0.0',
                             'CheewawaDev:Tritale - Echoes of Hyrule':'>=1.0.8 <2.0.0'},
        'Validation':'Required materials, benches and merchants are checked against this server\'s full native asset registry.'})
    lang_path=PACK/'Server/Languages/en-US/server.lang';lang_path.parent.mkdir(parents=True,exist_ok=True)
    lang_path.write_text('\n'.join(lang)+'\n',encoding='utf-8')
    subprocess.run([sys.executable,str(ROOT/'bench/generate_bench.py'),str(PACK)],check=True)
    gunsmith=read(ROOT/'bench/catalog.json')
    release=ROOT/'release';release.mkdir(exist_ok=True)
    limitations=read(ROOT/'mechanics/generated/mechanics-catalog.json')['limitations']
    limitations=[s for s in limitations if s!='Cooldown persistence after swapping requires native runtime validation.']
    limitations.append('Keep the rifle equipped through impact; the native damage pipeline resolves held-weapon bonuses at impact.')
    audio=read(ROOT/'audio/catalog.json')
    write(release/'catalog.json',{'modName':mod_name,'pluginId':spec.get('pluginId','Steven:360 No Scope'),'artifact':f'{artifact_stem}-{version}.jar','version':version,'sourceVersions':spec['sourceVersions'],'weapons':release_rows,'ammo':spec['ammo'],'legacyAmmo':spec.get('legacyAmmo',[]),'gunsmithBench':gunsmith,'audio':{'clips':len(audio['clips']),'events':len(audio['events']),'preview':'360 No Scope Audio Preview.html','sourcePacks':audio['sourcePacks']},'limitations':limitations})
    shutil.copy2(ROOT/'audio/catalog.json',release/'Audio Catalog.json')
    shutil.copy2(ROOT/'audio/360 No Scope Audio Preview.html',release/'360 No Scope Audio Preview.html')
    shutil.copy2(ROOT/'audio/credits/Audio Source Credits.txt',release/'Audio Source Credits.txt')
    write(release/'acquisition.json',{k:v for k,v in acquisition.items() if k!='ShopBaseline'})
    target=release/f'{artifact_stem}-{version}.jar'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(PACK.rglob('*')):
            if path.is_file():
                info=zipfile.ZipInfo(path.relative_to(PACK).as_posix(),(2026,11,8,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,path.read_bytes())
        with zipfile.ZipFile(ROOT/'reload/RangerSnipersReload.jar') as helper:
            for name in sorted(helper.namelist()):
                if name.endswith('.class') or name == 'ranger-snipers-reload-profiles.json':
                    info=zipfile.ZipInfo(name,(2026,11,8,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED
                    z.writestr(info,helper.read(name))
    (release/'SHA256SUMS.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    print(f'Built {target.name}: {target.stat().st_size:,} bytes; {len(release_rows)} rifles, regional recipes and additive vendor trades.')

if __name__=='__main__':main()
