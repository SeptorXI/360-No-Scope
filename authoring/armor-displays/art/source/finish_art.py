"""Create native RGBA8 inventory icons and labeled exact-geometry review sheets."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('seguisb.ttf' if b else 'segoeui.ttf'),n)
def fit(image,size):
    bbox=image.getbbox();assert bbox
    out=image.crop(bbox);out.thumbnail(size,Image.Resampling.LANCZOS);return out

def main():
    c=json.loads((ROOT/'art-contract.json').read_text())
    sheet=Image.new('RGB',(1800,1350),'#111b23');d=ImageDraw.Draw(sheet)
    d.text((44,25),'ARMOR DISPLAYS',font=font(40,True),fill='#f1eee4')
    d.text((45,80),'Armor stands and wall weapon mounts / original Hytale furniture / two material styles',font=font(23),fill='#9db3bf')
    titles=['ARMOR STAND','SINGLE WALL HOLDER','THREE-WEAPON WALL RACK']
    for index,a in enumerate(c['assets']):
        renders=[Image.open(ROOT/'previews'/(a['id']+'_'+angle+'.png')).convert('RGBA') for angle in ('Front_Left','Front','Rear_Right')]
        for img in renders:
            bounds=img.getbbox();assert bounds and min(bounds[:2])>2 and max(bounds[2:])<766,(a['id'],bounds)
        icon=Image.new('RGBA',(64,64));crop=fit(renders[0],(60,60));icon.alpha_composite(crop,((64-crop.width)//2,(64-crop.height)//2))
        path=ROOT/'Common'/a['icon'];path.parent.mkdir(parents=True,exist_ok=True);icon.save(path)
        row=index//3;col=index%3;x=30+col*590;y=140+row*580
        accent='#d2b57d' if a['style']=='Wood' else '#8ec9d0'
        d.rounded_rectangle((x,y,x+560,y+540),radius=14,fill='#1b2b36',outline='#344955',width=2)
        d.text((x+20,y+16),titles[col],font=font(21,True),fill=accent)
        d.text((x+20,y+46),'WOOD & FORGED IRON' if a['style']=='Wood' else 'METAL & RUBBER',font=font(16),fill='#90a7b3')
        crop=fit(renders[0],(520,402));sheet.paste(crop,(x+(560-crop.width)//2,y+80+(402-crop.height)//2),crop)
        iconlarge=icon.resize((72,72),Image.Resampling.NEAREST);sheet.paste(iconlarge,(x+470,y+451),iconlarge)
        label={'stand':'4 armor slots + hand equipment','holder':'1 actual weapon','rack':'3 independent weapon slots'}[a['kind']]
        d.text((x+20,y+493),label,font=font(19),fill='#b6c6cc')
        views=Image.new('RGB',(1800,800),'#111b23');vd=ImageDraw.Draw(views)
        vd.text((40,24),a['name'].upper(),font=font(30,True),fill='#f1eee4')
        vd.text((42,68),'Exact authored geometry; empty fixtures shown without player equipment.',font=font(20),fill='#91a9b6')
        for j,(im,title) in enumerate(zip(renders,('FRONT LEFT','FRONT','REAR RIGHT'))):
            px=25+j*590;vd.rounded_rectangle((px,112,px+565,704),radius=14,fill='#1b2b36')
            vd.text((px+20,130),title,font=font(20,True),fill=accent)
            crop=fit(im,(530,510));views.paste(crop,(px+(565-crop.width)//2,177+(510-crop.height)//2),crop)
        vd.text((42,737),f"{a['cubeCount']} original cuboids | 512px pixel atlas | native 64px icon | front -Z / wall +Z",font=font(20),fill='#b6c6cc')
        views.save(ROOT/'previews'/(a['id']+'_Views.png'))
    d.text((45,1311),'Exact-geometry offline renders. Equipped armor and weapons are supplied by the separate in-game display runtime.',font=font(19),fill='#7e98a5')
    sheet.save(ROOT/'previews/Armor_Displays_Contact_Sheet.png')
    print('Six 64px icons and seven review sheets created')

if __name__=='__main__':main()
