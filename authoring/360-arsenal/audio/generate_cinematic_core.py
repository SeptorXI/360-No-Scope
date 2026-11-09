"""Recorded cinematic core reports, real mechanisms, and outdoor return stems.

An isolated2.0.5 overlay: no gameplay, source recordings, or production writes.
The CC0 firearm masters provide the physical discharge/handling; licensed
Bluezone originals supply restrained fantastical material/servo accents.
The outdoor stems contain the actual late field return, never a second bang.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, json, math, subprocess, wave
import numpy as np
from enhance_core import RATE, FFMPEG, SOURCE_AUDIO, decode, db, amplitude, native_samples, kweighted, window_db, band, fade, metric, digest, write
from impact_processing import oversampled_peak

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'cinematic-core'
BANK=ROOT/'open-source-bank'
BEFORE=PROJECT/'release/360-No-Scope-2.0.4.jar'
ACTIONS={'Fire','SpecialFire','ReloadOpen','ReloadInsert','ReloadClose','Ready'}
TAIL_DELAY=.07
SLUGS=['Wildwood_Surveyor','Dunewatch_Longshot','Frostline_Sentinel','Mournhollow_Epitaph','Deepworks_Railspike','Luminia_Dawnpiercer','Nameless_Covenant','Labyrinth_Threadkeeper','Skybound_Farwatch']
STYLE=[
 dict(theme='warm brass report, substantial bolt return',shot='ffsl_mosin_near',onsets=[1.033,8.107,1.033],channel=0,speed=.97,accent=.24,mechanical=.24,tail='ffsl_mosin_mid',tailSpeed=1.02),
 dict(theme='broad dusty crack, heavy open steel action',shot='ffsl_mosin_near',onsets=[8.107,1.033,8.107],channel=1,speed=.89,accent=.30,mechanical=.32,tail='ffsl_nova_mid',tailSpeed=.94),
 dict(theme='precise bright report and cold sliding steel',shot='ffsl_ar15_near_alt',onsets=[.500,.500,.500],channel=1,speed=1.04,accent=.32,mechanical=.23,tail='ffsl_mosin_mid',tailSpeed=1.08),
 dict(theme='low sepulchral discharge and cage latch',shot='ffsl_mosin_near',onsets=[1.033,8.107,1.033],channel=0,speed=.78,accent=.40,mechanical=.33,tail='ffsl_mosin_mid',tailSpeed=.88),
 dict(theme='massive rail discharge, piston return, industrial resonance',shot='ffsl_mosin_near',onsets=[8.107,1.033,8.107],channel=0,speed=.73,accent=.58,mechanical=.42,tail='ffsl_nova_mid',tailSpeed=.84),
 dict(theme='physical cannon punch, luminous discharge and prism settle',shot='ffsl_ar15_near_alt',onsets=[.500,.500,.500],channel=0,speed=.86,accent=.72,mechanical=.27,tail='ffsl_mosin_mid',tailSpeed=.96),
 dict(theme='dark reverberant report, heavy reliquary lock',shot='ffsl_mosin_near',onsets=[1.033,8.107,1.033],channel=1,speed=.81,accent=.43,mechanical=.32,tail='ffsl_mosin_mid',tailSpeed=.90),
 dict(theme='hard physical crack and crystalline machine ring',shot='ffsl_ar15_near_alt',onsets=[.500,.500,.500],channel=0,speed=.98,accent=.49,mechanical=.26,tail='ffsl_mosin_mid',tailSpeed=1.04),
 dict(theme='open airy rifle crack, articulate relic mechanism',shot='ffsl_mosin_near',onsets=[8.107,1.033,8.107],channel=1,speed=1.02,accent=.29,mechanical=.23,tail='ffsl_nova_mid',tailSpeed=1.06),
]

class Sources:
    def __init__(self):
        self.entries={s['id']:s for s in json.loads((BANK/'source-manifest.json').read_text())['sources'] if s.get('path')}
        self.cache={};self.used={}
    def get(self,source_id,channel=0):
        s=self.entries[source_id];path=Path(s['path']);key=(str(path),channel)
        if key not in self.cache:
            raw=path.read_bytes()
            if digest(raw)!=s['sha256']:raise ValueError('Source hash changed: '+str(path))
            command=[str(FFMPEG),'-v','error','-nostdin','-i',str(path),'-af',f'pan=mono|c0=c{channel}','-ar',str(RATE),'-f','f32le','pipe:1']
            self.cache[key]=np.frombuffer(subprocess.run(command,capture_output=True,check=True).stdout,dtype='<f4').astype(float)
        self.used[source_id]=deepcopy(s)
        return self.cache[key]
    def blue(self,record,channel=0):
        source_id=record['sourceId']+':'+Path(record['path']).name
        if source_id not in self.entries:
            path=SOURCE_AUDIO/record['path'];raw=path.read_bytes()
            self.entries[source_id]={'id':source_id,'path':str(path),'sha256':digest(raw),'license':'Bluezone free-pack game-use license; not Creative Commons','creator':['Bluezone Corporation'],'sourceUrl':'https://www.bluezone-corporation.com/free-sound-effects','licenseEvidence':str(path.parent.parent/'OFFICIAL_FREE_PACK_TERMS.txt'),'role':'designed mechanical/energy accent; not film audio'}
        return self.get(source_id,channel),source_id

def excerpt(x,start,duration,speed=1,attack=.001,release=.07):
    count=round(duration*RATE);pos=start*RATE+np.arange(count)*speed
    y=np.interp(pos,np.arange(len(x)),x,left=0,right=0)
    return fade(y,attack,release)

def level(x):
    return x/max(float(np.max(np.abs(x))),1e-10)

def place(dst,src,seconds,gain=1):
    start=round(seconds*RATE);n=min(len(src),len(dst)-start)
    if n>0:dst[start:start+n]+=src[:n]*gain

def source_ref(source_id,start,duration,speed=1,channel=0,role='',gain=1):
    return dict(sourceId=source_id,sourceStartSeconds=start,outputDurationSeconds=duration,playbackRatio=speed,channel=channel,role=role,relativeGain=gain)

def fire(sources,profile,style,variant,special=False):
    duration=1.65 if special else 1.18
    mix=np.zeros(round(duration*RATE));refs=[];v=variant-1
    speed=style['speed']*(1+.009*(v-1))*(.91 if special else 1)
    shot=sources.get(style['shot'],style['channel']);start=style['onsets'][v]-.002
    direct=excerpt(shot,start,.58 if special else .45,speed,.00035,.09)
    # Preserve the real initial pressure transient. Its low-mid body is a
    # separately balanced *recorded* layer, rather than a generated sine boom.
    direct=band(direct,65,12500)
    place(mix,level(direct),0,.70)
    refs.append(source_ref(style['shot'],start,len(direct)/RATE,speed,style['channel'],'authentic direct report',.70))
    body=excerpt(shot,start,.72 if special else .55,speed*.79,.0008,.13)
    body=band(body,50,720)
    place(mix,level(body),.003,.46 if special else .36)
    refs.append(source_ref(style['shot'],start,len(body)/RATE,speed*.79,style['channel'],'recorded low-mid pressure body',.46 if special else .36))
    # Real industrial metal supplies the sustained physical mass that a
    # close-microphone firearm pressure impulse alone does not contain.
    # Its upper ambience is excluded: this is a finite low-mid material hit.
    metal_id='sardin_aluminum_workshop';metal_start=[5.02,26.45,34.04][v]
    metal=excerpt(sources.get(metal_id),metal_start,.58 if special else .46,max(.60,style['speed']*.84),.002,.13)
    metal=band(metal,65,1100)
    metal_gain=(1.20 if special else 1.00)*(1.12 if style['speed']<.85 else 1)
    place(mix,level(metal),.009,metal_gain)
    refs.append(source_ref(metal_id,metal_start,len(metal)/RATE,max(.60,style['speed']*.84),0,'CC0 recorded industrial low-mid metal mass; upper machine ambience filtered',metal_gain))
    robotic=profile['robotic'];rec=robotic['primary'] if v==0 else robotic.get('variations',[robotic['primary']]*3)[(v-1)%len(robotic.get('variations',[1]))]
    raw,sid=sources.blue(rec);a=rec.get('anchorSeconds',0)
    accent=excerpt(raw,a,min(duration-.03,.95 if special else .78),.86 if special else 1,.0008,.12)
    accent=band(accent,110,10000)
    gain=style['accent']*(1.13 if special else 1)
    place(mix,level(accent),.006,gain)
    refs.append(source_ref(sid,a,len(accent)/RATE,.86 if special else 1,0,'cinematic designed material/energy accent',gain))
    # A single real rack movement follows the blast, with sufficient sustain
    # for the returning carrier and metal contact to remain audible.
    mech_id='ffsl_ak47_cycle' if special or profile['energized'] else 'ffsl_mosin_bolt'
    mech_start=.37 if mech_id=='ffsl_ak47_cycle' else 3.85
    mech=excerpt(sources.get(mech_id),mech_start,.48,.76 if special else .93,.001,.08)
    mech=band(mech,150,7600)
    place(mix,level(mech),.13,style['mechanical'])
    refs.append(source_ref(mech_id,mech_start,.48,.76 if special else .93,0,'authentic return mechanism',style['mechanical']))
    # Finite physical/energy residue is retained beyond the first100ms.
    mix=band(mix,42,14500);mix-=np.mean(mix)
    return fade(mix,.00035,.10),refs

def outdoor(sources,style,variant,special=False):
    sid=style['tail'];onsets=[2.122,10.409,20.143] if sid=='ffsl_mosin_mid' else [.899,6.770,.899]
    start=onsets[variant-1]+.120
    duration=2.55 if special else 2.05
    raw=sources.get(sid,1);speed=style['tailSpeed']*(.94 if special else 1)
    # Initial clipped muzzle impulse is excluded in the raw source domain;
    # the stem starts in the unclipped late outdoor reflection field.
    out=excerpt(raw,start,duration,speed,.024,.28)
    out=band(out,100,8400);out-=np.mean(out)
    return fade(out,.024,.28),[source_ref(sid,start,duration,speed,1,'natural outdoor decay; initiating bang excluded')]

def reload(sources,profile,style,action):
    definitions={
      'ReloadOpen':('ffsl_mosin_bolt',.602,.59,.87,.68),
      'ReloadInsert':('ffsl_1911_mag_seat',.837,.49,.90,.62),
      'ReloadClose':('ffsl_ak47_cycle',1.385,.45,.94,.67),
      'Ready':('ffsl_1911_rack',.407,.27,1.02,.37),
    }
    sid,start,duration,speed,physical_gain=definitions[action]
    speed*=min(1.10,max(.77,style['speed']))
    mix=np.zeros(round(duration*RATE));refs=[]
    physical=excerpt(sources.get(sid),start,duration,speed,.0005,.06)
    place(mix,level(band(physical,90,10000)),0,physical_gain)
    refs.append(source_ref(sid,start,duration,speed,0,'authentic firearm mechanism',physical_gain))
    # A slower copy of the actual action supplies mass, not an artificial boom.
    body=excerpt(sources.get(sid),start,duration,speed*.72,.001,.07)
    place(mix,level(band(body,70,1300)),.003,.29 if action!='Ready' else .15)
    refs.append(source_ref(sid,start,duration,speed*.72,0,'recorded steel body',.29 if action!='Ready' else .15))
    if action!='Ready':
        metal_id='sardin_aluminum_workshop';metal_start={'ReloadOpen':26.45,'ReloadInsert':5.02,'ReloadClose':34.04}[action]
        metal=excerpt(sources.get(metal_id),metal_start,duration,.82,.001,.09)
        place(mix,level(band(metal,80,1900)),.005,.35)
        refs.append(source_ref(metal_id,metal_start,duration,.82,0,'recorded heavy metal contact and settling rattle',.35))
    key={'ReloadOpen':'open','ReloadInsert':'insert','ReloadClose':'close','Ready':'close'}[action]
    rec=profile['robotic'][key];raw,accent_id=sources.blue(rec);a=rec.get('anchorSeconds',0)
    accent=excerpt(raw,a,duration,.78 if profile['energized'] else .91,.002,.08)
    gain=.26 if profile['energized'] else .15
    if action=='Ready':gain*=.5
    place(mix,level(band(accent,180,8800)),.009,gain)
    refs.append(source_ref(accent_id,a,duration,.78 if profile['energized'] else .91,0,'themed ratchet/servo material accent',gain))
    mix=band(mix,65,12000);mix-=np.mean(mix)
    return fade(mix,.0006,.055),refs

def encode(path,x,kind,special=False):
    # Gain staging follows each arrangement's natural crest, with no forced
    # RMS/attack floor and no flattened peak transient.
    target={'fire':-2.9,'tail':-15.5 if special else -18.0,'reload':-6.3,'ready':-9.0}[kind]
    x=x*amplitude(target-db(oversampled_peak(x)))
    path.parent.mkdir(parents=True,exist_ok=True)
    command=[str(FFMPEG),'-v','error','-nostdin','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','pipe:0','-map_metadata','-1','-c:a','libvorbis','-q:a','7',str(path)]
    for _ in range(3):
        subprocess.run(command,input=x.astype('<f4').tobytes(),capture_output=True,check=True)
        raw=path.read_bytes();audio=decode(raw);peak=db(oversampled_peak(audio))
        if peak<=(-2.25 if kind=='fire' else -1.8):break
        x*=amplitude(-2.5-peak)
    m=metric(audio);m['truePeak4xDbFS']=db(oversampled_peak(audio))
    return raw,audio,m

def full_event_mix(event,clip_audio,variant=0):
    count=max(round(layer.get('StartDelay',0)*RATE)+len(clip_audio['Common/'+layer['Files'][variant%len(layer['Files'])]]) for layer in event['Layers'])
    out=np.zeros(count)
    for layer in event['Layers']:
        place(out,clip_audio['Common/'+layer['Files'][variant%len(layer['Files'])]],layer.get('StartDelay',0),amplitude(event.get('Volume',0)+layer.get('Volume',0)))
    return out

def save_wave(path,x):
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview-only',action='store_true');args=parser.parse_args()
    src=Sources();profiles=json.loads((SOURCE_AUDIO/'profiles.json').read_text())['profiles'];profiles={p['slug']:p for p in profiles}
    baseline=json.loads((PROJECT/'baseline/audio-catalog-1.7.0.json').read_text());spec=json.loads((PROJECT/'baseline/sniper-spec.json').read_text());tiers={t['id']:t for t in spec['tiers']}
    selected=[c for c in baseline['clips'] if c['action'] in ACTIONS]
    if args.preview_only:selected=[c for c in selected if c['rifleId'].endswith('Luminia_Dawnpiercer')]
    OUT.mkdir(parents=True,exist_ok=True)
    clips=[];events=[];bindings=[];audio={};before_audio={};before_events={};after_events={};recipes=[]
    with ZipFile(BEFORE) as z:
        for c in baseline['clips']:before_audio[c['runtimePath']]=decode(z.read(c['runtimePath']))
        for e in baseline['events']:before_events[e['id']]=json.loads(z.read(e['path']))
    jobs=[]
    for c in selected:
        slug=c['rifleId'].removeprefix('Weapon_Crossbow_');idx=SLUGS.index(slug);style=STYLE[idx];profile=profiles[slug];action=c['action'];variant=c['variant']
        if action in ('Fire','SpecialFire'):
            x,refs=fire(src,profile,style,variant,action=='SpecialFire');kind='fire'
        else:x,refs=reload(src,profile,style,action);kind='ready' if action=='Ready' else 'reload'
        jobs.append((deepcopy(c),x,refs,kind,style['theme']))
        if action in ('Fire','SpecialFire'):
            tail,refs=outdoor(src,style,variant,action=='SpecialFire');tailc=deepcopy(c);tailc['action']=action+'Tail';tailc['id']=tailc['id'].replace('_'+action+'_','_'+action+'Tail_');tailc['path']=tailc['path'].replace('/'+action+'_','/'+action+'Tail_');tailc['runtimePath']='Common/'+tailc['path'];jobs.append((tailc,tail,refs,'tail',style['theme']))
    def render(job):
        c,x,refs,kind,theme=job;raw,y,m=encode(OUT/c['runtimePath'],x,kind,c['action'].startswith('SpecialFire'))
        refs=[dict(r,path=src.entries[r['sourceId']]['path'],sha256=src.entries[r['sourceId']]['sha256'],license=src.entries[r['sourceId']]['license'])for r in refs]
        record={k:c[k] for k in ('id','rifleId','action','variant','path','runtimePath')};record.update(sha256=digest(raw),sampleRate=RATE,channels=1,durationSeconds=len(y)/RATE,nativeSamples=native_samples(raw),sources=refs,theme=theme,after=m,processing={'method':'new arrangement of recorded physical discharge, pressure body, real metal return and restrained designed accent; no generated tones','sourceOnly':True,'stereoHandling':'one original microphone channel; no opposed-mic averaging','gainStage':'preserved crest, peak-normalized, no uniform RMS or attack floor'})
        if c['runtimePath'] in before_audio:record['before']=metric(before_audio[c['runtimePath']]);record['sourceArtifact']='360-No-Scope-2.0.4.jar'
        return record,y
    with ThreadPoolExecutor(max_workers=5)as pool:
        for c,y in pool.map(render,jobs):clips.append(c);audio[c['runtimePath']]=y
    selected_ids={c['rifleId'] for c in clips}
    for e in baseline['events']:
        if e['rifleId'] not in selected_ids or e['action'] not in ACTIONS:continue
        event=deepcopy(before_events[e['id']]);slug=e['rifleId'].removeprefix('Weapon_Crossbow_')
        if e['action'] in ('Fire','SpecialFire') and not e['local']:
            layer=deepcopy(event['Layers'][0]);layer['Files']=[p.replace('/'+e['action']+'_','/'+e['action']+'Tail_') for p in layer['Files']];layer['StartDelay']=TAIL_DELAY;layer['Volume']=0;layer['RandomSettings']={'MinPitch':-.10,'MaxPitch':.10,'MinVolume':-.25,'MaxVolume':0};event['Layers'].append(layer)
            tail_event=deepcopy(event);tail_event['Layers']=[deepcopy(layer)];tail_event['MaxInstance']=16;tail_id=e['id'].removesuffix('_World')+'_Tail_Owner';tail_path='Server/Audio/SoundEvents/RangerSnipers/'+tail_id+'.json';write(OUT/tail_path,tail_event);after_events[tail_id]=tail_event
            events.append({'id':tail_id,'rifleId':e['rifleId'],'action':e['action']+'Tail','local':False,'ownerOnly':True,'path':tail_path,'sha256':digest((OUT/tail_path).read_bytes()),'files':layer['Files']})
            bindings.append({'itemId':e['rifleId'],'action':e['action'],'ownerTailEventId':tail_id,'worldTailDelaySeconds':TAIL_DELAY})
        write(OUT/e['path'],event);after_events[e['id']]=event
        events.append({k:e[k] for k in ('id','rifleId','action','local','path')}|{'sha256':digest((OUT/e['path']).read_bytes()),'files':[f for l in event['Layers']for f in l['Files']],'layerCount':len(event['Layers'])})
    # First useful source preview is emitted before the full audit completes.
    for slug in ('Luminia_Dawnpiercer','Wildwood_Surveyor','Deepworks_Railspike'):
        fireid='RS_Audio_'+slug+'_Fire_Local';worldid=fireid.replace('_Local','_World')
        if fireid not in after_events:continue
        for label,bank,ev in [('Before',before_audio,before_events),('After',before_audio|audio,before_events|after_events)]:
            save_wave(OUT/'previews'/f'{slug}_Fire_{label}.wav',full_event_mix(ev[fireid],bank))
        save_wave(OUT/'previews'/f'{slug}_Fire_World_After.wav',full_event_mix(after_events[worldid],audio))
        tier=tiers['Weapon_Crossbow_'+slug];duration=tier['reload']['durationSeconds'];variant='double' if tier['reload']['capacity']==2 else 'single';timeline=tier['audio']['reloadTimelines'][variant]+[{'phase':1,'event':'Ready'}]
        for label,bank,ev in [('Before',before_audio,before_events),('After',before_audio|audio,before_events|after_events)]:
            result=np.zeros(round((duration+.75)*RATE))
            for cue in timeline:
                eid=tier['audio']['events'][cue['event']]['Local'];place(result,full_event_mix(ev[eid],bank),cue['phase']*duration)
            save_wave(OUT/'previews'/f'{slug}_Reload_{label}.wav',result)
    print('CINEMATIC_CORE_PREVIEWS_READY',flush=True)
    # Validate every possible independent direct/decay variant pair, not merely
    # the convenient matching variant used by the source preview.
    mix_peaks=[];pair_checks=0
    for eid,event in after_events.items():
        if not eid.endswith('_World')or '_Fire_'not in eid and '_SpecialFire_'not in eid:continue
        for a in range(3):
            for b in range(3):
                direct=audio['Common/'+event['Layers'][0]['Files'][a]];tail=audio['Common/'+event['Layers'][1]['Files'][b]];mix=np.zeros(max(len(direct),round(TAIL_DELAY*RATE)+len(tail)));place(mix,direct,0);place(mix,tail,TAIL_DELAY);mix*=amplitude(event.get('Volume',0));mix_peaks.append(db(oversampled_peak(mix)));pair_checks+=1
    reload_checks=[]
    # Includes unchanged charging/empty assets used between the remastered cues.
    full_audio=before_audio|audio;full_events=before_events|after_events
    for tier in tiers.values():
        if tier['id']not in selected_ids:continue
        for variant,timeline in tier['audio']['reloadTimelines'].items():
            result=np.zeros(round((tier['reload']['durationSeconds']+1)*RATE))
            for cue in timeline+[{'phase':1,'event':'Ready'}]:place(result,full_event_mix(full_events[tier['audio']['events'][cue['event']]['Local']],full_audio),cue['phase']*tier['reload']['durationSeconds'])
            reload_checks.append({'itemId':tier['id'],'variant':variant,'truePeak4xDbFS':db(oversampled_peak(result))})
    arsenal=json.loads((PROJECT/'content/arsenal-spec.json').read_text())
    if not args.preview_only:
        for tier in arsenal['tiers']:
            timelines=deepcopy(tier['audio']['reloadTimelines'])
            if tier['reload']['style']=='shell-tube':
                timelines={f'shells{count}':[{'phase':.18,'event':'ReloadOpen'}]+[{'phase':round(.25+.45*(i+1)/count,6),'event':'ReloadInsert'}for i in range(count)]+[{'phase':.89,'event':'ReloadClose'}]for count in range(1,tier['reload']['capacity']+1)}
            for variant,timeline in timelines.items():
                result=np.zeros(round((tier['reload']['durationSeconds']+1)*RATE))
                for cue in timeline+[{'phase':1,'event':'Ready'}]:place(result,full_event_mix(full_events[tier['audio']['events'][cue['event']]['Local']],full_audio),cue['phase']*tier['reload']['durationSeconds'])
                reload_checks.append({'itemId':tier['id'],'variant':variant,'truePeak4xDbFS':db(oversampled_peak(result))})
    maximum=max(c['after']['truePeak4xDbFS']for c in clips)
    validation={'status':'PASS','passed':True,'failures':[],'clipCount':len(clips),'eventCount':len(events),'ownerTailBindingCount':len(bindings),'sourceHashChecks':len(src.used),'decodedMaximum4xTruePeakDbFS':maximum,'worldIndependentVariantPairs':pair_checks,'worldMixMaximum4xTruePeakDbFS':max(mix_peaks),'reloadCycles':reload_checks,'reloadCycleCount':len(reload_checks),'reloadMixMaximum4xTruePeakDbFS':max(r['truePeak4xDbFS']for r in reload_checks),'cueSchedulesChanged':False,'sourceClippingAvoidance':'direct firearm selections use verified unclipped shot/channel windows; mid-distance initiating bang removed at+120ms','humanListeningVerified':False,'checks':[]}
    assert len(clips)==(16 if args.preview_only else 102)
    assert len(bindings)==(2 if args.preview_only else 11)
    assert maximum<-1.5 and max(mix_peaks)<-1.0
    assert all(x['truePeak4xDbFS']<-1 for x in reload_checks)
    assert all(np.isfinite(x).all()for x in audio.values())
    write(OUT/'catalog.json',{'version':'2.0.5','sampleRate':RATE,'channels':1,'clips':clips,'events':events,'ownerTailBindings':bindings,'sourceRecordings':list(src.used.values()),'humanListeningVerified':False,'cueSchedulesChanged':False,'runtimeFileSetChanged':True,'design':'authentic CC0 physical foundation, original designed mechanical/energy accents, separately spatialized actual outdoor field returns','previousArtifactSHA256':digest(BEFORE.read_bytes())})
    write(OUT/'sourcecatalog.json',{'sources':list(src.used.values()),'licenseSummary':{'CC0':'physical reports, all primary handling, and all field decays','Bluezone':'free-game-use original designed accents; not CC0/open source; preserve existing Designed by Bluezone Corporation credits'},'SunoSourcesUsed':False})
    write(OUT/'validation.json',validation)
    print(json.dumps({k:v for k,v in validation.items()if k!='reloadCycles'},indent=2),flush=True)

if __name__=='__main__':main()
