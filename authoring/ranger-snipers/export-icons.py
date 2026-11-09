"""Export authored item thumbnails to Hytale's64px inventory-icon contract.

Authoring renders remain high resolution. Only the generated runtime pack is
converted; all names, models, textures and original image composition survive.
"""
from pathlib import Path
import hashlib,json
from PIL import Image

ROOT=Path(__file__).resolve().parent
PACK=ROOT/'pack'

def main():
    icons={}
    for path in (PACK/'Server/Item/Items/RangerSnipers').rglob('*.json'):
        item=json.loads(path.read_text(encoding='utf-8-sig'))
        if item.get('Icon'):
            icons.setdefault(item['Icon'],[]).append(path.stem)
    assert len(icons)==21,'Expected nine rifle, nine active and three legacy ammo icons'
    rows=[]
    for relative,items in sorted(icons.items()):
        path=(PACK/'Common'/relative).resolve()
        if not path.is_relative_to((PACK/'Common/Icons').resolve()):
            raise ValueError('Unexpected item icon export path')
        with Image.open(path) as image:
            before=image.size
            icon=image.convert('RGBA')
            if icon.size!=(64,64):
                icon=icon.convert('RGBa').resize((64,64),Image.Resampling.LANCZOS).convert('RGBA')
            assert icon.getbbox(),'Refusing a fully transparent inventory icon'
            icon.save(path,format='PNG',optimize=True)
        with Image.open(path) as check:
            assert check.size==(64,64) and check.mode=='RGBA'
            bbox=check.getbbox();assert bbox and bbox[0]>0 and bbox[1]>0 and bbox[2]<64 and bbox[3]<64
            rows.append({'path':relative,'items':items,'authoringDimensions':list(before),
                         'runtimeDimensions':[64,64],'mode':'RGBA','visibleBounds':list(bbox),
                         'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    report={'passed':True,'contract':'64x64 RGBA8 item thumbnails, matching native and installed working-mod icon assets',
            'icons':rows,'count':len(rows),'sourceArtworkChanged':False}
    (ROOT/'release/Icon Export Report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Exported {len(rows)} native64px inventory icons; authoring art unchanged.')

if __name__=='__main__':main()
