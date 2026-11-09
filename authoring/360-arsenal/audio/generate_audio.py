import os
"""Cadence-matched derivatives of a hash-pinned immutable audio revision.

Gameplay remains based on 1.6.0. baseline/audio-revision.json independently pins
the selected sound artifact, with an optional equally frozen source catalog.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave
from zipfile import ZipFile
import numpy as np
from impact_processing import strengthen, master, oversampled_peak

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
BASELINE = PROJECT / 'baseline'
FFMPEG=Path(os.environ.get('FFMPEG', 'ffmpeg'))
RATE = 48000
FAMILY = {
    'handgun': {'duration': .42, 'pitch': 1.09, 'targetEffectiveK100Db': -15.5, 'volume': -1, 'distance': 48},
    'smg': {'duration': .16, 'pitch': 1.14, 'targetEffectiveK100Db': -19.5, 'volume': -2.5, 'distance': 48},
    'semiauto': {'duration': .62, 'pitch': 1.02, 'targetEffectiveK100Db': -14.5, 'volume': -.5, 'distance': 64},
    'automatic': {'duration': .21, 'pitch': 1.04, 'targetEffectiveK100Db': -17.5, 'volume': -1.5, 'distance': 64},
    'shotgun': {'duration': .8, 'pitch': .86, 'targetEffectiveK100Db': -12.5, 'volume': 0, 'distance': 72},
}
ENCODE_HEADROOM_DB = -2.8
DECODED_PEAK_LIMIT_DB = -1.0

def db(value):
    return float(20*np.log10(max(float(value),1e-15)))

def window_rms_db(audio):
    """Maximum sliding100ms RMS; suitable for these160ms-or-longer reports."""
    window=min(round(RATE*.1),len(audio))
    cumulative=np.concatenate(([0.],np.cumsum(audio.astype(np.float64)**2)))
    maximum=np.max(cumulative[window:]-cumulative[:-window])/window
    return db(np.sqrt(max(0,maximum)))

def kweighted(audio):
    """48k BS.1770 K-weighting filters, evaluated as a zero-padded FFT filter.

    This supplies a100ms energy metric, not integrated LUFS. The4096sample
    trailing pad makes circular wrap smaller than the metric's reporting floor.
    """
    size=1 << (len(audio)+4096-1).bit_length()
    z=np.exp(-2j*np.pi*np.fft.rfftfreq(size))
    h=(1.53512485958697-2.69169618940638*z+1.19839281085285*z*z)/(1-1.69065929318241*z+.73248077421585*z*z)
    h*=(1-2*z+z*z)/(1-1.99004745483398*z+.99007225036621*z*z)
    return np.fft.irfft(np.fft.rfft(audio,n=size)*h,n=size)[:len(audio)]

def metric(audio):
    return {'peakDb':db(np.max(np.abs(audio))),
            'rmsDb':db(np.sqrt(np.mean(audio.astype(np.float64)**2))),
            'maximum100msRmsDb':window_rms_db(audio),
            'maximum100msKWeightedRmsDb':window_rms_db(kweighted(audio))}

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def decode(data):
    command=[str(FFMPEG),'-v','error','-nostdin','-i','pipe:0','-ac','1','-ar',str(RATE),'-f','f32le','pipe:1']
    return np.frombuffer(subprocess.run(command,input=data,capture_output=True,check=True).stdout,dtype='<f4').copy()

def snapshot_before():
    """Keep exact installed2.0.3 reports for reproducible decoded A/B evidence."""
    source=PROJECT/'release/360-No-Scope-2.0.3.jar'
    destination=ROOT/'remaster-before/2.0.3'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    manifest=destination/'manifest.json'
    if manifest.exists():
        prior=json.loads(manifest.read_text(encoding='utf-8'))
        if prior['artifactSHA256']!=digest:raise ValueError('Frozen pre-remaster2.0.3 audio no longer matches its artifact')
        return destination,prior
    rows=[]
    with ZipFile(source) as archive:
        for name in sorted(archive.namelist()):
            if not (name.startswith('Common/Sounds/Arsenal/')and name.endswith('.ogg')or name.startswith('Server/Audio/SoundEvents/Arsenal/')and name.endswith('.json')):continue
            raw=archive.read(name);path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            rows.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
    prior={'version':'2.0.3','artifact':source.name,'artifactSHA256':digest,'files':rows}
    write(manifest,prior)
    return destination,prior

def audio_revision():
    manifest=BASELINE/'audio-revision.json'
    revision=json.loads(manifest.read_text(encoding='utf-8-sig')) if manifest.exists() else {
        'artifact':'360-No-Scope-1.6.0.jar','version':'1.6.0',
        'sha256':'9459fda21ef57c8e4bb1ccc1410a13764f797d8be5f60f88abaa89c646fadd52'}
    artifact=(BASELINE/revision['artifact']).resolve()
    if not artifact.is_relative_to(BASELINE.resolve()):
        raise ValueError('Audio artifact escapes immutable baseline directory')
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest!=revision['sha256'].lower():
        raise ValueError('Selected audio revision SHA-256 mismatch')
    return artifact,revision,digest

def provenance_for(archive,revision,digest):
    destination=ROOT/'source-provenance.json'
    if destination.exists():
        cached=json.loads(destination.read_text(encoding='utf-8'))
        if cached.get('sourceSHA256')==digest:
            return cached
    source={}
    if revision.get('catalog'):
        catalog=(BASELINE/revision['catalog']).resolve()
        if not catalog.is_relative_to(BASELINE.resolve()):
            raise ValueError('Audio source catalog escapes immutable baseline directory')
        source=json.loads(catalog.read_text(encoding='utf-8-sig'))
    else:
        embedded=next((name for name in archive.namelist()
                       if Path(name).name.lower() in ('audio catalog.json','audio-catalog.json')),None)
        if embedded:
            source=json.loads(archive.read(embedded))
        elif revision['version']=='1.6.0':
            archived=PROJECT.parent/'ranger-snipers/snapshots/1.6.0/audio/catalog.json'
            if archived.exists():source=json.loads(archived.read_text(encoding='utf-8-sig'))
    metadata={c['runtimePath']:c for c in source.get('clips',[]) if c.get('action')=='Fire'}
    rows=[]
    for name in sorted(archive.namelist()):
        if not name.startswith('Common/Sounds/RangerSnipers/') or not Path(name).name.startswith('Fire_') or not name.endswith('.ogg'):
            continue
        raw=archive.read(name);actual=hashlib.sha256(raw).hexdigest();known=metadata.get(name)
        if known and known.get('sha256')!=actual:
            raise ValueError('Frozen source catalog does not match selected audio revision: '+name)
        rows.append(known if known else {'runtimePath':name,'sha256':actual,'action':'Fire','sources':[]})
    notices=[{'path':name,'sha256':hashlib.sha256(archive.read(name)).hexdigest()}
             for name in sorted(archive.namelist()) if name.startswith('Audio Credits/') and not name.endswith('/')]
    frozen={'sourceVersion':revision['version'],'sourceArtifact':revision['artifact'],'sourceSHA256':digest,
            'sourcePacks':source.get('sourcePacks',[]),'clips':rows,'creditNotices':notices,
            'attributionScope':'Verified per-output source manifest plus verbatim selected-artifact notices.' if metadata else 'Verbatim selected-artifact notices; the artifact supplies no per-layer source manifest.'}
    write(destination,frozen)
    return frozen

def write_comparison(spec,clips,before_root,before_manifest,event_gains):
    """Decoded measurements and listening files use native gain, never preview gain."""
    for entry in before_manifest['files']:
        if hashlib.sha256((before_root/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Pre-remaster snapshot changed: '+entry['path'])
    tiers={t['id']:t for t in spec['tiers']};rows=[];signals={}
    for clip in clips:
        tier=tiers[clip['weaponId']]
        event_id=tier['audio']['events']['Fire']['Local']
        old_event=json.loads((before_root/f'Server/Audio/SoundEvents/Arsenal/{event_id}.json').read_text(encoding='utf-8-sig'))
        old_gain=old_event.get('Volume',0)+old_event['Layers'][0].get('Volume',0)
        old_audio=decode((before_root/clip['runtimePath']).read_bytes())
        new_audio=decode((ROOT/'Common'/clip['path']).read_bytes())
        old=metric(old_audio);old['fourTimesOversampledPeakDb']=db(oversampled_peak(old_audio))
        old['first20msRmsDb']=db(np.sqrt(np.mean(old_audio[:round(RATE*.02)].astype(np.float64)**2)))
        old['localEventGainDb']=old_gain
        old['effectiveLocal100msKWeightedRmsDb']=old['maximum100msKWeightedRmsDb']+old_gain
        rows.append({'weaponId':clip['weaponId'],'family':clip['family'],'variant':clip['variant'],
            'before':old,'after':{k:clip[k] for k in ('peakDb','fourTimesOversampledPeakDb','first20msRmsDb','localEventGainDb','maximum100msKWeightedRmsDb','effectiveLocal100msKWeightedRmsDb')},
            'effectiveLiftDb':clip['effectiveLocal100msKWeightedRmsDb']-old['effectiveLocal100msKWeightedRmsDb'],
            'attack20msLiftDb':clip['first20msRmsDb']+clip['localEventGainDb']-old['first20msRmsDb']-old_gain})
        if clip['variant']==1:signals[clip['weaponId']]=(old_audio*10**(old_gain/20),new_audio*10**(clip['localEventGainDb']/20))
    families={}
    for family in FAMILY:
        members=[r for r in rows if r['family']==family]
        families[family]={'clips':len(members),'meanEffectiveLiftDb':float(np.mean([r['effectiveLiftDb']for r in members])),
            'minimumEffectiveLiftDb':min(r['effectiveLiftDb']for r in members),'maximumEffectiveLiftDb':max(r['effectiveLiftDb']for r in members),
            'meanAttack20msLiftDb':float(np.mean([r['attack20msLiftDb']for r in members]))}
        if families[family]['minimumEffectiveLiftDb']<6:
            raise ValueError('Remaster did not deliver a material audible increase: '+family)
    preview=ROOT/'previews';preview.mkdir(parents=True,exist_ok=True)
    previews=[]
    def save(name,samples,details):
        if not np.isfinite(samples).all() or np.max(np.abs(samples))>=1:
            raise ValueError('Native-gain preview mix would clip: '+name)
        path=preview/name
        with wave.open(str(path),'wb')as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(RATE)
            out.writeframes(np.round(samples*32767).astype('<i2').tobytes())
        previews.append({'file':name,'sampleRate':RATE,'channels':1,'durationSeconds':len(samples)/RATE,
                         'peakDb':db(np.max(np.abs(samples))),'previewMasterGainDb':0,**details})
    gap=lambda seconds:np.zeros(round(seconds*RATE),dtype=np.float32)
    showcase=[]
    for family in FAMILY:
        tier=next(t for t in spec['tiers']if t['family']==family)
        old,new=signals[tier['id']]
        save(f'{family}-before-after.wav',np.concatenate([gap(.2),old,gap(.75),new,gap(.5)]),
             {'weaponId':tier['id'],'family':family,'order':['installed2.0.3','remastered'],'nativeEventGainApplied':True})
        showcase.extend([gap(.35),new,gap(.7)])
        if family in ('smg','automatic'):
            def burst(audio):
                result=np.zeros(round(4*RATE)+len(audio),dtype=np.float32)
                for start in np.arange(0,4,tier['cycleSeconds']):
                    at=round(start*RATE);result[at:at+len(audio)]+=audio
                return result
            previous,current=burst(old),burst(new)
            save(f'{family}-4s-burst-before-after.wav',np.concatenate([gap(.2),previous,gap(1),current,gap(.5)]),
                 {'weaponId':tier['id'],'family':family,'order':['installed2.0.3','remastered'],
                  'nativeEventGainApplied':True,'cycleSeconds':tier['cycleSeconds'],'firingWindowSeconds':4,
                  'remasteredBurstPeakDb':db(np.max(np.abs(current))),
                  'remasteredBurstFourTimesPeakDb':db(oversampled_peak(current))})
    save('Arsenal New Fire Showcase.wav',np.concatenate(showcase),{'families':list(FAMILY),'nativeEventGainApplied':True})
    core=ROOT/'core-enhanced'
    dawn_event=core/'Server/Audio/SoundEvents/RangerSnipers/RS_Audio_Luminia_Dawnpiercer_Fire_Local.json'
    dawn_file=core/'Common/Sounds/RangerSnipers/Luminia_Dawnpiercer/Fire_01.ogg'
    if dawn_event.exists() and dawn_file.exists():
        event=json.loads(dawn_event.read_text(encoding='utf-8-sig'))
        new_gain=event.get('Volume',0)+event['Layers'][0].get('Volume',0)
        new=decode(dawn_file.read_bytes())*10**(new_gain/20)
        with ZipFile(PROJECT/'release/360-No-Scope-2.0.3.jar')as archive:
            path=next(n for n in archive.namelist()if n.endswith('/RS_Audio_Luminia_Dawnpiercer_Fire_Local.json'))
            old_event=json.loads(archive.read(path));old_gain=old_event.get('Volume',0)+old_event['Layers'][0].get('Volume',0)
            old=decode(archive.read('Common/'+old_event['Layers'][0]['Files'][0]))*10**(old_gain/20)
        save('sniper-before-after.wav',np.concatenate([gap(.2),old,gap(.75),new,gap(.5)]),
             {'weaponId':'Weapon_Crossbow_Luminia_Dawnpiercer','family':'sniper','order':['installed2.0.3','remastered'],'nativeEventGainApplied':True})
        save('360 No Scope Six Family New Fire.wav',np.concatenate([gap(.2),new,gap(.7),*showcase]),
             {'families':['sniper',*FAMILY],'nativeEventGainApplied':True})
        sequence=[gap(.2),old,gap(.75),new,gap(.8)]
        for family in FAMILY:
            tier=next(t for t in spec['tiers']if t['family']==family);previous,current=signals[tier['id']]
            sequence.extend([previous,gap(.75),current,gap(.8)])
        save('360 No Scope Six Family Before After.wav',np.concatenate(sequence),
             {'families':['sniper',*FAMILY],'order':['installed2.0.3','remastered'],'nativeEventGainApplied':True})
    comparison={'version':'impact-remaster-v1','beforeArtifact':before_manifest['artifact'],'beforeSHA256':before_manifest['artifactSHA256'],
        'comparisonScope':'Decoded installed OGGs versus remastered OGGs at each native Local event/layer gain; no preview normalization or master gain.',
        'families':families,'clips':rows,'previews':previews,'passed':True,'all135ClipsChanged':True}
    write(ROOT/'remaster-comparison.json',comparison)
    write(preview/'preview-manifest.json',previews)
    cards=''.join(f'<section><h2>{p["file"]}</h2><audio controls preload="none" src="{p["file"]}"></audio><p>Native event gain; no preview boost.</p></section>'for p in previews)
    (preview/'Gunfire Before and After.html').write_text('<!doctype html><meta charset="utf-8"><title>360 No Scope gunfire remaster</title><style>body{font:16px system-ui;background:#101419;color:#eee;max-width:900px;margin:40px auto;padding:16px}section{padding:18px;border-bottom:1px solid #345}audio{width:100%}h2{font-size:18px}</style><h1>Gunfire remaster: before / after</h1><p>Each A/B plays the installed report first, then the remaster. Native event and layer gain is applied with no preview normalization.</p>'+cards,encoding='utf-8')

def main():
    before_root,before_manifest=snapshot_before()
    spec=json.loads((PROJECT/'content/arsenal-spec.json').read_text(encoding='utf-8'))
    old=json.loads((PROJECT/'baseline/sniper-spec.json').read_text(encoding='utf-8'))
    originals={t['id']:t for t in old['tiers']}
    artifact,revision,digest=audio_revision()
    # These two generated trees belong exclusively to this authoring script.
    # Resolve and constrain both absolute targets before deleting any output;
    # scripts, credits, immutable inputs and provenance are outside the list.
    clean_targets=[(ROOT/relative).resolve() for relative in ('Common','generated/Server')]
    if any(not target.is_relative_to(ROOT.resolve()) or target==ROOT.resolve() for target in clean_targets):
        raise ValueError('Refusing unexpected generated audio cleanup target')
    for target in clean_targets:
        if target.exists():shutil.rmtree(target)
    provenance={}
    tasks=[];events=[];event_gains={}
    with ZipFile(artifact) as archive:
        frozen=provenance_for(archive,revision,digest)
        clip_metadata={c['runtimePath']:c for c in frozen.get('clips',[])}
        for name in archive.namelist():
            if name.startswith('Audio Credits/') and not name.endswith('/'):
                dest=ROOT/'credits'/Path(name).name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(archive.read(name))
        cache={}
        for tier in spec['tiers']:
            source=originals[tier['sourceThemeWeapon']]
            original_pair=source['audio']['events']['Fire'];paths=[]
            for mode,event_id in tier['audio']['events']['Fire'].items():
                baseline_id=original_pair[mode]
                event_path=next(x for x in archive.namelist() if x.endswith('/'+baseline_id+'.json'))
                event=json.loads(archive.read(event_path))
                slug=tier['id'].removeprefix('Weapon_Crossbow_')
                output_paths=[f'Sounds/Arsenal/{slug}/Fire_{i:02}.ogg' for i in range(1,4)]
                event['Layers'][0]['Files']=output_paths
                tuning=FAMILY[tier['family']]
                event['Volume']=round(event['Volume']+tuning['volume'],2)
                event['MaxDistance']=tuning['distance']
                event['MaxInstance']=32
                event['PreventSoundInterruption']=False
                event['Layers'][0]['RandomSettings']={'MinPitch':-.12,'MaxPitch':.12,'MinVolume':-.25,'MaxVolume':0}
                event_gains.setdefault(tier['id'],{})[mode]=event['Volume']+event['Layers'][0].get('Volume',0)
                relative=f'Server/Audio/SoundEvents/Arsenal/{event_id}.json'
                write(ROOT/'generated'/relative,event)
                events.append({'id':event_id,'weaponId':tier['id'],'mode':mode,'path':relative,'sourceEventId':baseline_id,
                               'nominalGainDb':event_gains[tier['id']][mode]})
                if mode=='Local': paths=json.loads(archive.read(event_path))['Layers'][0]['Files']
            for index,path in enumerate(paths,1):
                full='Common/'+path
                if full not in cache:
                    raw=archive.read(full);cache[full]=decode(raw)
                    metadata=clip_metadata.get(full,{})
                    if metadata and metadata.get('sha256')!=hashlib.sha256(raw).hexdigest():
                        raise ValueError('Archived source provenance does not match immutable JAR: '+full)
                    provenance[full]={'sha256':hashlib.sha256(raw).hexdigest(),'sources':clip_metadata.get(full,{}).get('sources',[])}
                tasks.append((tier,index,cache[full],full))
    def prepare(task):
        tier,index,source,source_path=task;tuning=FAMILY[tier['family']]
        duration=min(tuning['duration'],tier['cycleSeconds']*.88)
        count=round(duration*RATE)
        position=np.arange(count,dtype=np.float64)*tuning['pitch']
        audio=np.interp(position,np.arange(len(source)),source,left=0,right=0).astype(np.float32)
        audio,processing=strengthen(audio,tier['family'])
        fade=round(processing['tailFadeSeconds']*RATE)
        measured=metric(audio)
        if measured['peakDb']<=-299:raise ValueError('Silent source '+source_path)
        return task,audio,duration,fade,measured,processing
    prepared=[prepare(task) for task in tasks]
    # Each source gets its own smooth-knee peak treatment. One unusually high
    # crest no longer lowers every gun family beneath its intended foreground.
    common_offset=0
    targets={family:tuning['targetEffectiveK100Db']+common_offset for family,tuning in FAMILY.items()}
    def build(prepared_task):
        task,audio,duration,fade,measured,processing=prepared_task
        tier,index,source,source_path=task;tuning=FAMILY[tier['family']]
        gains=event_gains[tier['id']];target=targets[tier['family']]
        audio,mastering=master(audio,target-gains['Local'],lambda a:window_rms_db(kweighted(a)),ENCODE_HEADROOM_DB)
        gain_db=mastering['inputGainDb']
        slug=tier['id'].removeprefix('Weapon_Crossbow_')
        relative=f'Sounds/Arsenal/{slug}/Fire_{index:02}.ogg';dest=ROOT/'Common'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        cmd=[str(FFMPEG),'-v','error','-nostdin','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','pipe:0','-map_metadata','-1','-c:a','libvorbis','-q:a','5',str(dest)]
        def encode(samples):
            subprocess.run(cmd,input=samples.astype('<f4').tobytes(),capture_output=True,check=True)
            result=dest.read_bytes();decoded=decode(result)
            encoded=metric(decoded)
            encoded['fourTimesOversampledPeakDb']=db(oversampled_peak(decoded))
            encoded['first20msRmsDb']=db(np.sqrt(np.mean(decoded[:round(RATE*.02)].astype(np.float64)**2)))
            return result,decoded,encoded
        raw,decoded,encoded=encode(audio)
        error=target-(encoded['maximum100msKWeightedRmsDb']+gains['Local'])
        correction=min(error,-1.25-max(encoded['peakDb'],encoded['fourTimesOversampledPeakDb']))
        corrected=abs(error)>.05 or max(encoded['peakDb'],encoded['fourTimesOversampledPeakDb'])>=-1.25
        if corrected:
            raw,decoded,encoded=encode(audio*10**(correction/20))
            gain_db+=correction
        # Read the Vorbis identification header independently of the encoder's
        # arguments: codec, channel count and sample rate are part of the file.
        header=raw.find(b'\x01vorbis')
        if header<0:raise ValueError('Missing Vorbis identification')
        channels=raw[header+11];rate=int.from_bytes(raw[header+12:header+16],'little')
        actual=len(decoded)/RATE
        if channels!=1 or rate!=RATE or not np.isfinite(decoded).all() or max(encoded['peakDb'],encoded['fourTimesOversampledPeakDb'])>=DECODED_PEAK_LIMIT_DB or abs(actual-duration)>.025 or actual>=tier['cycleSeconds']:
            raise ValueError('Audio validation failed '+str(dest))
        return {'weaponId':tier['id'],'family':tier['family'],'variant':index,'path':relative,'runtimePath':'Common/'+relative,
                'durationSeconds':actual,'cycleSeconds':tier['cycleSeconds'],'sampleRate':rate,'channels':channels,'codec':'Vorbis',
                **{key:round(value,4) for key,value in encoded.items()},
                'localEventGainDb':gains['Local'],'worldEventGainDb':gains['World'],
                'effectiveLocal100msKWeightedRmsDb':round(encoded['maximum100msKWeightedRmsDb']+gains['Local'],4),
                'effectiveWorld100msKWeightedRmsDb':round(encoded['maximum100msKWeightedRmsDb']+gains['World'],4),
                'targetEffectiveLocal100msKWeightedRmsDb':round(target,4),'normalizationGainDb':round(gain_db,4),'postEncodeCorrectionApplied':corrected,
                'sha256':hashlib.sha256(raw).hexdigest(),'sourceRuntimePath':source_path,'sourceSHA256':provenance[source_path]['sha256'],
                'sourceVersion':revision['version'],'sourceArtifact':revision['artifact'],'sourceArtifactSHA256':digest,
                'sources':provenance[source_path]['sources'],'processing':{'pitchRatio':tuning['pitch'],'fadeSeconds':fade/RATE,'cadenceFraction':round(actual/tier['cycleSeconds'],4),'sourceUntouched':True,'impactRemaster':processing,'mastering':mastering}}
    with ThreadPoolExecutor(max_workers=4) as pool:clips=list(pool.map(build,prepared))
    family_metrics={}
    for family in FAMILY:
        members=[c for c in clips if c['family']==family]
        regions={}
        for weapon in sorted({c['weaponId'] for c in members}):
            variants=[c for c in members if c['weaponId']==weapon]
            regions[weapon]={mode:round(float(np.mean([c[f'effective{mode}100msKWeightedRmsDb'] for c in variants])),4) for mode in ('Local','World')}
        family_metrics[family]={'clips':len(members),'maximumDurationSeconds':max(c['durationSeconds'] for c in members),
            'targetEffectiveLocal100msKWeightedRmsDb':round(targets[family],4),'regions':regions,
            'localClipSpreadDb':round(max(c['effectiveLocal100msKWeightedRmsDb'] for c in members)-min(c['effectiveLocal100msKWeightedRmsDb'] for c in members),4),
            'worldClipSpreadDb':round(max(c['effectiveWorld100msKWeightedRmsDb'] for c in members)-min(c['effectiveWorld100msKWeightedRmsDb'] for c in members),4)}
        for mode in ('Local','World'):
            values=[v[mode] for v in regions.values()]
            family_metrics[family][mode.lower()+'RegionSpreadDb']=round(max(values)-min(values),4)
        if any(family_metrics[family][key]>1.5 for key in ('localClipSpreadDb','worldClipSpreadDb','localRegionSpreadDb','worldRegionSpreadDb')):
            raise ValueError('Encoded family/region loudness spread exceeds1.5dB: '+family)
    metric_contract={'measure':'Maximum sliding100ms K-weighted RMS plus nominal native event and layer gain',
        'filter':'BS.1770 K-weighting at48000Hz; energy window100ms, no integrated-LUFS claim',
        'randomEventVolumeRangeDb':[-.25,0],'randomPitchRangeSemitones':[-.12,.12],
        'spatialAttenuationIncluded':False,'humanListeningVerified':False,'maximumFamilyRegionSpreadDb':1.5,
        'decodedPeakStrictlyBelowDbFS':DECODED_PEAK_LIMIT_DB,'fourTimesOversampledPeakStrictlyBelowDbFS':DECODED_PEAK_LIMIT_DB,
        'commonHeadroomOffsetDb':round(common_offset,4),'familyTargets':targets,
        'masteringPolicy':'Per-clip source-derived impact/body treatment and smooth-knee peak control; no global crest penalty'}
    write(ROOT/'catalog.json',{'schemaVersion':2,'baselineVersion':revision['version'],'baselineSHA256':digest,
          'sourceVersion':revision['version'],'sourceSHA256':digest,'sourceArtifact':revision['artifact'],
          'runtimeFormat':'48kHz mono Ogg Vorbis','loudnessMetricContract':metric_contract,'families':family_metrics,
          'clips':clips,'events':events,'sourcePacks':frozen.get('sourcePacks',[]),
          'creditNotices':frozen['creditNotices'],'attributionScope':frozen['attributionScope'],
          'credits':'Audio Credits (selected artifact notices retained verbatim)',
          'limitations':[f"Frozen {revision['version']} designed firing effects are adapted to each family; this is an audio-only revision over gameplay baseline1.6.0.",'Static codec, cadence, clipping and loudness checks do not replace spatial in-game listening.']})
    write(ROOT/'validation.json',{'passed':True,'weapons':45,'clips':len(clips),'events':len(events),'mono48000Vorbis':all(c['channels']==1 and c['sampleRate']==RATE for c in clips),
          'allClipsEndBeforeNextShot':all(c['durationSeconds']<c['cycleSeconds'] for c in clips),'maximumDecodedPeakDb':max(c['peakDb'] for c in clips),
          'sourceRecordingsModified':False,'sourceVersion':revision['version'],'sourceSHA256':digest,'sourceArtifact':revision['artifact'],
          'creditNoticesVerified':len(frozen['creditNotices']),'loudnessMetricContract':metric_contract,'families':family_metrics})
    write_comparison(spec,clips,before_root,before_manifest,event_gains)
    print(json.dumps({'clips':len(clips),'events':len(events),'passed':True,'sourceVersion':revision['version'],'sourceSHA256':digest}))

if __name__=='__main__':main()
