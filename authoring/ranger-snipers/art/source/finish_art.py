"""Make transparent inventory icons and a readable review contact sheet."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'artcatalog.json').read_text())
fontfile=Path('C:/Windows/Fonts/segoeui.ttf')
boldfile=Path('C:/Windows/Fonts/seguisb.ttf')
font=ImageFont.truetype(str(fontfile),18)
bold=ImageFont.truetype(str(boldfile),26)
columns=3 if len(catalog['assets'])>6 else 2
rows=(len(catalog['assets'])+columns-1)//columns
sheet=Image.new('RGB',(columns*700,130+rows*340),'#111a24');draw=ImageDraw.Draw(sheet)
draw.text((40,24),'RANGER SNIPERS',font=ImageFont.truetype(str(boldfile),36),fill='#eef3f5')
draw.text((40,72),'Six regional models · three acquisition variants · native Rifle anchors',font=font,fill='#9bb0bf')
for i,asset in enumerate(catalog['assets']):
    image=Image.open(ROOT/'previews'/f"Tier{i+1:02}.png").convert('RGBA')
    bbox=image.getbbox()
    assert bbox and bbox[0]>1 and bbox[1]>1 and bbox[2]<image.width-1 and bbox[3]<image.height-1,(i,bbox)
    inventory_preview=ROOT/'previews'/f"Tier{i+1:02}_Inventory.png"
    icon_source=Image.open(inventory_preview).convert('RGBA') if i+1 in (5,6) and inventory_preview.exists() else image
    icon=icon_source.resize((256,256),Image.Resampling.LANCZOS)
    icon.save(ROOT/'Common'/asset['icon'])
    x=30+(i%columns)*700;y=120+(i//columns)*340
    draw.rounded_rectangle((x,y,x+670,y+320),radius=15,fill='#1d2a37',outline='#334556',width=2)
    crop=image.crop(bbox);crop.thumbnail((510,226),Image.Resampling.LANCZOS)
    sheet.paste(crop,(x+95+(510-crop.width)//2,y+65+(226-crop.height)//2),crop)
    label=f"VARIANT {i-5}  {asset['name']}" if asset.get('acquisition_variant') else f"{i+1:02}  {asset['name']}"
    draw.text((x+22,y+14),label,font=bold,fill='#e7edf1')
    footer=asset['zone']+' · '+asset['family']
    if asset['tier'] in (5,6):footer+=' · SIMULATED DUSK GLOW'
    draw.text((x+22,y+288),footer,font=font,fill='#9eb3c4')
sheet.save(ROOT/'previews'/'Ranger_Snipers_Contact_Sheet.png')
print('Inventory icons and contact sheet created.')
