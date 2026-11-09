"""Compile the six named merchant-exclusive guns without changing their mechanics."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def output_ids(value):
    result=set()
    if isinstance(value,dict):
        primary=value.get('PrimaryOutput')
        if isinstance(primary,dict) and primary.get('ItemId'):result.add(primary['ItemId'])
        for row in value.get('Output',[]) if isinstance(value.get('Output',[]),list) else [value.get('Output')]:
            if isinstance(row,dict) and row.get('ItemId'):result.add(row['ItemId'])
    return result

def apply(pack):
    pack=Path(pack).resolve()
    assert pack==ROOT/'pack','Refusing an unexpected pack directory'
    contract=read(ROOT/'content/nameless-exclusives.json')
    guns={w['id']:w for w in contract['weapons']}
    assert len(guns)==6 and {w['family'] for w in guns.values()}=={'sniper','handgun','smg','semiauto','automatic','shotgun'}
    removed_embedded=[];removed_recipes=[];removed_sales=[]
    for path in sorted((pack/'Server/Item/Items').rglob('*.json')):
        if path.stem not in guns:continue
        item=read(path)
        if item.pop('Recipe',None) is not None:removed_embedded.append(path.relative_to(pack).as_posix())
        write(path,item)
    for path in sorted((pack/'Server/Item/Recipes').rglob('*.json')):
        if output_ids(read(path))&guns.keys():
            removed_recipes.append(path.relative_to(pack).as_posix());path.unlink()
    # Remove only our selected gun outputs. Ammunition and unrelated merchant
    # operations retain their original prices, quantities and stock.
    for path in sorted((pack/'Server/Patchwork/Patches').glob('*.json')):
        patch=read(path);before=patch.get('Operations',[]);after=[]
        for operation in before:
            item=operation.get('Value',{}).get('Trade',{}).get('Output',{}).get('ItemId')
            if item in guns:removed_sales.append({'patch':path.name,'operation':operation['Id'],'weaponId':item})
            else:after.append(operation)
        if after!=before:
            assert after,'Refusing to discard an entire unrelated shop patch'
            patch['Operations']=after;write(path,patch)
    for gun in guns.values():
        recipe={'Input':[{'ItemId':k,'Quantity':v} for k,v in gun['ingredients'].items()],
                'PrimaryOutput':{'ItemId':gun['id'],'Quantity':1},'Output':[{'ItemId':gun['id'],'Quantity':1}],
                'OutputQuantity':1,'BenchRequirement':[gun['bench']],'KnowledgeRequired':False,'TimeSeconds':1,'RequiredMemoriesLevel':1}
        folder='RangerSnipers' if gun['family']=='sniper' else 'Arsenal/Nameless'
        write(pack/f'Server/Item/Recipes/{folder}/{gun["recipeId"]}.json',recipe)
    language=pack/'Server/Languages/en-US/server.lang'
    lines=language.read_text(encoding='utf-8').splitlines()
    for index,line in enumerate(lines):
        for gun in guns.values():
            for previous in gun.get('previousNames',[]):line=line.replace(previous,gun['name'])
        lines[index]=line
    for index,line in enumerate(lines):
        for gun in guns.values():
            if line.startswith(f'items.{gun["id"]}.description = ') and 'Sold exclusively through' not in line:
                lines[index]+="\\nSold exclusively through The Nameless God's Barter: Weapons, Tier 2. Price: 40 Dark Coins + 1 Silver Skull."
    language.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report={'seller':contract['seller'],'weapons':contract['weapons'],'removedEmbeddedRecipes':removed_embedded,
            'retiredStandaloneRecipes':removed_recipes,'removedOtherSellerOperations':removed_sales,
            'ordinaryCraftingPermitted':False,'ammunitionPolicy':'Unchanged; matching ammo remains available at its existing crafting and sales sources.'}
    write(ROOT/'generated/nameless-exclusivity.json',report)
    return report
