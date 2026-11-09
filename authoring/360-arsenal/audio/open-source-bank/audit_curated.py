"""Independent channel/window selection; objective checks, never listening claims."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np
from acquire_curated import FFMPEG,FFPROBE,db

ROOT=Path(__file__).resolve().parent
SELECTIONS=[
 ('handgun','ffsl_1911_near_alt',1,1.145,2.1,'single_discharge'),
 ('smg','ffsl_m45_near_alt',1,.192,1.8,'single_discharge'),
 ('semiauto','ffsl_ar15_near_alt',0,.501,2.5,'single_discharge'),
 ('automatic','ffsl_ak47_near_alt',0,.799,2.0,'single_discharge'),
 ('sniper','ffsl_mosin_near',0,1.034,2.7,'single_discharge'),
 ('shotgun','ffsl_nova_behind',1,1.481,2.7,'single_discharge'),
 ('mosin_outdoor_returns','ffsl_mosin_mid',0,2.122,2.8,'natural_returns_only'),
 ('nova_outdoor_returns','ffsl_nova_mid_actual',0,1.164,2.8,'natural_returns_only'),
]
def decode(path,channels):
    raw=subprocess.run([str(FFMPEG),'-v','error','-nostdin','-i',str(path),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype='<f4').reshape(-1,channels).astype(np.float64)
def max_run(mask):
    changes=np.diff(np.concatenate(([False],mask,[False])).astype(np.int8))
    a=np.flatnonzero(changes==1);b=np.flatnonzero(changes==-1)
    return int(max(b-a,default=0))
def main():
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    sources={r['id']:r for r in manifest['sources']};report=[];wave={};failures=[]
    tree=json.loads((ROOT/'evidence/github-tree.json').read_text());blob={r['path']:r['sha'] for r in tree['tree'] if r['type']=='blob'}
    for ident,r in sources.items():
        p=Path(r['path']);raw=p.read_bytes();actual=hashlib.sha256(raw).hexdigest()
        if actual!=r['sha256']:failures.append('SHA256 changed: '+ident)
        git_valid=None
        if 'originalPath' in r:
            h=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();git_valid=h==blob[r['originalPath']]
            if not git_valid:failures.append('Pinned git blob mismatch: '+ident)
        rate=r['technical']['sampleRate'];channels=r['technical']['channels'];x=decode(p,channels);wave[ident]=x
        per_channel=[{'channel':j,'peakDbFS':db(np.max(np.abs(c))),
          'fullScaleSampleCount':int(np.count_nonzero(np.abs(c)>=.999999)),
          'longestFullScaleRunSamples':max_run(np.abs(c)>=.999999)} for j,c in enumerate(x.T)]
        shots=[]
        if r.get('perspective') in ('near','mid','far','behind'):
            for t in r['technical']['strongestSeparated300msRms1msPeaksSeconds']:
                cut=x[max(0,round((t-.03)*rate)):min(len(x),round((t+1.5)*rate))]
                shots.append({'peakCandidateSeconds':t,'windowStartSeconds':max(0,t-.03),'windowEndSeconds':t+1.5,
                  'channels':[{'channel':j,'peakDbFS':db(np.max(np.abs(c))),'fullScaleSampleCount':int(np.sum(np.abs(c)>=.999999)),
                  'cleanAtDigitalFullScale':bool(np.max(np.abs(c))<.999999)} for j,c in enumerate(cut.T)]})
        report.append({'id':ident,'path':str(p),'sha256Verified':actual==r['sha256'],'pinnedGitBlobVerified':git_valid,
          'perChannel':per_channel,'candidateWindows':shots,'stereoWarning':r['technical']['stereoCorrelation']<0,
          'sourcePerspective':r.get('perspective'),'semanticEventCount':'not inferred from energy groups'})
    (ROOT/'curated').mkdir(exist_ok=True);selections=[]
    for name,ident,ch,t,length,role in SELECTIONS:
        r=sources[ident];rate=r['technical']['sampleRate'];x=wave[ident][:,ch]
        if role=='single_discharge':
            a=max(0,round((t-.03)*rate));b=min(len(x),round((t+.004)*rate));segment=x[a:b]
            indices=np.flatnonzero(np.abs(segment)>=np.max(np.abs(segment))*.01)
            first=a+int(indices[0]);start=max(0,first-1)
        else:start=round((t+.14)*rate)
        end=min(len(x),start+round(length*rate));cut=x[start:end]
        clipped=int(np.sum(np.abs(cut)>=.999999))
        if clipped:failures.append('Selected window contains digital full-scale samples: '+name)
        target=ROOT/'curated'/f'{name}.wav'
        filters=f'pan=mono|c0=c{ch},atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS,volume=-2dB,aresample=48000,afade=t=out:st={max(0,length-.025)}:d=0.025'
        subprocess.run([str(FFMPEG),'-y','-v','error','-nostdin','-i',r['path'],'-af',filters,'-c:a','pcm_s24le',str(target)],check=True)
        y=decode(target,1)[:,0];peak=float(np.max(np.abs(y)))
        if peak>=10**(-1/20):failures.append('Curated48k derivative lacks1dB sample headroom: '+name)
        selections.append({'name':name,'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
          'sourceId':ident,'sourceSHA256':r['sha256'],'channel':ch,'sourceStartSeconds':start/rate,'sourceEndSeconds':end/rate,
          'sourceFullScaleSampleCountInSelection':clipped,'sampleRate':48000,'channels':1,'bitsPerSample':24,
          'decodedSamplePeakDbFS':db(peak),'role':role,'operations':['one microphone channel only','trim','-2dB fixed headroom gain','resample48k','25msendfade'],
          'use':'Source reference for family sound designer; not final native event. Exactly one initiating shot in selected source range; this is based on original single-shot metadata and widely separated transient groups, not automated listening.' if role=='single_discharge' else 'Initial gunshot omitted by140ms; late natural outdoor returns donor. Engineer should audition before committing.'})
    result={'schemaVersion':1,'passed':not failures,'failures':failures,'checks':'Original hashes and pinned git blobs; per-channel fullscale samples/runs; selected mono48kPCM24 derivative peaks.',
      'sources':report,'curatedSelections':selections,
      'limitations':['No human listening performed. Spectral/energy measurements cannot establish absence of voices, music or subjective cinematic quality.',
        'Some full source tracks contain clipped takes. The curated8windows contain0digitalfullscalesamples before processing; rejected takes remain for provenance and late returns only.',
        'Raw stereo microphone pairs are often anticorrelated; derivatives use one microphone rather than phase-cancelling averages.',
        'Curated source snippets are not ready-to-install Hytale events. Runtime must keep one emission per trigger, use mono World sources and fixed firing-position tail emitters.'],
      'productionChanged':False}
    (ROOT/'source-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (ROOT/'curated-selections.json').write_text(json.dumps({'schemaVersion':1,'selections':selections},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'failures':failures,'sources':len(report),'curated':[{k:r[k] for k in ('name','sourceId','channel','sourceStartSeconds','sourceFullScaleSampleCountInSelection','decodedSamplePeakDbFS')} for r in selections]},indent=2))
if __name__=='__main__':main()
