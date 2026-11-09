"""Build and cache actual static renders; animation-only edits avoid rerendering."""
from pathlib import Path
from PIL import Image
import hashlib,json,subprocess,sys

ART=Path(__file__).resolve().parent
BLENDER=Path('C:/Tools/Blender/blender-5.1.2-windows-x64/blender.exe')

def static_digest():
    h=hashlib.sha256()
    h.update((ART/'render_art.py').read_bytes())
    for scene in sorted((ART/'source').glob('*.scene.json')):
        data=json.loads(scene.read_text());h.update(scene.name.encode());h.update(json.dumps(data,sort_keys=True).encode())
        texture=Image.open(data['texture']).convert('RGBA');h.update(texture.crop((0,0,512,512)).tobytes())
    return h.hexdigest()

def main():
    subprocess.run([sys.executable,str(ART/'generate_art.py')],check=True)
    cache=ART/'render-manifest.json';digest=static_digest();prior=json.loads(cache.read_text()) if cache.exists() else {}
    catalog=json.loads((ART/'artcatalog.json').read_text());expected=[ART/'previews'/(Path(a['scene']).name.removesuffix('.scene.json')+'.png') for a in catalog['assets']+catalog['ammo']]
    if prior.get('staticDigest')!=digest or not all(p.is_file() for p in expected):
        subprocess.run([str(BLENDER),'--background','--factory-startup','--python',str(ART/'render_art.py')],check=True)
        cache.write_text(json.dumps(dict(staticDigest=digest,renderer=str(BLENDER),renders=len(expected)),indent=2)+'\n')
    subprocess.run([sys.executable,str(ART/'finish_art.py')],check=True)
    subprocess.run([sys.executable,str(ART/'validate_art.py')],check=True)

if __name__=='__main__':main()
