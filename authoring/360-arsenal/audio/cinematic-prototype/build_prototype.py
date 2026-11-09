import os
"""Stage a source-driven spatial audition. Never edits an input JAR or deployment.

Manifest layers accept raw/Suno WAV segments; only finite one-shot OGG assets and
existing SoundEvent JSONs are emitted. No gameplay/Java/interaction changes.
"""
from pathlib import Path
from itertools import product
from functools import lru_cache
import argparse, hashlib, json, math, subprocess, wave
from zipfile import ZipFile
import numpy as np

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
RATE=48000
FFMPEG=Path(os.environ.get('FFMPEG', 'ffmpeg'))

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def db(x):return float(20*np.log10(max(float(x),1e-15)))
def gain(x):return 10**(x/20)

@lru_cache(maxsize=24)
def decode(path):
    return np.frombuffer(subprocess.run([str(FFMPEG),'-v','error','-nostdin','-i',str(path),'-ac','1','-ar',str(RATE),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout,dtype='<f4').copy()

@lru_cache(maxsize=32)
def decode_channel(path,channel):
    return np.frombuffer(subprocess.run([str(FFMPEG),'-v','error','-nostdin','-i',str(path),'-af',f'pan=mono|c0=c{int(channel)}','-ar',str(RATE),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout,dtype='<f4').copy()

def filter_band(x,lo=25,hi=18000):
    n=1<<(len(x)+4095).bit_length();f=np.fft.rfftfreq(n,1/RATE)
    low=1/(1+(lo/np.maximum(f,1e-9))**4) if lo else np.ones(len(f))
    high=1/(1+(f/hi)**8) if hi else np.ones(len(f))
    return np.fft.irfft(np.fft.rfft(x,n)*low*high,n)[:len(x)]

def peak4(x):
    maximum=float(np.max(np.abs(x)))
    t=np.arange(49)-24
    for phase in (.25,.5,.75):
        h=np.sinc(t-phase)*np.hanning(49);h/=h.sum()
        maximum=max(maximum,float(np.max(np.abs(np.convolve(x,h,'same')))))
    return maximum

def metrics(x):
    window=min(len(x),round(RATE*.1));q=np.r_[0,np.cumsum(x.astype(np.float64)**2)]
    return {'seconds':len(x)/RATE,'samplePeakDb':db(np.max(np.abs(x))),'truePeak4xDb':db(peak4(x)),
            'maximum100msRmsDb':db(np.sqrt(np.max(q[window:]-q[:-window])/window)),
            'rmsDb':db(np.sqrt(np.mean(x.astype(np.float64)**2)))}

def wav(path,x):
    path.parent.mkdir(parents=True,exist_ok=True)
    if np.max(np.abs(x))>=1:raise ValueError('Preview clips at PCM conversion')
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(np.round(x*32767).astype('<i2').tobytes())

def encode(path,x):
    path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(FFMPEG),'-v','error','-nostdin','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','pipe:0','-c:a','libvorbis','-q:a','7',str(path)],input=x.astype('<f4').tobytes(),capture_output=True,check=True)
    return decode(str(path)).copy()

def mix(arrays,offsets=None):
    offsets=offsets or [0]*len(arrays);n=max(a+len(x) for a,x in zip(offsets,arrays));out=np.zeros(n)
    for a,x in zip(offsets,arrays):out[a:a+len(x)]+=x
    return out

def component(c,base,provenance):
    path=Path(c['path']);path=path if path.is_absolute() else (base/path).resolve()
    a=decode_channel(str(path),c['sourceChannel']) if 'sourceChannel' in c else decode(str(path))
    start=round(c.get('startSeconds',0)*RATE);count=round(c.get('durationSeconds',(len(a)-start)/RATE)*RATE)
    if start<0 or count<=0 or start+count>len(a)+4:raise ValueError(f'Invalid source segment: {path}')
    x=a[start:min(start+count,len(a))].astype(np.float64)
    speed=c.get('playbackRate',1)
    if speed!=1:x=np.interp(np.arange(math.ceil(len(x)/speed))*speed,np.arange(len(x)),x)
    x=filter_band(x,c.get('highpassHz',25),c.get('lowpassHz',18000))
    if 'peakDb' in c:x*=gain(c['peakDb'])/max(np.max(np.abs(x)),1e-12)
    x*=gain(c.get('gainDb',0))
    for edge,seconds in [('in',c.get('fadeInSeconds',.0005)),('out',c.get('fadeOutSeconds',.04))]:
        n=min(len(x)//2,round(seconds*RATE))
        if n:
            fade=np.linspace(0,1,n)**1.2
            if edge=='in':x[:n]*=fade
            else:x[-n:]*=fade[::-1]
    provenance.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sourceFrames':len(a),'sourceSampleRate':RATE,'processing':{k:v for k,v in c.items() if k!='path'}})
    return x

def render_layers(w,base):
    layers=[];provenance=[]
    for l in w['layers']:
        variants=[]
        for v in l['variants']:
            cs=v.get('components',[v]);parts=[component(c,base,provenance) for c in cs]
            offsets=[round(c.get('outputOffsetSeconds',0)*RATE) for c in cs]
            variants.append(mix(parts,offsets))
        layers.append({'name':l['name'],'delay':round(l.get('delaySeconds',0)*RATE),'volumeDb':l.get('volumeDb',0),'variants':variants})
    return layers,provenance

def shot(layers,selection):
    return mix([l['variants'][i]*gain(l['volumeDb']) for l,i in zip(layers,selection)],[l['delay'] for l in layers])

def burst(layers,cycle,seed,seconds=4):
    rng=np.random.default_rng(seed);shots=[];offsets=[]
    for j,t in enumerate(np.arange(0,seconds,cycle)):
        picks=[int(rng.integers(len(l['variants']))) for l in layers]
        shots.append(shot(layers,picks));offsets.append(round(t*RATE))
    return mix(shots,offsets)

def budget(layers,cycle):
    # Mixed independent layer choices, plus sustained automatic combinations.
    singles=[peak4(shot(layers,c)) for c in product(*[range(len(l['variants'])) for l in layers])]
    repeated=[peak4(burst(layers,cycle,s)) for s in range(32)] if cycle<.65 else []
    maximum=max(singles+repeated);return min(1,gain(-2.2)/maximum),{'unscaledMaximumTruePeak4xDb':db(maximum),'singleCombinations':len(singles),'burstSeeds':len(repeated)}

def build(manifest,artifact,output):
    if not output.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Output must stay in isolated cinematic-prototype folder')
    config=json.loads(manifest.read_text(encoding='utf-8-sig'))
    report={'status':'isolated audition, not installed','inputArtifact':str(artifact.resolve()),'inputArtifactSHA256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'gameplayChanges':False,'runtimeBinaryChanges':False,'masterCompressionUsed':False,'sourcePacks':config.get('sourcePacks',[]),'previewGainContract':'Native Local event gain, no extra preview normalization','weapons':[]}
    with ZipFile(artifact) as z:
        sounds={Path(n).stem:(n,json.loads(z.read(n))) for n in z.namelist() if n.startswith('Server/Audio/SoundEvents/') and n.endswith('.json')}
        for w in config['weapons']:
            if not 1<=len(w['layers'])<=8:raise ValueError('Native layer count is 1..8')
            layers,provenance=render_layers(w,manifest.parent);cycle=w['cycleSeconds'];scale,evidence=budget(layers,cycle)
            for l in layers:l['variants']=[a*scale for a in l['variants']]
            slug=w['weaponId'].removeprefix('Weapon_Crossbow_');folder='Arsenal' if slug.startswith('AS_') else 'RangerSnipers'
            native_layers=[];stems=[]
            for l in layers:
                names=[];decoded=[]
                for i,x in enumerate(l['variants'],1):
                    relative=f'Common/Sounds/{folder}/{slug}/Cinematic_{l["name"]}_{i:02}.ogg'
                    value=encode(output/relative,x);names.append(relative.removeprefix('Common/'));decoded.append(value)
                    stems.append({'path':relative,'sha256':hashlib.sha256((output/relative).read_bytes()).hexdigest(),**metrics(value)})
                l['variants']=decoded
                native_layers.append({'Files':names,'Volume':l['volumeDb'],'StartDelay':l['delay']/RATE,'Looping':False,'RoundRobinHistorySize':min(1,len(names)-1)})
            events=[]
            for route,id in w['events'].items():
                path,original=sounds[id];event=dict(original)
                event.update({'Volume':w.get('localVolumeDb',0) if route=='Local' else w.get('worldVolumeDb',-3),'SpatialBlend':0 if route=='Local' else 1,'StartAttenuationDistance':0 if route=='Local' else w.get('startAttenuationBlocks',4),'MaxDistance':w.get('maxDistanceBlocks',128),'MaxInstance':32,'PreventSoundInterruption':False,'Layers':native_layers})
                write(output/path,event);events.append({'id':id,'path':path,'route':route,'volumeDb':event['Volume'],'spatialBlend':event['SpatialBlend']})
            # Re-test decoded assets at native Local gain after Vorbis encoding.
            local_gain=gain(w.get('localVolumeDb',0));single=shot(layers,[0]*len(layers))*local_gain
            combinations=[peak4(shot(layers,c)*local_gain) for c in product(*[range(len(l['variants'])) for l in layers])]
            burst_max=max(peak4(burst(layers,cycle,s)*local_gain) for s in range(32)) if cycle<.65 else None
            if db(max(combinations+([burst_max] if burst_max else [])))>-1:raise ValueError('Decoded composite/burst exceeds -1 dBFS; lower source gains or budget')
            wav(output/f'previews/{slug}_Single_After.wav',single)
            for l in layers:wav(output/f'previews/{slug}_Stem_{l["name"]}.wav',l['variants'][0]*gain(l['volumeDb'])*local_gain)
            _,before_event=sounds[w['events']['Local']];before_layer=before_event['Layers'][0];before_path='Common/'+before_layer['Files'][0]
            raw=z.read(before_path);temp=output/'reference'/slug/Path(before_path).name;temp.parent.mkdir(parents=True,exist_ok=True);temp.write_bytes(raw)
            before=decode(str(temp))*gain(before_event.get('Volume',0)+before_layer.get('Volume',0))
            wav(output/f'previews/{slug}_Single_Before.wav',before)
            silence=np.zeros(round(RATE*1.2));wav(output/f'previews/{slug}_Single_Before_After.wav',np.r_[before,silence,single])
            if cycle<.65:
                after_burst=burst(layers,cycle,9)*local_gain
                before_burst=mix([before]*len(np.arange(0,4,cycle)),[round(t*RATE) for t in np.arange(0,4,cycle)])
                wav(output/f'previews/{slug}_Burst_4s_After.wav',after_burst)
                wav(output/f'previews/{slug}_Burst_4s_Before_After.wav',np.r_[before_burst,silence,after_burst])
            end=round(cycle*RATE);tail_energy=float(np.sum(single[end:]**2)/max(np.sum(single**2),1e-15))
            report['weapons'].append({'weaponId':w['weaponId'],'sourceStatus':w.get('sourceStatus','audition'),'cycleSecondsUnchanged':cycle,'sourceComponents':provenance,'events':events,'stems':stems,'linearBudgetGainDb':db(scale),'budget':evidence,'single':metrics(single),'beforeSingle':metrics(before),'decodedCompositeMaxTruePeak4xDb':db(max(combinations)),'decoded4sBurstMaxTruePeak4xDb':db(burst_max) if burst_max else None,'energyAfterNextShotFraction':tail_energy,'audibleTailAfterCycleIntended':len(single)>end})
    write(output/'prototype-report.json',report)
    print(json.dumps({'weapons':len(report['weapons']),'output':str(output),'gameplayChanges':False,'runtimeBinaryChanges':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('--artifact',type=Path,default=PROJECT/'release/360-No-Scope-2.0.4.jar');p.add_argument('--output',type=Path,default=ROOT/'staged')
    a=p.parse_args();build(a.manifest.resolve(),a.artifact.resolve(),a.output.resolve())
