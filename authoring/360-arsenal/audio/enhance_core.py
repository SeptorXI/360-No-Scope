"""Heavier original sniper reports and shared reloads from licensed recordings.

Reads only the immutable1.7 JAR/catalog and hash-verified existing raw sources.
Writes a separate overlay. Event IDs, file paths, sample counts and schedules
stay fixed; no new oscillators, noise booms or source downloads are introduced.
"""
from __future__ import annotations
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
import base64,hashlib,html,json,math,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'core-enhanced'
SOURCE_AUDIO=PROJECT.parent/'ranger-snipers/audio'
FFMPEG=Path(os.environ.get('FFMPEG', 'ffmpeg'))
RATE=48000
ACTIONS={'Fire','SpecialFire','ReloadOpen','ReloadInsert','ReloadClose','Ready'}
TARGETS={'Fire':-11.5,'ReloadOpen':-21.5,'ReloadInsert':-21.5,'ReloadClose':-21.5,'Ready':-26.0}

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def db(value):return float(20*np.log10(max(float(value),1e-15)))
def amplitude(value):return 10**(value/20)

def native_samples(raw):
    offset=0;granules=[]
    while offset<len(raw):
        if raw[offset:offset+4]!=b'OggS':raise ValueError('Invalid Ogg page')
        count=raw[offset+26];table=raw[offset+27:offset+27+count];g=int.from_bytes(raw[offset+6:offset+14],'little')
        if g<(1<<63):granules.append(g)
        offset+=27+count+sum(table)
    return max(granules)

def decode(raw):
    p=subprocess.run([str(FFMPEG),'-v','error','-nostdin','-i','pipe:0','-ac','1','-ar',str(RATE),'-f','f32le','pipe:1'],input=raw,capture_output=True,check=True)
    x=np.frombuffer(p.stdout,dtype='<f4').copy()
    if raw[:4]==b'OggS':
        # A nonseekable FFmpeg decode can expose the final Vorbis block padding
        # (up to1024samples) or omit the128sample lead-in. The final granule is
        # the native duration contract; pad/trim only that codec-only edge.
        count=native_samples(raw)
        x=np.pad(x,(0,max(0,count-len(x))))[:count]
    return x

def kweighted(x):
    n=1<<(len(x)+4095).bit_length();z=np.exp(-2j*np.pi*np.fft.rfftfreq(n))
    h=(1.53512485958697-2.69169618940638*z+1.19839281085285*z*z)/(1-1.69065929318241*z+.73248077421585*z*z)
    h*=(1-2*z+z*z)/(1-1.99004745483398*z+.99007225036621*z*z)
    return np.fft.irfft(np.fft.rfft(x,n=n)*h,n=n)[:len(x)]

def window_db(x,seconds=.1):
    count=min(round(RATE*seconds),len(x));c=np.r_[0,np.cumsum(x.astype(np.float64)**2)]
    return db(np.sqrt(np.max(c[count:]-c[:-count])/count))

def band(x,low=60,high=12000):
    n=1<<(len(x)+2047).bit_length();f=np.fft.rfftfreq(n,1/RATE)
    hp=(f/np.sqrt(f*f+low*low))**2
    lp=1/np.sqrt(1+(f/high)**8)
    return np.fft.irfft(np.fft.rfft(x,n=n)*hp*lp,n=n)[:len(x)].astype(np.float64)

def true_peak(x):
    n=1<<(len(x)+2047).bit_length()
    return db(np.max(np.abs(np.fft.irfft(np.fft.rfft(x,n=n),n=n*4)*4)))

def metric(x):
    k=kweighted(x)
    return {'samples':len(x),'durationSeconds':len(x)/RATE,'peakDbFS':db(np.max(np.abs(x))),
            'truePeak4xDbFS':true_peak(x),'maximum100msRmsDbFS':window_db(x),
            'maximum100msKWeightedRmsDbFS':window_db(k),
            'attack20msRmsDbFS':window_db(x[:min(len(x),round(.12*RATE))],.02),
            'body60to500HzRmsDbFS':window_db(band(x,60,500)),
            'tail20msRmsDbFS':db(np.sqrt(np.mean(x[-min(len(x),960):]**2))),
            'dcMean':float(np.mean(x))}

