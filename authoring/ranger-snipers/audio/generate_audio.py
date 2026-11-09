import os
"""Reproducible weapon sound design from licensed recordings and original DSP.

The sources are never modified. Runtime files are mono 48kHz Vorbis; native
local/spatial events share their authored mix, with separate gain/attenuation.
"""
from pathlib import Path
import hashlib,json,math,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
AUDIO=ROOT/'audio'
RATE=48000
FFMPEG=Path(os.environ.get('FFMPEG', 'ffmpeg'))
COMMON=AUDIO/'Common'
SERVER=AUDIO/'generated/Server'
WORK=AUDIO/'work'
CACHE={}
USED=set()

GUN=AUDIO/'sources/tabasco-gunshot-sounds/extracted/sounds'
FOLEY=AUDIO/'sources/springyspringo-gun-reloads'
SCI=AUDIO/'sources/kenney-sci-fi-sounds/extracted/Audio'

def db(value):return 10**(value/20)
def peak(x):return float(np.max(np.abs(x))) if len(x) else 0.
def fit(x,seconds):
    n=round(seconds*RATE)
    return np.pad(x[:n],(0,max(0,n-len(x))))
def fade(x,attack=.002,release=.04):
    x=np.array(x,dtype=float,copy=True)
    a=min(round(attack*RATE),len(x)//3);r=min(round(release*RATE),len(x)//3)
    if a:x[:a]*=np.sin(np.linspace(0,np.pi/2,a))**2
    if r:x[-r:]*=np.cos(np.linspace(0,np.pi/2,r))**2
    return x
def normalized(x):return x/max(peak(x),1e-12)
def filtered(x,low=45,high=12000):
    # Zero-phase padded spectral filter: stable and deterministic for one-shots.
    n=1<<max(1,(len(x)*2-1).bit_length());f=np.fft.rfftfreq(n,1/RATE)
    hp=1/np.sqrt(1+(low/np.maximum(f,1e-9))**6) if low else np.ones_like(f)
    lp=1/np.sqrt(1+(f/high)**8) if high else np.ones_like(f)
    return np.fft.irfft(np.fft.rfft(x,n)*hp*lp,n)[:len(x)]
def pitch(x,rate):
    return np.interp(np.arange(0,len(x)-1,rate),np.arange(len(x)),x)
def add(*layers):
    # Each layer is (samples, gain, offset seconds).
    n=max((len(x)+round(t*RATE) for x,g,t in layers),default=0)
    y=np.zeros(n)
    for x,g,t in layers:
        i=round(t*RATE);y[i:i+len(x)]+=x*g
    return y
def tone(seconds,start,end=None,decay=7,kind='sine',seed=0):
    t=np.arange(round(seconds*RATE))/RATE
    end=start if end is None else end
    phase=2*np.pi*(start*t+(end-start)*t*t/(2*seconds))
    x=np.sin(phase)
    if kind=='metal':x=.68*x+.22*np.sin(phase*2.756)+.10*np.sin(phase*4.103)
    if kind=='air':
        noise=np.random.default_rng(seed).normal(size=len(t));x=.35*x+.65*filtered(noise,700,6500)
    return fade(x*np.exp(-decay*t/seconds),.001,min(.04,seconds/4))
def read(path):
    path=Path(path);USED.add(path)
    if path not in CACHE:
        data=subprocess.run([str(FFMPEG),'-v','error','-i',str(path),'-ac','1','-ar',str(RATE),
                             '-f','f32le','-'],capture_output=True,check=True).stdout
        CACHE[path]=np.frombuffer(data,dtype='<f4').astype(float)
    return CACHE[path].copy()
def attack_trim(x,threshold=.025):
    active=np.flatnonzero(np.abs(x)>max(peak(x)*threshold,1e-6))
    return x[max(0,int(active[0]) - 48):] if len(active) else x
def shot(source,variant):
    # Isolated onsets, not whole recordings containing several shots/handling.
    starts={'mosin':[.41,5.95,12.15],'sks':[.34,6.00,12.72],
            'cz':[.26,2.76,5.48],'shotty':[.148,.148,.148]}
    x=read(GUN/(source+'.wav'));start=round(starts[source][variant%3]*RATE)
    x=attack_trim(x[start:start+round(.82*RATE)],.03)
    return fade(normalized(x),.0008,.15)
def sci(name,index,seconds=.7):
    return fade(fit(attack_trim(normalized(read(SCI/f'{name}_{index:03}.ogg'))),seconds),.001,.06)
def foley(kind,variant=0,seconds=.16):
    # Individual transients from self-recorded airsoft handling, not full reloads.
    if kind=='open':filename='shotguncock_0.wav';start=.012+variant*.012
    elif kind=='insert':filename='assaultriflereload1_0.wav';start=.21+variant*.01
    elif kind=='close':filename='gunreload1.wav';start=1.22+variant*.008
    else:filename='gunreload1.wav';start=.12+variant*.008
    x=read(FOLEY/filename);x=x[round(start*RATE):round((start+seconds)*RATE)]
    return fade(fit(normalized(attack_trim(x,.025)),seconds),.001,.028)
def space(x,amount,seed):
    taps=[(.027,.35),(.061,.24),(.107,.16),(.179,.10),(.273,.055)]
    y=fit(x,len(x)/RATE+.32)
    for delay,g in taps:
        copy=filtered(x,110,4300);i=round((delay+seed*.0005)*RATE)
        y[i:i+len(copy)]+=copy*g*amount
    return fade(y,.0008,.12)

def robot(entry, seconds, rate=1., offset=0.):
    """Extract one curated impact, aligning its main transient to the cue frame."""
    raw=read(AUDIO/entry['path'])
    start=max(0,round((entry['anchorSeconds']-.012+offset)*RATE))
    look=raw[start:start+round(.055*RATE)]
    if len(look)>240:
        energy=np.convolve(look*look,np.ones(240)/240,'valid')
        start+=max(0,int(np.argmax(energy))-round(.006*RATE))
    count=round(seconds*rate*RATE)+2
    x=normalized(raw[start:start+count])
    return fade(fit(pitch(x,rate),seconds),.0008,min(.025,seconds/4))

def decay(x, hold=.012, slope=13.):
    t=np.arange(len(x))/RATE
    return x*np.exp(-np.maximum(0,t-hold)*slope)

def fire(profile,variant,special=False):
    USED.clear();idx=variant%3;pal=profile['robotic'];slug=profile['slug']
    rate=profile['playbackRate']*(1+[-.016,.001,.018][idx])
    body=profile['bodyHz'];ring=profile['ringHz'] or body*5
    # One central discharge. Whole transformation/weapon sequences are never used.
    primary=decay(robot(pal['primary'],.39,rate,[-.002,0,.002][idx]),.012,13.)
    variation=decay(robot(pal['variations'][idx],.30,rate),.008,18.)
    bolt=decay(robot(pal['close'],.11,rate),.006,24.)
    x=add((filtered(primary,65,profile['lowpassHz']),.82,0),
          (filtered(variation,160,profile['lowpassHz']),.19,.002),
          (tone(.25,body,body*.72,7),.18,.003),
          (filtered(bolt,380,7500),.055,.009))
    if not profile['energized']:
        # Actual cartridge/bolt character underneath the robotic report.
        x=add((x,1,0),(filtered(shot(profile['shotSource'],idx),180,6000),.16,0))
    if slug=='Mournhollow_Epitaph':
        x=add((x,1,0),(tone(.36,207.65,174.6,8,'metal'),.10,.012))
    elif slug=='Nameless_Covenant':
        t=np.arange(round(.33*RATE))/RATE
        cage=tone(.33,466,392,8,'metal')*(.72+.28*np.cos(2*np.pi*41*t))
        x=add((x,1,0),(cage,.10,.008))
    elif slug=='Deepworks_Railspike':
        x=add((x,1,0),(tone(.31,74,49,7,'air',idx+44),.20,.002))
    elif slug=='Luminia_Dawnpiercer':
        x=add((x,1,0),(tone(.29,1480,1332,8,'metal'),.13,.006),
              (tone(.26,2220,1998,9),.055,.011))
    elif slug=='Labyrinth_Threadkeeper':
        x=add((x,1,0),(tone(.22,880,660,10,'metal'),.12,.003))
    elif slug=='Frostline_Sentinel':
        x=add((x,1,0),(tone(.24,1800,1760,10,'metal'),.055,.009))
    elif slug=='Skybound_Farwatch':
        x=add((x,1,0),(tone(.19,1056,1320,10,'metal'),.045,.014))
    if special:
        if slug=='Deepworks_Railspike':
            cannon=decay(robot(pal['variations'][0],.49,rate*.81),.016,11.)
            x=add((x,.85,0),(filtered(cannon,55,6200),.58,.002),
                  (tone(.48,61,34,7,'air',idx+91),.26,.004))
        else:
            # A launch pulse with a prism chord; never a hit/lock confirmation.
            x=add((x,.60,0),(tone(.36,1110,1056,8,'metal'),.17,.003),
                  (tone(.31,1665,1584,9),.10,.012))
    length=1.35 if special else 1.04
    return fade(fit(space(x,profile['reflections']*.55,idx),length),.001,.10)

def cue(profile,action):
    USED.clear();pal=profile['robotic'];n=sum(map(ord,profile['slug']))%3
    rate=profile['playbackRate'];ring=profile['ringHz'] or profile['bodyHz']*4
    if action in ('ReloadOpen','ReloadInsert','ReloadClose','Empty'):
        duration={'ReloadOpen':.21,'ReloadInsert':.18,'ReloadClose':.19,'Empty':.115}[action]
        active={'ReloadOpen':.145,'ReloadInsert':.115,'ReloadClose':.145,'Empty':.065}[action]
        source={'ReloadOpen':'open','ReloadInsert':'insert','ReloadClose':'close','Empty':'open'}[action]
        kind={'ReloadOpen':'open','ReloadInsert':'insert','ReloadClose':'close','Empty':'empty'}[action]
        mechanism=decay(robot(pal[source],active,rate),.008,24.)
        physical=decay(foley(kind,n,active),.006,28.)
        x=add((filtered(mechanism,160,profile['lowpassHz']*.88),.85,0),
              (filtered(physical,220,8000),.25,.001))
        # A single feed clack. Double-load clips invoke this same cue twice.
        if profile['energized'] and action=='ReloadInsert':
            x=add((x,1,0),(tone(.065,ring*.5,ring*.62,8),.065,.005))
        return fade(fit(x,duration),.001,.025)
    if action in ('ChargeStart','ChargeMid','ChargeEnd','SpecialCharge'):
        phase={'ChargeStart':0,'ChargeMid':1,'ChargeEnd':2,'SpecialCharge':3}[action]
        duration=.26 if action=='SpecialCharge' else .20
        active={'ChargeStart':.115,'ChargeMid':.030,'ChargeEnd':.095,'SpecialCharge':.225}[action]
        fundamental=(110+profile['bodyHz']*.7)*(1+phase*.30)
        mech=decay(robot(pal['charge'],active,rate*(1+phase*.06)),.006,29 if phase<3 else 15)
        x=add((filtered(mech,180,5200),.67,0),
              (tone(active,fundamental,fundamental*1.55,7,'air',n+phase),.26,.002),
              (tone(active,fundamental*3,fundamental*3.9,8),.085,.003))
        # Mid clears even the50ms insertion gap on the expansion handguns. SpecialCharge only arms the Q;
        # its actual release remains on the native1-second projectile commit.
        return fade(fit(fade(x,.002,.018),duration),.001,.025)
    if action=='SpecialAbort':
        mech=robot(pal['charge'],.10,rate*.77)
        x=add((filtered(mech,220,3000),.40,0),(tone(.145,380,75,7,'air',n),.60,0))
        return fade(fit(x,.145),.002,.035)
    if action=='Ready':
        lock=decay(robot(pal['close'],.095,rate*1.12),.003,34.)
        x=filtered(lock,600,7500)*.68
        if profile['energized']:x=add((x,1,0),(tone(.12,ring,ring*1.001,8,'metal'),.24,.002))
        return fade(fit(x,.15),.001,.025)
    raise ValueError(action)

def finish(x,action):
    x=np.nan_to_num(x);x=filtered(x,40,15000);x-=np.mean(x)
    is_fire=action in ('Fire','SpecialFire')
    if is_fire:
        measured=np.sqrt(np.mean(x[:min(len(x),round(.20*RATE))]**2))+1e-12
        # Soft control tames isolated cannon spikes before energy matching;
        # it adds no hard clipping and retains a short, weighty report.
        knee=3.0*measured
        x=knee*np.tanh(x/knee)
        measured=np.sqrt(np.mean(x[:min(len(x),round(.20*RATE))]**2))+1e-12
        desired=db(-15.5 if action=='Fire' else -14.0)
    else:
        win=min(len(x),round(.020*RATE))
        measured=math.sqrt(float(np.max(np.convolve(x*x,np.ones(win)/win,'valid'))))+1e-12
        desired=db(-24 if 'Charge' in action else (-23 if action in ('Ready','Empty','SpecialAbort') else -20))
    x*=min(6,desired/measured)
    # Peak ceiling only attenuates: never undo the energy balance by boosting
    # every short cue to the same peak. Vorbis decoding retains headroom.
    ceiling=db(-4 if is_fire else -9)
    x*=min(1,ceiling/max(peak(x),1e-12))
    return fade(x,.001,.05 if is_fire else .020)

def source_rows():
    rows=[]
    for p in sorted(USED):
        key=next((bank for bank in ('bluezone-transformers','bluezone-robot','bluezone-weapon','bluezone-mechanical') if p.is_relative_to(AUDIO/'sources'/bank)),None)
        if key is None:key='tabasco-gunshot-sounds' if p.is_relative_to(GUN) else ('springyspringo-gun-reloads' if p.is_relative_to(FOLEY) else 'kenney-sci-fi-sounds')
        rows.append({'sourceId':key,'path':p.relative_to(AUDIO).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    rows.append({'sourceId':'360-no-scope-original-dsp','description':'Original oscillators, envelopes, EQ, transient shaping, short reflections and layered arrangement.'})
    return rows

def write_clip(profile,action,variant,x,sources):
    name=f"{action}_{variant:02}"
    slug=profile['slug'];wav=WORK/slug/(name+'.wav');wav.parent.mkdir(parents=True,exist_ok=True)
    x=finish(x,action)
    # Four milliseconds of codec guard also protects quiet mechanical cues.
    # ChargeMid still clears the shortest50ms next-cue gap.
    x=np.pad(x,(round(.004*RATE),0))[:len(x)]
    with wave.open(str(wav),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes(np.round(np.clip(x,-1,1)*32767).astype('<i2').tobytes())
    runtime=f'Sounds/RangerSnipers/{slug}/{name}.ogg';ogg=COMMON/runtime;ogg.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(FFMPEG),'-v','error','-nostdin','-y','-i',str(wav),'-map_metadata','-1',
                    '-fflags','+bitexact','-flags:a','+bitexact',
                    '-c:a','libvorbis','-q:a','6','-ar',str(RATE),'-ac','1',str(ogg)],check=True)
    decoded=subprocess.run([str(FFMPEG),'-v','error','-i',str(ogg),'-ac','1','-ar',str(RATE),'-f','f32le','-'],capture_output=True,check=True).stdout
    samples=np.frombuffer(decoded,dtype='<f4').astype(float);window=min(len(samples),round(.1*RATE))
    squares=np.r_[0.,np.cumsum(samples*samples)]
    maximum_rms=math.sqrt(max(1e-20,float(np.max((squares[window:]-squares[:-window])/window))))
    return {'max100msRmsDbFS':20*math.log10(maximum_rms),'id':f'{slug}_{name}','rifleId':'Weapon_Crossbow_'+slug,'action':action,'variant':variant,
            'path':runtime,'runtimePath':'Common/'+runtime,'sourceWav':wav.relative_to(ROOT).as_posix(),
            'durationSeconds':len(x)/RATE,'sampleRate':RATE,'channels':1,
            'targetPeakDb':-4 if action in ('Fire','SpecialFire') else -9,
            'sources':sources,'sha256':hashlib.sha256(ogg.read_bytes()).hexdigest()}

def loudness(path):
    result=subprocess.run([str(FFMPEG),'-hide_banner','-nostdin','-i',str(path),
        '-af','loudnorm=I=-20:TP=-2:LRA=7:print_format=json','-f','null','-'],capture_output=True,check=True)
    output=result.stderr.decode('utf-8',errors='replace');data,_=json.JSONDecoder().raw_decode(output[output.rfind('{'):])
    return float(data['input_i'])

def event_gain(action,local,made):
    if action in ('Fire','SpecialFire'):
        # Balance perceived output using the actual encoded one-shots. Keep
        # transient headroom; quieter beam attacks are never boosted above0dB.
        mean=float(np.mean([r['integratedLufs'] for r in made]))
        target=-20 if action=='Fire' else -18.5
        gain=round(max(-6,min(0,target-mean)),2)
        return gain if local else gain-1
    if action=='Empty':return -11 if local else -15
    if action=='Ready':return -11 if local else -16
    if 'Charge' in action or action=='SpecialAbort':return -9 if local else -13
    return -8 if local else -13

def main():
    if not FFMPEG.exists():raise FileNotFoundError('Portable FFmpeg missing; see audio/tools/provenance.json')
    spec=json.loads((ROOT/'research/progression-spec.json').read_text());design=json.loads((AUDIO/'profiles.json').read_text())
    profiles={p['rifleId']:p for p in design['profiles']};clips=[];events=[];rifles=[]
    for weapon in spec['tiers']:
        profile=profiles[weapon['id']];audio=weapon['audio'];action_clips={}
        for action,pair in audio['events'].items():
            count=3 if action in ('Fire','SpecialFire') else 1;made=[]
            for variant in range(1,count+1):
                x=fire(profile,variant-1,action=='SpecialFire') if action in ('Fire','SpecialFire') else cue(profile,action)
                row=write_clip(profile,action,variant,x,source_rows());row['events']=list(pair.values())
                if action in ('Fire','SpecialFire'):row['integratedLufs']=loudness(COMMON/row['path'])
                clips.append(row);made.append(row)
            action_clips[action]=made
            for side,event_id in pair.items():
                local=side=='Local';reach=(72 if action=='SpecialFire' else 64) if action in ('Fire','SpecialFire') else 20
                volume=event_gain(action,local,made)
                event={'AudioCategory':'AudioCat_Weapons','Volume':volume,'SpatialBlend':0 if local else 1,
                       'StartAttenuationDistance':3 if not local else 0,'MaxDistance':reach,
                       'MaxInstance':24 if action in ('Fire','SpecialFire') else 16,
                       'PreventSoundInterruption':False,
                       'Layers':[{'Files':[r['path'] for r in made],'Volume':0,'StartDelay':0,'Looping':False}]}
                if count>1:event['Layers'][0]['RandomSettings']={'MinPitch':-.2,'MaxPitch':.2,'MinVolume':-.2,'MaxVolume':0}
                path=f'Server/Audio/SoundEvents/RangerSnipers/{event_id}.json';dest=AUDIO/'generated'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(event,indent=2)+'\n')
                events.append({'id':event_id,'rifleId':weapon['id'],'action':action,'local':local,
                               'volumeDb':volume,'maxDistance':reach,'spatialBlend':0 if local else 1,
                               'path':path,'clipIds':[r['id'] for r in made],'files':[r['path'] for r in made]})
        rifles.append({'id':weapon['id'],'name':weapon['name'],'slug':profile['slug'],'theme':profile['theme'],
                       'events':audio['events'],'reloadTimelines':audio['reloadTimelines'],
                       'reloadDurationSeconds':weapon['reload']['durationSeconds'],'capacity':weapon['reload']['capacity'],
                       'ability':weapon.get('ability')})
    # Calibrate the actual encoded reports together, including dark/bass-heavy
    # voices. Attenuation changes alone keep perceived normal-shot power even.
    means={r['id']:float(np.mean([c['integratedLufs'] for c in clips if c['rifleId']==r['id'] and c['action']=='Fire'])) for r in rifles}
    fire_target=round(min(-20.,min(means.values())),2)
    for event in events:
        if event['action'] not in ('Fire','SpecialFire'):continue
        members=[c for c in clips if c['id'] in event['clipIds']]
        mean=float(np.mean([c['integratedLufs'] for c in members]))
        target=fire_target if event['action']=='Fire' else fire_target+(1.5 if event['rifleId'].endswith('Deepworks_Railspike') else -.75)
        gain=round(max(-18,min(0,target-mean)),2)-(0 if event['local'] else 1)
        event['volumeDb']=gain
        path=SERVER/'Audio/SoundEvents/RangerSnipers'/(event['id']+'.json')
        native=json.loads(path.read_text());native['Volume']=gain;path.write_text(json.dumps(native,indent=2)+'\n')
    # Keep mechanical actions audible but subordinate to this rifle's report.
    local_fire={e['rifleId']:e for e in events if e['action']=='Fire' and e['local']}
    fire_rms={item:float(np.mean([c['max100msRmsDbFS'] for c in clips if c['rifleId']==item and c['action']=='Fire']))+event['volumeDb'] for item,event in local_fire.items()}
    for event in events:
        action=event['action']
        if action in ('Fire','SpecialFire'):continue
        member=next(c for c in clips if c['id']==event['clipIds'][0])
        contrast=10 if action in ('ReloadOpen','ReloadInsert','ReloadClose') else (14 if action=='Ready' else (12 if action=='SpecialAbort' else 13))
        gain=round(max(-18,min(0,fire_rms[event['rifleId']]-contrast-member['max100msRmsDbFS'])),2)
        if not event['local']:gain-=5 if action in ('ReloadOpen','ReloadInsert','ReloadClose','Ready') else 4
        event['volumeDb']=gain
        path=SERVER/'Audio/SoundEvents/RangerSnipers'/(event['id']+'.json')
        native=json.loads(path.read_text());native['Volume']=gain;path.write_text(json.dumps(native,indent=2)+'\n')
    source_manifest=json.loads((AUDIO/'sources/source-manifest.json').read_text())
    used_ids={source['sourceId'] for c in clips for source in c['sources']}

    catalog={'schemaVersion':1,'modName':spec['modName'],'version':spec['version'],'sampleRate':RATE,
             'runtimeFormat':'48kHz mono Ogg Vorbis','normalFireTargetLUFS':fire_target,'clips':clips,'events':events,'rifles':rifles,
             'sourcePacks':[{k:p[k] for k in ('id','title','author','sourceUrl','license','licenseUrl')} for p in source_manifest['packs'] if p['id'] in used_ids],
             'audioStyle':'Original cinematic transforming-machine effects from credited Bluezone free packs, with tailored physical handling and DSP; not extracted movie recordings.',
             'scope':'Mixed and objectively analyzed offline; subjective listening and Hytale playback remain a player-client check.'}
    (AUDIO/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(f'Authored {len(clips)} OGG one-shots, {len(events)} native local/world events, {len(rifles)} rifle audio identities.')

if __name__=='__main__':main()
