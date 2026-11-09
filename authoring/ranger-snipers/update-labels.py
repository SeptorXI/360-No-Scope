import os
"""Resolve the installed English display names for the actual acquisition IDs."""
from pathlib import Path
import json,zipfile
ROOT=Path(__file__).resolve().parent
def main():
    spec=json.loads((ROOT/'research/progression-spec.json').read_text())
    acq=json.loads((ROOT/'acquisition/acquisition-spec.json').read_text())
    ids={k for t in spec['tiers']+spec['ammo'] for k in t.get('ingredients',{})}
    ids.update(k for t in acq['AdditionalRecipes'] for k in t['ingredients'])
    ids.update(i['ItemId'] for s in acq['Shops'] for t in s['Trades'] for i in t['Input'])
    own={t['id']:t['name'] for t in spec['tiers']+spec['ammo']+spec.get('legacyAmmo',[])}
    ids.difference_update(own)
    labels={};items={}
    mods=Path(os.environ['HYTALE_MODS_DIR'])
    archives=[Path(os.environ['HYTALE_ASSETS_ZIP'])]+sorted(mods.glob('*.jar'))+sorted(mods.glob('*.zip'))
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                if n.startswith('Server/Languages/en-US/') and n.endswith('.lang'):
                    for line in z.read(n).decode('utf-8-sig',errors='replace').splitlines():
                        if '=' in line and not line.lstrip().startswith('#'):
                            k,v=line.split('=',1);k=k.strip();v=v.strip()
                            labels[k]=v
                            labels[Path(n).stem+'.'+k]=v
                elif n.startswith('Server/Item/Items/') and n.endswith('.json') and Path(n).stem in ids:
                    try:items[Path(n).stem]=json.loads(z.read(n))
                    except json.JSONDecodeError:pass
    missing=sorted(ids-items.keys())
    if missing:raise ValueError('Item assets missing: '+', '.join(missing))
    names={}
    for item_id in sorted(ids):
        key=items[item_id].get('TranslationProperties',{}).get('Name','server.items.'+item_id+'.name')
        names[item_id]=labels.get(key,labels.get(key.removeprefix('server.'),key if not key.startswith('server.') else item_id))
    names.update(own)
    (ROOT/'research/material-names.json').write_text(json.dumps(names,indent=2)+'\n')
    print(f'Resolved {len(ids)} acquisition ingredient/currency IDs and {len(spec["tiers"])} weapon names.')
if __name__=='__main__':main()
