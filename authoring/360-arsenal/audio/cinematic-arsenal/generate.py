"""Cinematic CC0 firearm redesign for the 45 expansion guns, audio assets only."""
from pathlib import Path
from functools import lru_cache
from itertools import product
import hashlib,json,subprocess,sys
from zipfile import ZipFile
import numpy as np

ROOT=Path(__file__).resolve().parent
AUDIO=ROOT.parent;PROJECT=AUDIO.parent
sys.path.insert(0,str(AUDIO/'cinematic-prototype'))
from build_prototype import RATE,decode,decode_channel,component,mix,peak4,metrics,db,gain,wav,encode,write,shot,burst,budget

BANK=AUDIO/'open-source-bank'
OLD_SOURCES=PROJECT.parent/'ranger-snipers/audio/sources'
SOURCE=json.loads((BANK/'source-manifest.json').read_text(encoding='utf-8-sig'))
BY_SOURCE={s['id']:s for s in SOURCE['sources']}
SPEC=json.loads((PROJECT/'content/arsenal-spec.json').read_text(encoding='utf-8-sig'))
FOUNDATIONS={
 'handgun':('ffsl_1911_near_alt',1,[1.144,5.055,10.003]),
 'smg':('ffsl_m45_near_alt',1,[.191,2.979,6.832]),
 'semiauto':('ffsl_ar15_near_alt',0,[.500,.500,.500]),
 'automatic':('ffsl_ak47_near_alt',0,[.798,7.525,11.239]),
 'shotgun':('ffsl_nova_behind',1,[1.480,1.480,1.480]),
}
FAMILY={
 'handgun':dict(report=.33,peak=-4.8,mechanism='ffsl_1911_rack',mechStart=.201,mechDuration=.26,mechDelay=.045,mechPeak=-17.5,tail=.98,tailPeak=-25,maxDistance=80),
 'smg':dict(report=.21,peak=-8.0,mechanism='ffsl_ak47_cycle',mechStart=.188,mechDuration=.16,mechDelay=.035,mechPeak=-21,tail=.85,tailPeak=-29,maxDistance=80),
 'semiauto':dict(report=.41,peak=-4.7,mechanism='ffsl_ak47_cycle',mechStart=.188,mechDuration=.29,mechDelay=.065,mechPeak=-17,tail=1.45,tailPeak=-24.5,maxDistance=140),
 'automatic':dict(report=.34,peak=-6.8,mechanism='ffsl_ak47_cycle',mechStart=.188,mechDuration=.23,mechDelay=.045,mechPeak=-19,tail=1.22,tailPeak=-26,maxDistance=128),
 'shotgun':dict(report=.55,peak=-4.2,mechanism='ffsl_nova_pump',mechStart=1.030,mechDuration=.70,mechDelay=.16,mechPeak=-16,tail=1.65,tailPeak=-24,maxDistance=112),
}

@lru_cache(maxsize=24)
def old_path(pack,filename):
    matches=list((OLD_SOURCES/pack/'extracted').glob(filename));assert len(matches)==1,(pack,filename)
    return str(matches[0])

def src(ident,start,duration,peak,channel=0,lo=40,hi=15500,rate=1,offset=0,fade=.05):
    return dict(path=BY_SOURCE[ident]['path'],sourceId=ident,sourceChannel=channel,startSeconds=start,durationSeconds=duration,
                peakDb=peak,highpassHz=lo,lowpassHz=hi,playbackRate=rate,outputOffsetSeconds=offset,fadeInSeconds=.0004,fadeOutSeconds=fade)

def blue(pack,name,start,duration,peak,lo=50,hi=6500,rate=1,offset=0):
    return dict(path=old_path(pack,name),sourceId=pack,startSeconds=start,durationSeconds=duration,peakDb=peak,
                highpassHz=lo,lowpassHz=hi,playbackRate=rate,outputOffsetSeconds=offset,fadeInSeconds=.001,fadeOutSeconds=min(.08,duration*.25))

