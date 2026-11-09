"""Label exact native-asset mechanical key-pose studies without altering icons."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ART=Path(__file__).resolve().parents[1]
OUT=ART/'previews/reloads'
def font(size):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)
def main():
    cat=json.loads((ART/'artcatalog.json').read_text());data=json.loads((OUT/'keyposes.json').read_text());cols=5;w=320;h=180;pad=18;header=116;rowh=246
    sheet=Image.new('RGB',(cols*w+2*pad,header+len(cat['assets'])*rowh+48),(15,23,34));d=ImageDraw.Draw(sheet)
    d.text((pad,12),'Ranger rifles — original reload mechanisms',font=font(30),fill=(237,242,250))
    d.text((pad,53),'Actual native model / texture / clip key poses. Receiver closeups; muzzle and stock intentionally cropped.',font=font(18),fill=(172,192,214))
    d.text((pad,79),'Offline mechanism study, not an in-client avatar screenshot. Exact FPS/TPS clips also animate player arms.',font=font(18),fill=(172,192,214))
    labels=['Rest','Open bolt / gate','Feed cartridge 1','Feed / recharge / cartridge 2','Return to ready']
    for row,a in enumerate(cat['assets']):
        y=header+row*rowh;reload=a['reload'];title=f"{a['tier']:02}  {a['name']}   ·   {reload['durationSeconds']:.2f}s   ·   {reload['rig_style']}"
        d.text((pad,y),title,font=font(20),fill=(228,235,247))
        poses=[p for p in data['keyposes'] if p['index']==a['tier']]
        for i,p in enumerate(poses):
            image=Image.open(ART/p['path']).convert('RGB').resize((w,h),Image.Resampling.LANCZOS);sheet.paste(image,(pad+i*w,y+30))
            d.text((pad+i*w+5,y+212),labels[i]+f"  {p['frame']/60:.2f}s",font=font(15),fill=(173,193,215))
        # Per-rifle readable strip for review / guide integration.
        strip=sheet.crop((0,y-2,sheet.width,y+rowh-2));strip.save(OUT/f"{a['tier']:02}_storyboard.png")
    d.text((pad,sheet.height-37),'Legendary partial top-offs use a separate one-cartridge ReloadSingle clip at the same 2.70-second duration.',font=font(18),fill=(181,210,230))
    sheet.save(ART/'previews/reload-contact-sheet.jpg',quality=94)
    print('RELOAD_CONTACT_READY',sheet.size)
if __name__=='__main__':main()
