"""Download a small pinned CC0 field-recording bank; never edits game assets.

Network access is limited to public creator pages and a public CC0 mirror.
Original source bytes are retained; all processing belongs in derivative trees.
"""
from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib, json, subprocess, urllib.parse, urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parent
FFMPEG=Path(os.environ.get('FFMPEG', 'ffmpeg'))
FFPROBE=Path(os.environ.get('FFPROBE', 'ffprobe'))
REPO='https://raw.githubusercontent.com/buddingmonkey/FreeFirearmsSFXLibrary/'
PIN='beb2f4041f3d6740fa0aeaf0e71159bd65a78c1b'
PRIMARY='https://www.kickstarter.com/projects/bjjaszcz/the-firearm-sound-library/faqs'
RECORDISTS=['Ben Jaszczak','Brian Nelson','Kevin Heras','Matthew Nanney']
GUNS=[
 ('ffsl_1911_near','1911','A_42','handgun','near','1911 .45 handgun'),
 ('ffsl_ak47_near','AK-47','C_28','automatic','near','AK-47 7.62x39 rifle'),
 ('ffsl_ar15_near','AR-15','D_32','semiauto','near','AR-15 5.56x45 rifle'),
 ('ffsl_m45_near','Carl Gustav M45_Swedish K','G_31','smg','near','Carl Gustav M45 9mm submachine gun'),
 ('ffsl_mosin_near','Mosin Nagant','M_21','sniper','near','Mosin Nagant 7.62x54 rifle'),
 ('ffsl_nova_near','Nova','O_21','shotgun','near','Benelli Nova 12 gauge shotgun'),
 ('ffsl_mosin_mid','Mosin Nagant','M_26','sniper','mid','Mosin Nagant natural mid-distance report'),
 ('ffsl_nova_mid','Nova','O_17','shotgun','far','Benelli Nova far-distance report (historical bank id says mid; original Master Sheet identifies far)'),
 ('ffsl_1911_near_alt','1911','A_41','handgun','near','1911 alternate near-distance take'),
 ('ffsl_ak47_near_alt','AK-47','C_25','automatic','near','AK-47 alternate near-distance single shots'),
 ('ffsl_ar15_near_alt','AR-15','D_31','semiauto','near','AR-15 alternate near-distance single shots'),
 ('ffsl_cd_shotgun_near','Charles Daly','H_21','shotgun','near','Charles Daly 12 gauge near-distance single shots'),
 ('ffsl_mossberg_near','Mossberg','N_30','shotgun','near','Mossberg 12 gauge near-distance single shots'),
 ('ffsl_winchester12_near','Model 12','K_22','shotgun','near','Winchester Model12 12 gauge near-distance single shots'),
 ('ffsl_1911_mag_seat','1911','A_4','handgun','mechanism','1911 loaded magazine insertion'),
 ('ffsl_1911_rack','1911','A_24','handgun','mechanism','1911 full slide rack'),
 ('ffsl_ak47_cycle','AK-47','C_14','automatic','mechanism','AK-47 full action cycle with empty magazine'),
 ('ffsl_nova_pump','Nova','O_6','shotgun','mechanism','Benelli Nova full pump cycle with loaded magazine'),
 ('ffsl_mosin_bolt','Mosin Nagant','M_14','sniper','mechanism','Mosin Nagant full bolt cycle with loaded magazine'),
 ('ffsl_m45_near_alt','Carl Gustav M45_Swedish K','G_25','smg','near','Carl Gustav M45 alternate near-distance single shots'),
 ('ffsl_nova_near_alt','Nova','O_19','shotgun','near','Benelli Nova alternate near-distance single shots'),
 ('ffsl_nova_mid_actual','Nova','O_16','shotgun','mid','Benelli Nova mid-distance single-shot outdoor-tail donor'),
 ('ffsl_nova_behind','Nova','O_18','shotgun','behind','Benelli Nova single shots recorded behind shooter'),
 ('ffsl_nova_behind_alt','Nova','O_20','shotgun','behind','Benelli Nova alternate single shots recorded behind shooter'),
]
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (360-No-Scope CC0 source acquisition)'}),timeout=90).read()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def db(n):return round(float(20*np.log10(max(float(n),1e-15))),5)
def measure(path):
    probe=json.loads(subprocess.run([str(FFPROBE),'-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,check=True).stdout)
    stream=probe['streams'][0];rate=int(stream['sample_rate']);channels=int(stream['channels'])
    decoded=subprocess.run([str(FFMPEG),'-v','error','-nostdin','-i',str(path),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    x=np.frombuffer(decoded,dtype='<f4').reshape(-1,channels).astype(np.float64)
    mono=np.mean(x,axis=1);hop=max(1,rate//1000);n=len(mono)//hop
    env=np.sqrt(np.mean(mono[:n*hop].reshape(n,hop)**2,axis=1))
    peak=float(np.max(np.abs(x)));threshold=max(float(np.max(env))*.1,1e-5)
    candidates=[];last=-500
    for i in np.argsort(env)[::-1]:
        i=int(i)
        if env[i]<threshold:break
        if all(abs(i-j)>=300 for j in candidates):candidates.append(i)
        if len(candidates)>=10:break
    candidates.sort()
    onset=np.flatnonzero(env>=max(float(np.max(env))*.01,1e-5))
    corr=float(np.corrcoef(x.T)[0,1]) if channels==2 else 1.
    return {'codec':stream['codec_name'],'sampleRate':rate,'channels':channels,'bitsPerSample':stream.get('bits_per_sample'),
      'durationSeconds':len(x)/rate,'samplePeakDbFS':db(peak),'fullScaleSampleCount':int(np.count_nonzero(np.abs(x)>=.999969)),
      'monoPeakDbFS':db(np.max(np.abs(mono))),'stereoCorrelation':corr,
      'monoRmsLossAgainstMeanChannelEnergyDb':db(np.sqrt(np.mean(mono**2))/max(np.sqrt(np.mean(x**2)),1e-15)),
      'firstRelativeMinus40DbOnsetSeconds':int(onset[0])/1000 if len(onset) else None,
      'strongestSeparated300msRms1msPeaksSeconds':[i/1000 for i in candidates],
      'metadata':probe.get('format',{}).get('tags',{}),
      'measurementCaveat':'Peak groups are editing candidates, not semantic gunshot counts; listening and individual-shot selection remain required.'}
def main():
    for d in ('masters','evidence'): (ROOT/d).mkdir(exist_ok=True)
    commit=PIN
    print('Pinned mirror commit:',commit,flush=True)
    jobs=[]
    for ident,folder,stem,family,perspective,description in GUNS:
        rel=f'Master Tracks/{folder}/{stem}.wav'
        jobs.append({'id':ident,'filename':ident+'.wav','downloadUrl':REPO+commit+'/'+urllib.parse.quote(rel),
          'sourceUrl':PRIMARY,'mirrorUrl':'https://github.com/buddingmonkey/FreeFirearmsSFXLibrary','mirrorCommit':commit,
          'originalPath':rel,'description':description,'creator':RECORDISTS,'license':'CC0-1.0',
          'licenseUrl':'https://creativecommons.org/publicdomain/zero/1.0/','licenseEvidence':['evidence/firearm-CC0-LICENSE.txt','evidence/primary-license-verification.json'],
          'perspective':perspective,'suggestedFamilies':[family],
          'role':{'near':'authentic_single_discharge_and_tail_donor','behind':'authentic_single_discharge_and_tail_donor','mid':'natural_outdoor_tail_donor_remove_initial_discharge','far':'natural_outdoor_tail_donor_remove_initial_discharge','mechanism':'authentic_gun_handling_select_one_action'}[perspective]})
    for ident,num,title,page in [
      ('sardin_pneumatic_excavator','3125','Pneumatic mini-excavator jackhammer','https://bigsoundbank.com/pneumatic-jackhammer-1-s3125.html'),
      ('sardin_aluminum_workshop','0503','Aluminum powder-coating workshop handling and impacts','https://bigsoundbank.com/atelier-industrie-s0503.html')]:
        jobs.append({'id':ident,'filename':ident+'.wav','downloadUrl':f'https://bigsoundbank.com/UPLOAD/bwf-en/{num}.wav',
          'sourceUrl':page,'description':title,'creator':['Joseph SARDIN'],'license':'CC0-1.0','licenseUrl':'https://bigsoundbank.com/licenses.html',
          'licenseEvidence':[f'evidence/bigsoundbank-{int(num)}.html','evidence/bigsoundbank-license.html'],
          'suggestedFamilies':['handgun','smg','semiauto','automatic','shotgun','sniper'],
          'role':'physical_mechanism_layer_only_extract_isolated_hits_not_continuous_machine_bed'})
    def run(row):
        path=ROOT/'masters'/row['filename']
        if not path.exists():
            data=get(row['downloadUrl']);assert data[:4] in (b'RIFF',b'RF64'),(row['id'],'not WAV')
            path.write_bytes(data)
        data=path.read_bytes();row.update(path=str(path),sha256=sha(data),bytes=len(data),technical=measure(path))
        print(row['id'],row['bytes'],row['technical']['durationSeconds'],row['technical']['samplePeakDbFS'],flush=True)
        return row
    def safe_run(row):
        try:return run(row)
        except Exception as exc:
            print('FAILED',row['id'],str(exc),flush=True)
            row['downloadError']=str(exc);return row
    with ThreadPoolExecutor(max_workers=4) as pool:sources=list(pool.map(safe_run,jobs))
    evidence={'verifiedDate':'2026-11-09','firearmPrimaryLicense':{'url':PRIMARY,
      'verification':'Official creator Kickstarter FAQ states the library is released using the CC0 public-domain dedication, with no purchase, royalties or mandatory credit. Verified through browser search/open; direct automated HTML request returned403.',
      'creator':'Ben Jaszczak','originalRecordingTeam':RECORDISTS},
      'industrialPrimaryLicense':{'url':'https://bigsoundbank.com/licenses.html','verification':'Creator explicitly offers CC0 1.0, adaptation, commercial use and redistribution without restrictions. Original individual pages identify Joseph Sardin and recording equipment.'}}
    (ROOT/'evidence/primary-license-verification.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    manifest={'schemaVersion':1,'status':'curated authentic CC0 sources staged; not a final mixed game bank','mirrorCommit':commit,
      'sources':sources,'productionChanged':False,'sourceBytesPreserved':True,
      'requiredProcessing':['Select exactly one initiating discharge for each native trigger. Raw takes may contain multiple shots/handling; do not ship whole source tracks as Fire.',
        'Remote World events require a mono derivative; stereo source width must not encode the shooter direction.',
        'Tail donors include a real initiating report which must be removed; use only later natural returns in separate fixed-world-position emitters.',
        'Do not assume machine noise is a clean isolated mechanism; crop impacts and reject wind/voice/bed during listening.'],
      'recommendedCredits':'Original firearm field recordings: Ben Jaszczak, Brian Nelson, Kevin Heras and Matthew Nanney (Free Firearm Sound Library, CC0). Industrial field recordings: Joseph SARDIN / BigSoundBank.com (CC0).',
      'limitations':'Objective format, identity and signal checks do not prove absence of voices, music, unwanted second shots or subjective cinematic quality.'}
    temp=ROOT/'source-manifest.tmp.json';temp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');temp.replace(ROOT/'source-manifest.json')
    print('COMPLETE',len([r for r in sources if 'bytes' in r]),'files',sum(r.get('bytes',0) for r in sources),'bytes',flush=True)
if __name__=='__main__':main()