def theme_components(theme,family,variant):
    # Foreground pressure remains a recorded firearm. Accents are authored free-use
    # machinery/energy materials, typically 12–20 dB below its initiating report.
    rates=[.99,1.015,1.0];r=rates[variant]
    low='Bluezone_BC0284_soundwave_weapon_scifi_shot_low_001.wav'
    prism='Bluezone_BC0286_invader_weapon_scifi_shot_006_03.wav'
    glass='Bluezone_BC0284_soundwave_weapon_scifi_shot_004_02.wav'
    void='Bluezone_BC0286_invader_alien_scifi_texture_low_001.wav'
    steel='Bluezone_BC0287_annihilation_mech_mechanical_texture_007_01.wav'
    peak=-17 if family in ('shotgun','semiauto') else -20 if family=='smg' else -18.5
    if theme==1:return [blue('bluezone-weapon',low,.01,.25,peak-2,55,700,rate=r)]
    if theme==2:return [blue('bluezone-mechanical',steel,.215,.16,peak-3,1200,9000,rate=r*1.04)]
    if theme==3:return [blue('bluezone-transformers',glass,.03,.25,peak-1,1000,11500,rate=r*1.03)]
    if theme==4:return [blue('bluezone-robot',void,.015,.36,peak-1,60,1800,rate=r*.92)]
    if theme==5:return [blue('bluezone-weapon',low,.012,.49,peak+2.2,44,2200,rate=r*.94),blue('bluezone-mechanical',steel,.215,.22,peak-5,400,8500,rate=r*.97,offset=.027)]
    if theme==6:return [blue('bluezone-robot',prism,.012,.48,peak+1,350,13500,rate=r)]
    if theme==7:return [blue('bluezone-robot',void,.015,.42,peak-1,72,2650,rate=r*.87)]
    if theme==8:return [blue('bluezone-mechanical',steel,.215,.26,peak-1,500,11500,rate=r*1.03)]
    return [blue('bluezone-transformers',glass,.025,.35,peak-2,1100,10500,rate=r*1.07)]

