"""64px native-compatible icon and three-angle review sheet from exact renders."""
from pathlib import Path
import json,math,hashlib
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
FONTS=Path('C:/Windows/Fonts')
font=lambda n,b=False:ImageFont.truetype(str(FONTS/('seguisb.ttf' if b else 'segoeui.ttf')),n)
def main():
    renders=[ROOT/'previews'/('RS_Gunsmith_Bench_'+a+'.png') for a in ['Front_Left','Front_Right','Rear_Right']]
    images=[Image.open(p).convert('RGBA') for p in renders]
    for p,img in zip(renders,images):
        box=img.getbbox();assert box and box[0]>6 and box[1]>6 and box[2]<img.width-6 and box[3]<img.height-6,(p,box)
    icon=Image.new('RGBA',(64,64));crop=images[0].crop(images[0].getbbox());crop.thumbnail((60,60),Image.Resampling.LANCZOS)
    icon.alpha_composite(crop,((64-crop.width)//2,(64-crop.height)//2))
    out=ROOT/'Common/Icons/ItemsGenerated/RS_Gunsmith_Bench.png';out.parent.mkdir(parents=True,exist_ok=True);icon.save(out)
    sheet=Image.new('RGB',(1800,820),'#101b26');dr=ImageDraw.Draw(sheet)
    dr.text((44,26),'360 NO SCOPE  /  GUNSMITH BENCH',font=font(34,True),fill='#edf1ea')
    dr.text((46,78),'Original Hytale furniture art  •  walnut, forged steel & copper  •  cartridge press to energy calibration',font=font(22),fill='#9fb6c4')
    for i,(img,title) in enumerate(zip(images,['FRONT LEFT / working side','FRONT RIGHT / power module','REAR RIGHT / toolrail & joinery'])):
        x=25+i*590;dr.rounded_rectangle((x,128,x+565,697),radius=15,fill='#1c2b38',outline='#354957',width=2)
        dr.text((x+20,147),title,font=font(22,True),fill='#cfb680')
        crop=img.crop(img.getbbox());crop.thumbnail((545,480),Image.Resampling.LANCZOS)
        sheet.paste(crop,(x+(565-crop.width)//2,190+(480-crop.height)//2),crop)
    dr.text((45,726),'182 authored cuboids • selective fullbright lamp/cell surfaces • 512px original pixel atlas • native 64px item icon',font=font(22),fill='#b2c3c9')
    dr.text((45,762),'Offline exact-geometry views; native in-game lighting and placement are verified separately.',font=font(19),fill='#78929f')
    icon_big=icon.resize((96,96),Image.Resampling.NEAREST);sheet.paste(icon_big,(1640,12),icon_big)
    sheet.save(ROOT/'previews/RS_Gunsmith_Bench_Contact_Sheet.png')
    catalog=json.loads((ROOT/'bench-art-catalog.json').read_text())
    catalog['icon_size']=[64,64];catalog['preview_contact_sheet']='previews/RS_Gunsmith_Bench_Contact_Sheet.png'
    (ROOT/'bench-art-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    print('Created64px icon and three-angle contact sheet')

if __name__=='__main__':main()
