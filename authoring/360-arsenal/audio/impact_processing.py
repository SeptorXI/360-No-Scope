"""Source-only gun report mastering; no synthesized recordings or new source inputs."""
from functools import lru_cache
import numpy as np

RATE=48000
TREATMENT={
 'handgun':dict(low=.34,sub=.24,parallel=.28,crack=.20,mechanical=.11,decay=.12,subPitch=.78),
 'smg':dict(low=.22,sub=.12,parallel=.22,crack=.17,mechanical=.10,decay=.065,subPitch=.86),
 'semiauto':dict(low=.40,sub=.29,parallel=.30,crack=.23,mechanical=.12,decay=.15,subPitch=.76),
 'automatic':dict(low=.30,sub=.20,parallel=.26,crack=.20,mechanical=.11,decay=.085,subPitch=.82),
 'shotgun':dict(low=.55,sub=.48,parallel=.36,crack=.22,mechanical=.14,decay=.23,subPitch=.69),
}

@lru_cache(maxsize=32)
def kernel(cutoff,taps=129):
    t=np.arange(taps,dtype=np.float64)-(taps-1)/2
    h=2*cutoff/RATE*np.sinc(2*cutoff/RATE*t)*np.hanning(taps)
    return h/h.sum()

def lowpass(a,cutoff):return np.convolve(a,kernel(cutoff),mode='same')
def band(a,low,high):return lowpass(a,high)-lowpass(a,low)

def strengthen(source,family):
    """Retain the regional recording, adding only transformed copies of itself.

    Low body and a lower-pitched band supply weight, parallel saturation raises
    its physical sustain, a short high-band copy brings out the report's crack
    and a delayed high-band accent exposes existing mechanical texture.
    """
    a=source.astype(np.float64);p=TREATMENT[family];count=len(a);time=np.arange(count)/RATE
    peak=max(float(np.max(np.abs(a))),1e-9);x=a/peak
    compressed=np.tanh(x*3.4)/np.tanh(3.4)*peak
    body=band(a,65,420)*np.exp(-time/p['decay'])
    down=np.interp(np.arange(count)*p['subPitch'],np.arange(count),a,left=0,right=0)
    sub=band(down,48,235)*np.exp(-time/(p['decay']*1.3))
    crack=(a-lowpass(a,2100))*np.exp(-time/.026)
    delay=round(RATE*(.029 if family in ('smg','automatic')else .045))
    mechanism=np.zeros(count)
    if count>delay:
        mechanical=(a-lowpass(a,1700))*np.exp(-time/.033)
        mechanism[delay:]=mechanical[:-delay]
    mix=(.86*a+p['parallel']*compressed+p['low']*body+p['sub']*sub+p['crack']*crack+p['mechanical']*mechanism)
    # Front edge stays abrupt enough to read as a firearm, with a sub-ms
    # anti-click ramp and a continuous tail taper to preserve cadence gaps.
    attack=min(round(.0007*RATE),count//20);mix[:attack]*=np.linspace(0,1,attack)
    fade=min(round((.025 if family in ('smg','automatic')else .05)*RATE),count//3)
    mix[-fade:]*=np.linspace(1,0,fade)**1.4
    return mix.astype(np.float32),{
        'method':'source-derived low band + lower-pitched body + parallel saturation + transient crack + delayed recorded texture',
        'sourceOnly':True,'treatment':p,'antiClickRampSeconds':attack/RATE,'tailFadeSeconds':fade/RATE,
    }

def limit(audio,ceiling):
    """Smooth-knee peak compression, unchanged below75% of ceiling."""
    threshold=.75*ceiling;span=ceiling-threshold;absolute=np.abs(audio)
    excess=np.maximum(absolute-threshold,0)
    shaped=threshold+span*np.tanh(excess/span)
    return np.where(absolute>threshold,np.sign(audio)*shaped,audio).astype(np.float32)

def master(audio,target_db,measure,ceiling_db=-2.8):
    """Reach a per-clip energy target without a global downward gain penalty."""
    ceiling=10**(ceiling_db/20);initial=target_db-measure(audio);gain=initial
    out=audio
    for _ in range(14):
        out=limit(audio*10**(gain/20),ceiling)
        error=target_db-measure(out)
        if abs(error)<.008:break
        gain+=error
    if abs(target_db-measure(out))>.15:raise ValueError('Requested report density is not achievable within peak ceiling')
    return out,{'inputGainDb':gain,'targetFileK100Db':target_db,'sampleCeilingDb':ceiling_db,'processing':'iterative energy target with smooth-knee transient peak control'}

@lru_cache(maxsize=4)
def interp_kernel(phase):
    offsets=np.arange(-24,25,dtype=np.float64)
    h=np.sinc(offsets-phase)*np.kaiser(len(offsets),8.6)
    return h/h.sum()

def oversampled_peak(audio):
    """Four-times interpolated peak estimate using49-tap windowed sinc phases."""
    peak=float(np.max(np.abs(audio)))
    for phase in (.25,.5,.75):peak=max(peak,float(np.max(np.abs(np.convolve(audio,interp_kernel(phase),mode='same')))))
    return peak
