"""Create transparent inventory icons and an original-ammo review sheet."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'artcatalog.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17);bold=ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf',23)
sheet=Image.new('RGB',(1500,1545),'#111a24');draw=ImageDraw.Draw(sheet)
draw.text((35,24),'RANGER AMMUNITION',font=ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf',35),fill='#eef3f5')
draw.text((35,77),'Nine original native cube designs · independent ammunition for each rifle',font=font,fill='#9cb3c4')
for i,a in enumerate(catalog['assets']):
    im=Image.open(ROOT/'previews'/f"Ammo{a['index']:02}.png").convert('RGBA');bbox=im.getbbox()
    assert bbox and min(bbox)>1 and bbox[2]<510 and bbox[3]<510
    im.resize((256,256),Image.Resampling.LANCZOS).save(ROOT/'Common'/a['icon'])
    x=20+(i%3)*500;y=125+(i//3)*470
    draw.rounded_rectangle((x,y,x+460,y+445),radius=14,fill='#1d2a37',outline='#344b5e',width=2)
    label=f"{a['index']:02}  {a['name']}";label_font=bold
    if draw.textlength(label,font=bold)>420:label_font=ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf',21)
    draw.text((x+20,y+17),label,font=label_font,fill='#edf1f4')
    crop=im.crop(bbox);crop.thumbnail((350,310),Image.Resampling.LANCZOS)
    sheet.paste(crop,(x+55+(350-crop.width)//2,y+61+(310-crop.height)//2),crop)
    rifle=a['rifle'];rf=font
    if draw.textlength(rifle,font=font)>420:rf=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
    draw.text((x+20,y+384),rifle,font=rf,fill='#d3dfe7')
    draw.text((x+20,y+411),a['region'],font=font,fill='#8ca8bc')
sheet.save(ROOT/'previews/Ranger_Ammo_Contact_Sheet.png')
print('Created9 transparent icons and contact sheet.')