def layers_for(t):
    family=t['family'];p=FAMILY[family];ident,ch,onsets=FOUNDATIONS[family];theme=t['artIndex']
    theme_rate={1:.98,2:1.025,3:1.015,4:.955,5:.965,6:1.02,7:.95,8:1.01,9:1.035}[theme]
    variants=[];mechanisms=[];tails=[];provenance=[]
    for i in range(3):
        # A tiny take-dependent rate change supplements the one clean AR/Nova take;
        # it is never represented as three separately recorded takes.
        rate=theme_rate*([1,.994,1.008][i] if family in ('semiauto','shotgun') else [1,1.002,.998][i])
        attack=src(ident,max(0,onsets[i]-.0015),p['report'],p['peak'],channel=ch,lo=42 if family=='shotgun' else 65,hi=15500,rate=rate,fade=.05)
        body_design={
            'handgun':('Bluezone_BC0284_soundwave_weapon_scifi_shot_low_001.wav',.012,.29,-10.5,85,2400),
            'smg':('Bluezone_BC0284_soundwave_weapon_scifi_shot_low_003.wav',.87,.23,-8.6,120,3500),
            'semiauto':('Bluezone_BC0284_soundwave_weapon_scifi_shot_low_003.wav',.87,.42,-8.8,65,3000),
            'automatic':('Bluezone_BC0284_soundwave_weapon_scifi_shot_low_003.wav',.87,.32,-9.8,80,3200),
            'shotgun':('Bluezone_BC0284_soundwave_weapon_scifi_shot_low_003.wav',.865,.52,-7.8,45,2100),
        }[family]
        name,begin,duration,body_peak,lo,hi=body_design
        pressure=blue('bluezone-weapon',name,begin,duration,body_peak,lo,hi,rate=theme_rate*[.994,1.006,1][i])
        cs=[attack,pressure]+theme_components(theme,family,i)
        parts=[component(c,ROOT,provenance) for c in cs]
        variants.append(mix(parts,[round(c.get('outputOffsetSeconds',0)*RATE) for c in cs]))
        m=src(p['mechanism'],p['mechStart'],p['mechDuration'],p['mechPeak']+(1 if theme==5 else 0),channel=0,lo=280,hi=10500,rate=theme_rate*[1,1.02,.985][i],fade=.035)
        mechanisms.append(component(m,ROOT,provenance))
        donor='ffsl_nova_mid_actual' if family=='shotgun' else 'ffsl_mosin_mid'
        donor_onset=.0
        technical=BY_SOURCE[donor]['technical']
        donor_onset=technical['firstRelativeMinus40DbOnsetSeconds']
        # Remove the recorded initial discharge completely; only later returns
        # remain. Native event delays this once, at the fixed firing source point.
        natural=src(donor,donor_onset+.145,p['tail'],p['tailPeak'],channel=i%2,lo=170,hi=4800 if theme not in (4,7) else 3300,rate=[1,.985,1.018][i],fade=.24)
        echo1=src(ident,max(0,onsets[i]-.0015),.14,p['tailPeak']-2,channel=ch,lo=280,hi=3600,rate=rate,offset=.16,fade=.095)
        echo2=src(ident,max(0,onsets[i]-.0015),.16,p['tailPeak']-10,channel=ch,lo=450,hi=2100,rate=rate,offset=.48,fade=.12)
        tail_cs=[natural,echo1,echo2]
        tails.append(mix([component(c,ROOT,provenance) for c in tail_cs],[round(c.get('outputOffsetSeconds',0)*RATE) for c in tail_cs]))
    family_gain={'handgun':2,'smg':0,'semiauto':1.8,'automatic':.8,'shotgun':1}[family]
    for group in (variants,mechanisms,tails):
        for i in range(len(group)):group[i]*=gain(family_gain)
    # At the firing player's reference position: dry Local is 0 dB, optional
    # owner tail equals the -3 dB World tail, including its event-level gain.
    return [dict(name='Report',delay=0,volumeDb=0,variants=variants),dict(name='Mechanism',delay=round(p['mechDelay']*RATE),volumeDb=0,variants=mechanisms),dict(name='OutdoorDecay',delay=round(.07*RATE),volumeDb=-3,variants=tails)],provenance