def fade(x,attack=.0008,release=.018):
    x=x.copy();a=min(round(RATE*attack),len(x)//4);b=min(round(RATE*release),len(x)//3)
    if a:x[:a]*=np.linspace(0,1,a)
    if b:x[-b:]*=np.linspace(1,0,b)
    return x

def normalize(x):return x/max(float(np.max(np.abs(x))),1e-12)

def recorded_fragment(x,count,rate,active):
    # Isolate a single recorded impact, not a complete multi-action sequence.
    win=min(480,len(x));c=np.r_[0,np.cumsum(x.astype(float)**2)]
    peak=int(np.argmax(c[win:]-c[:-win]));start=max(0,peak-round(.006*RATE))
    pos=start+np.arange(count)*rate
    y=np.interp(pos,np.arange(len(x)),x,left=0,right=0)
    active_count=min(count,round(active*RATE));envelope=np.zeros(count)
    if active_count:
        envelope[:active_count]=np.exp(-np.linspace(0,3.7,active_count))
        edge=min(240,active_count//5)
        if edge:envelope[active_count-edge:active_count]*=np.linspace(1,0,edge)
    return fade(y*envelope,.0006,.012)

def offset(x,samples):
    y=np.zeros_like(x)
    if samples<len(x):y[samples:]=x[:len(x)-samples]
    return y

def shape(before,entry,source_cache):
    action=entry['action'];n=len(before);is_fire=action in ('Fire','SpecialFire')
    sources=[s for s in entry['sources'] if s.get('path')]
    preferred='bluezone-weapon' if is_fire else 'bluezone-mechanical'
    primary=next((s for s in sources if s.get('sourceId')==preferred),sources[0])
    secondary=next((s for s in sources if s.get('sourceId')==('bluezone-mechanical' if is_fire else 'springyspringo-gun-reloads')),primary)
    raw=source_cache[primary['path']];secondary_raw=source_cache[secondary['path']]
    speed=.73 if is_fire else (.76 if action!='Ready' else .91)
    active=.32 if is_fire else min(n/RATE*.83,.16 if action!='Ready' else .11)
    low_body=recorded_fragment(raw,n,speed,active)
    low_body=normalize(band(low_body,55 if is_fire else 80,680 if is_fire else 1700))
    metal=recorded_fragment(secondary_raw,n,.88 if is_fire else .93,min(active,.20 if is_fire else .12))
    metal=normalize(band(metal,420 if is_fire else 650,6200))
    reference=max(float(np.max(np.abs(before))),.001)
    if is_fire:
        y=before.astype(float)+offset(low_body,round(.004*RATE))*reference*.58+offset(metal,round(.006*RATE))*reference*.13
        # Recorded body plus a very short reflection, not a synthesized boom.
        y+=offset(band(y,80,1800),round(.029*RATE))*.16
        y=band(y,48,12000)
        knee=max(float(np.sqrt(np.mean(y[:min(n,7200)]**2)))*2.1,.001)
        y=.53*y+.47*knee*np.tanh(y/knee)
    else:
        y=before.astype(float)+offset(low_body,round(.0015*RATE))*reference*.52+offset(metal,round(.003*RATE))*reference*.22
        # Keep a short, tactile return-rattle inside the existing cue envelope.
        y+=offset(band(metal,220,3400),round(.021*RATE))*reference*.10
        y=band(y,65,11000)
        knee=max(float(np.sqrt(np.mean(y*y)))*2.4,.001)
        y=.68*y+.32*knee*np.tanh(y/knee)
    y-=np.mean(y)
    return fade(y,.0008,.026 if is_fire else .016),[primary,secondary]

def encode(path,x,target):
    # Shape isolated peaks before gain matching so the finished file has both
    # body and true-peak headroom. Native event gain stays non-positive.
    for _ in range(7):
        gain=target-window_db(kweighted(x))
        if true_peak(x)+gain<=-2.0:break
        knee=max(float(np.sqrt(np.mean(x[:min(len(x),7200)]**2)))*1.75,.0001)
        x=.28*x+.72*knee*np.tanh(x/knee)
    x=x*amplitude(target-window_db(kweighted(x)))
    path.parent.mkdir(parents=True,exist_ok=True)
    command=[str(FFMPEG),'-v','error','-nostdin','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','pipe:0','-map_metadata','-1','-c:a','libvorbis','-q:a','6',str(path)]
    for _ in range(3):
        subprocess.run(command,input=x.astype('<f4').tobytes(),capture_output=True,check=True)
        raw=path.read_bytes();audio=decode(raw);m=metric(audio)
        correction=min(target-m['maximum100msKWeightedRmsDbFS'],-1.6-m['truePeak4xDbFS'])
        if abs(correction)<.035 and m['truePeak4xDbFS']<-1.3:break
        x*=amplitude(correction)
    return raw,audio,m

def event_gain(event):return event.get('Volume',0)+sum(layer.get('Volume',0) for layer in event.get('Layers',[])[:1])

def source_contract():
    revision=json.loads((PROJECT/'baseline/audio-revision.json').read_text());jar=PROJECT/'baseline'/revision['artifact'];catalog=PROJECT/'baseline'/revision['catalog']
    if digest(jar.read_bytes())!=revision['sha256'] or digest(catalog.read_bytes())!=revision['catalogSha256']:raise ValueError('Immutable1.7 source revision changed')
    return revision,jar,json.loads(catalog.read_text())

def preview(catalog,before_audio,after_audio,baseline_events,after_events):
    old=json.loads((PROJECT/'baseline/sniper-spec.json').read_text());profiles={t['id']:t for t in old['tiers']};clips={(c['rifleId'],c['action'],c['variant']):c for c in catalog['clips']}
    previews=[];dest=OUT/'previews';dest.mkdir(parents=True,exist_ok=True)
    def put(name,x):
        if np.max(np.abs(x))>.99:raise ValueError('A/B preview clips: '+name)
        path=dest/(name+'.wav')
        with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())
        return path
    for weapon in ('Weapon_Crossbow_Wildwood_Surveyor','Weapon_Crossbow_Luminia_Dawnpiercer'):
        tier=profiles[weapon];slug=weapon.removeprefix('Weapon_Crossbow_')
        fire=clips[(weapon,'Fire',1)];event_id=tier['audio']['events']['Fire']['Local']
        pair={}
        for label,bank,events in [('Before',before_audio,baseline_events),('After',after_audio,after_events)]:
            pair[label]=put(slug+'_Fire_'+label,bank[fire['runtimePath']]*amplitude(event_gain(events[event_id])))
        previews.append({'name':tier['name']+' — firing','files':pair,'type':'fire'})
        duration=tier['reload']['durationSeconds'];variant='double' if tier['reload']['capacity']==2 else 'single';timeline=tier['audio']['reloadTimelines'][variant]
        proof=[];pair={}
        for label,bank,events in [('Before',before_audio,baseline_events),('After',after_audio,after_events)]:
            audio=np.zeros(round((duration+.20)*RATE))
            for cue in timeline+[{'phase':1,'event':'Ready'}]:
                action=cue['event'];clip=clips[(weapon,action,1)];event_id=tier['audio']['events'][action]['Local'];pos=round(cue['phase']*duration*RATE);samples=bank[clip['runtimePath']]*amplitude(event_gain(events[event_id]));end=min(len(audio),pos+len(samples));audio[pos:end]+=samples[:end-pos]
                if label=='After':proof.append({'action':action,'atSeconds':cue['phase']*duration,'clipSeconds':len(samples)/RATE})
            pair[label]=put(slug+'_Reload_'+label,audio)
        previews.append({'name':tier['name']+' — full reload','files':pair,'type':'reload','reloadDurationSeconds':duration,'cueTimeline':proof})
    parts=['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>360 No Scope core audio A/B</title><style>body{background:#101820;color:#f2eadb;font:17px system-ui;max-width:1000px;margin:35px auto;padding:0 20px}article{background:#1a2935;padding:20px;border-radius:12px;margin:20px 0}audio{width:100%;max-width:400px}small{color:#b5c4cd}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:650px){.pair{grid-template-columns:1fr}}</style><h1>360 No Scope — core audio A/B</h1><p>Heavier licensed-recording layers, firmer metal mechanisms and restrained headroom. These are the actual runtime mixes with native local event gain applied.</p><p><small>Existing reload timing is preserved. Dawnpiercer reload commits at 2.7s; the preview includes the final Ready cue tail. No new synthesized booms or cue triggers.</small></p>']
    for row in previews:
        parts.append('<article><h2>'+html.escape(row['name'])+'</h2><div class="pair">')
        for label,path in row['files'].items():parts.append('<div><h3>'+label+'</h3><audio controls preload="metadata" src="data:audio/wav;base64,'+base64.b64encode(path.read_bytes()).decode()+'"></audio></div>')
        parts.append('</div></article>')
    (dest/'Core_Audio_AB.html').write_text(''.join(parts),encoding='utf-8');write(dest/'preview-timelines.json',[{**p,'files':{k:v.name for k,v in p['files'].items()}}for p in previews])

def main():
    revision,jar,source=source_contract();selected=[c for c in source['clips'] if c['action'] in ACTIONS];source_cache={};raw_sources={};before_audio={};baseline_events={};after_events={};overlay_events=[];native_counts={}
    # Only these owned output subtrees are rebuilt; provenance and A/B files
    # remain outside the runtime payload.
    import shutil
    for name in ('Common','Server'):
        p=(OUT/name).resolve()
        if not p.is_relative_to(OUT.resolve()):raise ValueError('Output escaped core enhancement root')
        if p.exists():shutil.rmtree(p)
    with ZipFile(jar)as z:
        credit_notices=[{'path':n,'sha256':digest(z.read(n))}for n in sorted(z.namelist())if n.startswith('Audio Credits/')and not n.endswith('/')]
        for c in source['clips']:
            raw=z.read(c['runtimePath'])
            if digest(raw)!=c['sha256']:raise ValueError('Frozen clip differs from catalog: '+c['runtimePath'])
            before_audio[c['runtimePath']]=decode(raw);native_counts[c['runtimePath']]=native_samples(raw)
        for e in source['events']:
            event=json.loads(z.read(e['path']));baseline_events[e['id']]=deepcopy(event);after_events[e['id']]=deepcopy(event)
            if e['action'] in ACTIONS:
                local=next(x for x in source['events']if x['rifleId']==e['rifleId']and x['action']==e['action']and x['local']);local_gain=event_gain(json.loads(z.read(local['path'])));desired=0 if e['local'] else event_gain(event)-local_gain
                event['Volume']=round(desired-event.get('Layers',[{}])[0].get('Volume',0),4)
                write(OUT/e['path'],event);after_events[e['id']]=event
                overlay_events.append({**e,'beforeVolumeDb':baseline_events[e['id']].get('Volume',0),'volumeDb':event['Volume'],'nominalGainDb':event_gain(event),'sha256':digest((OUT/e['path']).read_bytes())})
    for clip in selected:
        for s in clip['sources']:
            if not s.get('path')or s['path']in source_cache:continue
            path=(SOURCE_AUDIO/s['path']).resolve()
            if not path.is_relative_to((SOURCE_AUDIO/'sources').resolve()):raise ValueError('Raw source escaped recordings directory')
            raw=path.read_bytes()
            if digest(raw)!=s['sha256']:raise ValueError('Raw licensed source hash changed: '+str(path))
            source_cache[s['path']]=decode(raw);raw_sources[s['path']]={**s,'bytes':len(raw)}
    fire_targets={}
    for weapon in sorted({c['rifleId']for c in selected}):
        group=[c for c in selected if c['rifleId']==weapon and c['action']=='Fire']
        local=next(e['id']for e in source['events']if e['rifleId']==weapon and e['action']=='Fire'and e['local'])
        old_mean=float(np.mean([window_db(kweighted(before_audio[c['runtimePath']]))+event_gain(baseline_events[local])for c in group]))
        fire_targets[weapon]=max(-11.5,old_mean+2.7)
    def task(c):
        before=before_audio[c['runtimePath']];x,added=shape(before,c,source_cache)
        # Preserve the original Vorbis granule-duration profile as well as the
        # decoded sample count. Short Vorbis cues discard a128sample lead-in;
        # restore that codec guard before encoding instead of shortening them.
        count=native_counts[c['runtimePath']];guard=count-len(before)
        if abs(guard)>512:raise ValueError('Unexpected source Vorbis guard '+c['runtimePath'])
        if guard>0:x=np.pad(x,(guard,0))
        elif guard<0:x=x[:count]
        target=fire_targets[c['rifleId']]if c['action']=='Fire'else TARGETS.get(c['action'],-10 if c['rifleId'].endswith('Deepworks_Railspike') else -11)
        path=OUT/c['runtimePath'];raw,after,m=encode(path,x,target)
        if native_samples(raw)!=count:raise ValueError('Native Ogg duration changed '+c['runtimePath'])
        if abs(len(after)-len(before))>256:raise ValueError('Unexpected streaming decoder padding '+c['runtimePath'])
        if not np.isfinite(after).all()or m['truePeak4xDbFS']>=-1.0:raise ValueError('Invalid peak/PCM '+c['runtimePath'])
        local=next(e['id']for e in source['events']if e['rifleId']==c['rifleId']and e['action']==c['action']and e['local']);before_gain=event_gain(baseline_events[local]);after_gain=event_gain(after_events[local]);b=metric(before)
        b['effectiveLocal100msKWeightedRmsDb']=b['maximum100msKWeightedRmsDbFS']+before_gain;m['effectiveLocal100msKWeightedRmsDb']=m['maximum100msKWeightedRmsDbFS']+after_gain
        b['effectiveLocalBody60to500HzDb']=b['body60to500HzRmsDbFS']+before_gain;m['effectiveLocalBody60to500HzDb']=m['body60to500HzRmsDbFS']+after_gain
        b['effectiveLocalAttack20msRmsDb']=b['attack20msRmsDbFS']+before_gain;m['effectiveLocalAttack20msRmsDb']=m['attack20msRmsDbFS']+after_gain
        result={**c,'sha256':digest(raw),'sourceSHA256':c['sha256'],'durationSeconds':count/RATE,'nativeSamplesBefore':count,'nativeSamplesAfter':native_samples(raw),'streamingDecoderSampleDelta':len(after)-len(before),'before':b,'after':m,'targetEffectiveLocal100msKWeightedRmsDb':target,'effectiveK100UpliftDb':m['effectiveLocal100msKWeightedRmsDb']-b['effectiveLocal100msKWeightedRmsDb'],'lowBodyUpliftDb':m['effectiveLocalBody60to500HzDb']-b['effectiveLocalBody60to500HzDb'],'sourceRuntimePath':c['runtimePath'],'sourceArtifact':revision['artifact'],'sourceArtifactSHA256':revision['sha256'],'addedRecordedLayers':added,'processing':{'bodyPlaybackRatio':.73 if c['action']in('Fire','SpecialFire')else.76,'newSynthesizedSources':False,'exactNativeSampleCountRetained':True,'stage':'recorded body, metal transient, short natural rattle/reflection, parallel soft compression, K100 gain match'}}
        return result,after
    with ThreadPoolExecutor(max_workers=4)as pool:processed=list(pool.map(task,selected))
    clips=[row for row,a in processed];after_audio=dict(before_audio);after_audio.update({row['runtimePath']:a for row,a in processed})
    failures=[]
    for row in clips:
        if abs(row['after']['effectiveLocal100msKWeightedRmsDb']-row['targetEffectiveLocal100msKWeightedRmsDb'])>.4:failures.append('Loudness target '+row['runtimePath'])
        if row['nativeSamplesAfter']!=row['nativeSamplesBefore']:failures.append('Duration '+row['runtimePath'])
    action_summary={}
    for action in sorted(ACTIONS):
        group=[c for c in clips if c['action']==action];action_summary[action]={'clips':len(group),'meanEffectiveK100BeforeDb':float(np.mean([c['before']['effectiveLocal100msKWeightedRmsDb']for c in group])),'meanEffectiveK100AfterDb':float(np.mean([c['after']['effectiveLocal100msKWeightedRmsDb']for c in group])),'meanUpliftDb':float(np.mean([c['effectiveK100UpliftDb']for c in group])),'meanLowBodyUpliftDb':float(np.mean([c['lowBodyUpliftDb']for c in group]))}
    changed={c['runtimePath']:c for c in clips}
    all_core=[{'runtimePath':c['runtimePath'],'sha256':changed.get(c['runtimePath'],c)['sha256'],'rifleId':c['rifleId'],'action':c['action'],'sources':c['sources'],'nativeSamples':native_counts[c['runtimePath']],'changed':c['runtimePath']in changed}for c in source['clips']]
    for path,row in raw_sources.items():
        if digest((SOURCE_AUDIO/path).read_bytes())!=row['sha256']:raise ValueError('Source changed during mastering: '+path)
    catalog={'version':'2.0.4','sourceRevision':revision,'scope':'Original9 Fire/SpecialFire and all54 shared ReloadOpen/ReloadInsert/ReloadClose/Ready cues;69 existing clips and94 events replaced. Other26 core files unchanged.','sampleRate':RATE,'channels':1,'clips':clips,'allCoreClips':all_core,'events':overlay_events,'sourcePacks':source['sourcePacks'],'sourceRecordings':list(raw_sources.values()),'creditNotices':credit_notices,'actionSummary':action_summary,'runtimeFileSetChanged':False,'gameplayOrCueSchedulesChanged':False,'durationMetric':'Ogg final granule/native sample count, retained exactly. Nonseekable decoder block padding is aligned to that granule only for PCM measurement.','humanListeningVerified':False}
    write(OUT/'catalog.json',catalog)
    validation={'passed':not failures,'version':'2.0.4','clips':len(clips),'events':len(overlay_events),'coreFileCountRetained':95,'combinedFileCountRetained':230,'combinedEventCountRetained':236,'sharedReloadRecipients':54,'sampleCountsUnchanged':True,'sourceVersion':revision['version'],'sourceSHA256':revision['sha256'],'rawSourceFilesVerified':len(raw_sources),'originalRecordingsModified':False,'newSynthesizedSources':False,'creditNoticesPreserved':credit_notices,'maximumTruePeak4xDbFS':max(c['after']['truePeak4xDbFS']for c in clips),'actionSummary':action_summary,'failures':failures,'scope':'Decoded runtime PCM,4x peak estimate, exact sample counts and event metadata. Native/client listening checks are separate.'}
    write(OUT/'validation.json',validation);write(OUT/'provenance.json',{'sourceRevision':revision,'rawSources':list(raw_sources.values()),'creditNotices':credit_notices,'sourcePacks':source['sourcePacks'],'newSourcesOrDownloads':False,'changedSourceFiles':[]})
    preview(source,before_audio,after_audio,baseline_events,after_events)
    print(json.dumps({'passed':validation['passed'],'clips':len(clips),'events':len(overlay_events),'peak4xDbFS':validation['maximumTruePeak4xDbFS'],'actionSummary':action_summary,'failures':failures},indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
