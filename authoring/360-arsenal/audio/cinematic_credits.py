"""Package the new physical-recording credits without replacing old notices."""
from pathlib import Path
import json

PROJECT=Path(__file__).resolve().parents[1]
def apply(pack):
    manifest=json.loads((PROJECT/'audio/open-source-bank/source-manifest.json').read_text(encoding='utf-8-sig'))
    sources={}
    for source in manifest['sources']:
        key=(source.get('sourceUrl',''),source.get('license',''))
        sources.setdefault(key,source)
    lines=['360 NO SCOPE 2.0.5 — CINEMATIC RECORDING SOURCES','',
           'New physical gunfire, handling and natural-return source bank.',
           'Runtime effects are original edited and layered arrangements. Raw source recordings are not packaged as a sample library.','']
    for (url,license_name),source in sources.items():
        creators=source.get('creator',source.get('author',''))
        if isinstance(creators,list):creators=', '.join(creators)
        lines.extend([source.get('library',source.get('title',source.get('description',source['id']))),
                      'Creator: '+str(creators),'Source: '+url,'License: '+license_name,
                      'License reference: '+source.get('licenseUrl',''),''])
    lines.extend(['Existing Bluezone cinematic/mechanical accents retain their original project-use terms and attribution. See BluezoneLicense.txt and Bluezone Credits.txt.',
                  'Bluezone free project-use permission is distinct from the CC0 physical recording licenses above.',
                  'Any retained legacy gunshot/handling layers remain credited in Audio Source Credits.txt.',
                  'Suno audition material is not selected for this cinematic release.',''])
    target=Path(pack)/'Audio Credits/Cinematic Recording Sources.txt';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(lines),encoding='utf-8')
    return target