def main():
    write(ROOT/'validation.json',{'version':'2.0.5','passed':False,'failures':['Generation in progress; output not ready for assembly.']})
    catalog={'version':'2.0.5','sourcePolicy':'CC0 authentic firearm/weapon mechanics foundation + credited Bluezone free-use theme accents; no Suno sources',
             'clips':[],'events':[],'weapons':[],'ownerTailBindings':[],'sourceManifest':'../open-source-bank/source-manifest.json',
             'engineLimitations':['Outdoor decay is authored fixed-position sound, not geometric terrain reflection or proven automatic room adaptation.','Native room reverb scope for weapon SFX is unproven; no AmbienceFX assets are changed.']}
    artifact=PROJECT/'release/360-No-Scope-2.0.4.jar'
    with ZipFile(artifact) as z:
        oldevents={Path(n).stem:(n,json.loads(z.read(n))) for n in z.namelist() if n.startswith('Server/Audio/SoundEvents/') and n.endswith('.json')}
        for index,t in enumerate(SPEC['tiers'],1):
            slug=t['id'].removeprefix('Weapon_Crossbow_');layers,provenance=layers_for(t);cycle=t['cycleSeconds'];p=FAMILY[t['family']]
            scale,evidence=budget(layers,cycle)
            for l in layers:l['variants']=[x*scale for x in l['variants']]
            native=[];weaponclips=[]
            for l in layers:
                action={'Report':'Fire','Mechanism':'FireMechanism','OutdoorDecay':'FireTail'}[l['name']];files=[];decoded=[]
                for i,x in enumerate(l['variants'],1):
                    rel=f'Common/Sounds/Arsenal/{slug}/{action}_{i:02}.ogg';a=encode(ROOT/rel,x);decoded.append(a);files.append(rel.removeprefix('Common/'))
                    r={'path':rel,'runtimePath':rel,'weaponId':t['id'],'stem':l['name'],'variant':i,'channels':1,'sampleRate':RATE,'sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),**metrics(a)}
                    catalog['clips'].append(r);weaponclips.append(r)
                l['variants']=decoded;native.append(dict(Files=files,Volume=0,StartDelay=l['delay']/RATE,Looping=False,RoundRobinHistorySize=1))
            ids=t['audio']['events']['Fire'];owner_id=ids['Local'].removesuffix('_Local')+'_Tail_Owner'
            for route,id in [('Local',ids['Local']),('World',ids['World']),('OwnerTail',owner_id)]:
                path,original=oldevents[ids['Local'] if route=='OwnerTail' else id]
                if route=='OwnerTail':path=str(Path(path).with_name(id+'.json')).replace('\\','/')
                e=dict(original);e.update(dict(Volume=0 if route=='Local' else -3,SpatialBlend=0 if route=='Local' else 1,
                    StartAttenuationDistance=0 if route=='Local' else 4,MaxDistance=p['maxDistance'],MaxInstance=32,PreventSoundInterruption=False,
                    Layers=native[:2] if route=='Local' else native[2:] if route=='OwnerTail' else native))
                write(ROOT/path,e);catalog['events'].append({'id':id,'path':path,'weaponId':t['id'],'route':route,'layers':len(e['Layers']),'maxDistance':p['maxDistance'],'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()})
            combinations=[peak4(shot(layers,c)) for c in product(range(3),repeat=3)]
            burst_max=max(peak4(burst(layers,cycle,s)) for s in range(32)) if t['automatic'] else None
            maximum=max(combinations+([burst_max] if burst_max else []))
            if db(maximum)>-1:raise ValueError(t['id']+' decoded mix exceeds -1 dBFS')
            single=shot(layers,[0,0,0]);tail_fraction=float(np.sum(single[round(cycle*RATE):]**2)/np.sum(single**2))
            catalog['weapons'].append({'weaponId':t['id'],'family':t['family'],'themeIndex':t['artIndex'],'cycleSecondsUnchanged':cycle,
                'sources':provenance,'linearBudgetGainDb':db(scale),'budget':evidence,'decodedCompositeMaxTruePeak4xDb':db(max(combinations)),
                'decoded4sBurstMaxTruePeak4xDb':db(burst_max) if burst_max else None,'single':metrics(single),'energyAfterNextShotFraction':tail_fraction,
                'sourceCleanForegroundSelection':{'sourceId':FOUNDATIONS[t['family']][0],'channel':FOUNDATIONS[t['family']][1]},
                'variantDisclosure':'Three designed variants; semiauto and shotgun derive from one verified clean recorded take with different return/tail layers and less than 1.5% rate variation.'})
            catalog['ownerTailBindings'].append({'itemId':t['id'],'action':'Fire','ownerTailEventId':owner_id,'worldTailDelaySeconds':.07})
            # Representative Crown + tier-one family auditions, at Local+owner-tail
            # reference distance inside the unattenuated region; no preview boost.
            if t['artIndex']==1 or slug=='AS_Automatic_Crown_Of_Rivets':
                wav(ROOT/f'previews/{slug}_Single_After.wav',single)
                for l in layers:wav(ROOT/f'previews/{slug}_{l["name"]}.wav',l['variants'][0])
                if t['automatic']:wav(ROOT/f'previews/{slug}_Burst_4s_After.wav',burst(layers,cycle,9))
                before_event=oldevents[ids['Local']][1];before_name='Common/'+before_event['Layers'][0]['Files'][0]
                ref=ROOT/'reference'/slug/'Fire_01.ogg';ref.parent.mkdir(parents=True,exist_ok=True);ref.write_bytes(z.read(before_name))
                before=decode(str(ref))*gain(before_event.get('Volume',0)+before_event['Layers'][0].get('Volume',0))
                wav(ROOT/f'previews/{slug}_Single_Before_After.wav',np.r_[before,np.zeros(round(RATE*1.1)),single])
                if t['automatic']:
                    before_burst=mix([before]*len(np.arange(0,4,cycle)),[round(s*RATE) for s in np.arange(0,4,cycle)])
                    wav(ROOT/f'previews/{slug}_Burst_4s_Before_After.wav',np.r_[before_burst,np.zeros(round(RATE*1.1)),burst(layers,cycle,9)])
            print(f'{index}/45 {slug}: {len(single)/RATE:.2f}s composite; true peak {db(maximum):.2f} dBFS',flush=True)
    selected_ids={c.get('processing',{}).get('sourceId') for w in catalog['weapons'] for c in w['sources']}
    old_manifest=json.loads((OLD_SOURCES/'source-manifest.json').read_text(encoding='utf-8-sig'))
    usedbank=[s for s in SOURCE['sources'] if s['id'] in selected_ids]
    usedblue=[s for s in old_manifest['packs'] if s['id'] in selected_ids]
    write(ROOT/'source-provenance.json',{'newRecordings':usedbank,'freeUseThemeAccents':usedblue,'sourceBytesPreserved':True,'noSunoSources':True})
    write(ROOT/'catalog.json',catalog)
    validation={'version':'2.0.5','passed':True,'failures':[],'weapons':45,'clips':len(catalog['clips']),'events':len(catalog['events']),
        'ownerTailBindings':len(catalog['ownerTailBindings']),'mono48000Vorbis':True,'sourcePolicy':catalog['sourcePolicy'],'sourceBytesPreserved':True,
        'runtimeOrGameplayChangedByGenerator':False,'sourceSunoCount':0,'compressionOrClippingUsed':False,
        'decodedCompositeMaximumTruePeak4xDb':max(w['decodedCompositeMaxTruePeak4xDb'] for w in catalog['weapons']),
        'decodedAutomaticBurstMaximumTruePeak4xDb':max(w['decoded4sBurstMaxTruePeak4xDb'] for w in catalog['weapons'] if w['decoded4sBurstMaxTruePeak4xDb'] is not None),
        'clientListeningOrEnvironmentAdaptationClaimed':False}
    credit='Authentic firearm and weapon-mechanic field recordings: Ben Jaszczak, Brian Nelson, Kevin Heras and Matthew Nanney, Free Firearm Sound Library (CC0 1.0).\n'+SOURCE['recommendedCredits']+'\nTheme accents: Bluezone Corporation free sound collections, used under their original included Free Sounds License (retained below).\nNo Generation Zero, Transformers film/game audio, or Suno exports are included.\n'
    credits=ROOT/'Audio Credits/Cinematic Arsenal';credits.mkdir(parents=True,exist_ok=True);(credits/'CREDITS.txt').write_text(credit,encoding='utf-8')
    for pack in usedblue:
        notice=Path(pack['originalNoticePath']);notice=notice if notice.is_absolute() else PROJECT.parent/'ranger-snipers/audio'/notice
        (credits/(pack['id']+'-Free-Sounds-License.txt')).write_bytes(notice.read_bytes())
    (credits/'CC0-license.txt').write_bytes((BANK/'evidence/firearm-CC0-LICENSE.txt').read_bytes())
    write(ROOT/'validation.json',validation)
    print(json.dumps({'passed':True,'weapons':45,'clips':len(catalog['clips']),'events':len(catalog['events']),'ownerTailBindings':45}),flush=True)

if __name__=='__main__':main()
