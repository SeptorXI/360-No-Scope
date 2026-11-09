"""Assemble original, exclusive rifle ammunition from the canonical stat profiles."""
from pathlib import Path
import json,shutil,zipfile
ROOT=Path(__file__).resolve().parent
PACK=ROOT/'pack'

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

def main():
    spec=json.loads((ROOT/'research/progression-spec.json').read_text(encoding='utf-8-sig'))
    artwork=json.loads((ROOT/'ammo-art/artcatalog.json').read_text(encoding='utf-8-sig'))
    art={x['item_id']:x for x in artwork['assets']}
    weapons={x['id']:x for x in spec['tiers']}
    shutil.copytree(ROOT/'ammo-art/Common',PACK/'Common',dirs_exist_ok=True)
    itemdir=PACK/'Server/Item/Items/RangerSnipers/Ammo';lang=[]
    for a in spec['ammo']:
        model=art[a['id']];w=weapons[a['compatibleWeapon']];stats=a['stats']
        assert w['ammo']==a['id']
        assert w['receiverDamage']+stats['damage']==w['damage']
        assert w['receiverHeadDamage']+stats['headDamage']==w['headDamage']
        recipe={'TimeSeconds':2,'KnowledgeRequired':False,'Input':[{'ItemId':k,'Quantity':v} for k,v in a['ingredients'].items()],
                'OutputQuantity':a['output'],'BenchRequirement':[a['bench']]}
        if a.get('requiredMemoriesLevel',1)>1:recipe['RequiredMemoriesLevel']=a['requiredMemoriesLevel']
        item={'TranslationProperties':{'Name':f"server.items.{a['id']}.name",'Description':f"server.items.{a['id']}.description"},
              'Categories':['Items.Weapons'],'Quality':a['quality'],
              'Model':model['model'],'Texture':model['texture'],'Icon':model['icon'],
              'PlayerAnimationsId':'Item','MaxStack':100,
              'Tags':{'Type':['Ingredient'],'Family':['Arrow']},'ItemSoundSetId':'ISS_Items_Ingots',
              'IconProperties':{'Scale':1,'Rotation':[22.5,45,0],'Translation':[0,0]},'Recipe':recipe}
        write(itemdir/f"{a['id']}.json",item)
        desc=(a['description']+f"\\nFits {w['name']} only. Ammo impact: +{stats['damage']} body / +{stats['headDamage']} head. "
              f"Loaded normal shot: {w['damage']} / {w['headDamage']} before modifiers.\\nVelocity {stats['speed']} blocks/s | Drop rating {stats['gravity']:g} | Nominal travel {stats['range']} blocks. "
              f"Craft {a['output']} per batch; one round per normal shot.")
        if w.get('ability'):desc+=" Special shots use two rounds and the weapon's listed special damage."
        lang += [f"items.{a['id']}.name = {a['name']}",f"items.{a['id']}.description = {desc}"]
    # Keep prior stock readable, but remove its producers and direct rifle use.
    legacy=spec.get('legacyAmmo',[])
    if legacy:
        oldzip=ROOT/'snapshots/1.1.0/release/RangerSnipers-1.1.0.zip'
        names={a['id']:a['name'] for a in spec['ammo']}
        with zipfile.ZipFile(oldzip) as z:
            for old in legacy:
                relative=f"Server/Item/Items/RangerSnipers/Ammo/{old['id']}.json"
                item=json.loads(z.read(relative));item.pop('Recipe',None)
                write(PACK/relative,item)
                for field in ['Model','Texture','Icon']:
                    relative='Common/'+item[field]
                    destination=(PACK/relative).resolve()
                    if PACK.resolve() not in destination.parents:raise ValueError('Invalid legacy asset path')
                    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(z.read(relative))
                targets=', '.join(names[x] for x in old['repackTargets'])
                lang += [f"items.{old['id']}.name = {old['name']} (Legacy)",
                         f"items.{old['id']}.description = Legacy stock. Repack 1:1 at the Gunsmith's Bench into {targets}. New rifles require their named cartridges."]
    (ROOT/'ammo-lang.txt').write_text('\n'.join(lang)+'\n',encoding='utf-8')
    print(f"Built {len(spec['ammo'])} exclusive ammo items/recipes and retained {len(legacy)} uncraftable legacy item IDs.")

if __name__=='__main__':main()
