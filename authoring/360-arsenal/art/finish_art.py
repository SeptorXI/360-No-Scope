"""Native 64x64 RGBA icons and labelled family contact sheets from renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

ART=Path(__file__).resolve().parent
FAMILIES={'handgun':'HANDGUNS','smg':'SUBMACHINE GUNS','semiauto':'SEMI AUTO RIFLES','automatic':'FULL AUTO RIFLES','shotgun':'SHOTGUNS'}
COLORS={'Common':'#adb9bb','Uncommon':'#98bd74','Rare':'#72a9dc','Epic':'#b794dc','Legendary':'#f2c879'}

def font(size,bold=False):
    path=Path('C:/Windows/Fonts')/('bahnschrift.ttf' if bold else 'segoeui.ttf')
    return ImageFont.truetype(str(path),size)

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def main():
    catalog=json.loads((ART/'artcatalog.json').read_text());out=ART/'Common/Icons/ItemsGenerated';out.mkdir(parents=True,exist_ok=True)
    masters=ART/'previews/icon-masters';masters.mkdir(exist_ok=True)
    for a in catalog['assets']+catalog['ammo']:
        stem=Path(a['scene']).name.removesuffix('.scene.json');render=Image.open(ART/'previews'/f'{stem}.png').convert('RGBA');box=render.getbbox()
        if not box:raise ValueError('Blank actual render '+stem)
        crop=render.crop(box);crop.thumbnail((232,232),Image.Resampling.LANCZOS);master=Image.new('RGBA',(256,256));master.alpha_composite(crop,((256-crop.width)//2,(256-crop.height)//2));master.save(masters/(stem+'.png'))
        icon=master.resize((64,64),Image.Resampling.LANCZOS);icon.save(ART/'Common'/a['icon'])
    for family,title in FAMILIES.items():
        rows=[a for a in catalog['assets'] if a['family']==family];sheet=Image.new('RGB',(1500,1130),'#10171f');d=ImageDraw.Draw(sheet)
        d.text((35,22),'360 NO SCOPE  /  '+title,font=font(28,True),fill='#f0e6cf');d.text((35,64),'Original editable models · dedicated ammunition · nine regional designs',font=font(18),fill='#94a4b1')
        for n,a in enumerate(rows):
            x=20+(n%3)*495;y=110+(n//3)*335;d.rounded_rectangle((x,y,x+480,y+319),10,fill='#19242e',outline='#35424f',width=1)
            stem=Path(a['scene']).name.removesuffix('.scene.json');im=Image.open(ART/'previews'/f'{stem}.png').convert('RGBA');im.thumbnail((455,236));sheet.paste(im,(x+12,y+5),im)
            ammo=next(v for v in catalog['ammo'] if v['item_id']==a['reload']['ammo_prop']);am=Image.open(ART/'Common'/ammo['icon']).convert('RGBA').resize((52,52),Image.Resampling.NEAREST);sheet.paste(am,(x+413,y+241),am)
            name=a['name'];label=name if len(name)<40 else name[:37]+'…';d.text((x+17,y+244),label,font=font(18,True),fill=COLORS[a['quality']]);d.text((x+17,y+274),f"{a['quality']}  ·  {a['reload']['capacity']}-round capacity",font=font(15),fill='#b1bfca')
        sheet.save(ART/'previews'/f'Arsenal_{family}_Contact_Sheet.jpg',quality=94)
    overall=Image.new('RGB',(2500,3180),'#10171f');d=ImageDraw.Draw(overall);d.text((30,20),'360 NO SCOPE  /  THE ARSENAL',font=font(40,True),fill='#f0e6cf');d.text((30,75),'45 original firearms · five weapon families · nine regional themes each',font=font(23),fill='#a2b1bd')
    for col,(family,title) in enumerate(FAMILIES.items()):
        x=col*500;d.text((x+20,124),title,font=font(23,True),fill='#e1c797')
        for row,a in enumerate(v for v in catalog['assets'] if v['family']==family):
            y=170+row*330;d.rounded_rectangle((x+10,y,x+490,y+315),10,fill='#19242e');stem=Path(a['scene']).name.removesuffix('.scene.json');im=Image.open(ART/'previews'/f'{stem}.png').convert('RGBA');im.thumbnail((470,240));overall.paste(im,(x+15,y),im)
            name=a['name'];label=name if len(name)<39 else name[:36]+'…';d.text((x+25,y+250),label,font=font(19,True),fill=COLORS[a['quality']]);d.text((x+25,y+279),a['quality']+'  ·  '+str(a['reload']['capacity'])+' rounds',font=font(16),fill='#acbcca')
    overall.save(ART/'previews/Arsenal_All_45_Contact_Sheet.jpg',quality=94)
    legends=Image.new('RGB',(1640,2350),'#0d141d');d=ImageDraw.Draw(legends)
    d.text((35,25),'360 NO SCOPE  /  LEGENDARY INVENTIONS',font=font(37,True),fill='#f0e6cf')
    d.text((35,80),'Ten unique silhouettes · original geometry · moving mechanical and prism assemblies',font=font(23),fill='#acbbc7')
    d.text((35,133),'DEEPWORKS  /  BRUTAL MACHINERY',font=font(25,True),fill='#e8b36e');d.text((845,133),'LUMINIA  /  DIVINE ALIEN RELICS',font=font(25,True),fill='#a8eaf8')
    for row,(family,title) in enumerate(FAMILIES.items()):
        y=185+row*425
        for col,index in enumerate((5,6)):
            a=next(v for v in catalog['assets'] if v['family']==family and v['artIndex']==index);x=20+col*810
            d.rounded_rectangle((x,y,x+790,y+405),12,fill='#18232e',outline='#48515c',width=2)
            d.text((x+20,y+15),title,font=font(20,True),fill='#b5c3ce')
            stem=Path(a['scene']).name.removesuffix('.scene.json');im=Image.open(ART/'previews'/f'{stem}.png').convert('RGBA');im.thumbnail((750,315));legends.paste(im,(x+20,y+40),im)
            label=a['name'];label=label if len(label)<53 else label[:50]+'…';d.text((x+20,y+361),label,font=font(23,True),fill='#f0ce8e' if col==0 else '#b7edff')
    legends.save(ART/'previews/Arsenal_Legendary_Ten_Contact_Sheet.jpg',quality=95)
    print('Exported90 native64x64icons and7 contact sheets.')

if __name__=='__main__':main()
