from pathlib import Path
from functools import lru_cache
import hashlib
import json
import math
import re
import time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, fftconvolve, butter, sosfilt
from .score import validate, VOCALS
from .voice import ROOT, SR, Singer, Cancelled
from .bank import voices as bank_voices, synthesize as bank_synthesize
from .tuning import correct as correct_pitch

CACHE=ROOT/'cache'
OUTPUT=ROOT/'renders'
STEMS=ROOT/'imports'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def section_signature(track,tempo):
    return fingerprint({'notes':track['notes'],'tempo':tempo})


def pan_mono(wav,pan):
    angle=(pan+1)*np.pi/4
    return wav[:,None]*np.array([np.cos(angle),np.sin(angle)],np.float32)


@lru_cache(maxsize=20)
def sample(path):
    wav,sr=sf.read(path,dtype='float32',always_2d=True)
    wav=wav.mean(axis=1)
    if sr!=SR:
        g=math.gcd(sr,SR);wav=resample_poly(wav,SR//g,sr//g)
    # Keep recorded attacks; only remove a very short leading digital silence.
    active=np.flatnonzero(np.abs(wav)>.0008)
    if len(active):wav=wav[max(0,int(active[0]) - int(.005*SR)):]
    peak=np.max(np.abs(wav))
    return wav/max(peak,.01)*.35


def sample_pitch(name):
    # VSCO naming uses C3 for MIDI 60 (one octave below scientific notation).
    m=re.search(r'_([A-G])(#?)(\d)_',name)
    if not m:raise ValueError('Cannot identify sample pitch: '+name)
    return (int(m[3])+2)*12+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1]]+bool(m[2])


def orchestra(track,tempo,length):
    files=list((ROOT/'assets'/track['role']).glob('*.wav'))
    if not files:raise ValueError('Orchestral samples missing. Run python setup_assets.py.')
    out=np.zeros(length,np.float32)
    for n in track['notes']:
        f=min(files,key=lambda f:abs(sample_pitch(f.name)-n['pitch']))
        src=sample(str(f));ratio=2**((n['pitch']-sample_pitch(f.name))/12)
        count=round(n['duration']*60/tempo*SR)
        positions=np.arange(count)*ratio
        # Short crossfade loop only when a note exceeds the recorded sustain.
        if len(src)>SR and positions[-1]>=len(src):
            loop_a=int(.65*SR);loop_b=int(len(src)*.8);fade=int(.08*SR)
            cross=np.linspace(0,1,fade)
            loop=src[loop_a:loop_b].copy();loop[-fade:]=loop[-fade:]*(1-cross)+loop[:fade]*cross
            extended=np.concatenate([src[:loop_b-fade],np.tile(loop[fade:],int(positions[-1]/max(1,len(loop)-fade))+2)])
            tone=np.interp(positions,np.arange(len(extended)),extended)
        else:tone=np.interp(positions,np.arange(len(src)),src,right=0)
        attack=min(int(.012*SR),count//4);release=min(int(.12*SR),count//3)
        tone[:attack]*=np.linspace(0,1,attack);tone[-release:]*=np.linspace(1,0,release)
        start=round(n['start']*60/tempo*SR);end=min(length,start+count)
        out[start:end]+=tone[:end-start]
    return pan_mono(out,track['pan'])*track['gain']


class Renderer:
    def __init__(self):
        self.singers={}
        for p in [CACHE,OUTPUT,STEMS]:p.mkdir(exist_ok=True)

    def run(self, source, progress=lambda *_:None, cancel=None):
        p=validate(source)
        tracks=[t for t in p['tracks'] if t['enabled'] and (t['notes'] or t['voice']=='imported')]
        end_seconds=[(n['start']+n['duration'])*60/p['tempo'] for t in tracks for n in t['notes']]
        for t in tracks:
            if t['voice']=='imported':
                path=STEMS/(t['stem']+'.wav')
                if not path.exists():raise ValueError(f'{t["name"]}: imported WAV is missing on this computer. Import it again.')
                info=sf.info(path);end_seconds.append(info.frames/info.samplerate)
        delay_tail=max((120/p['tempo'] if t['role'] in VOCALS and t['vox']['delay'] else 0 for t in tracks),default=0)
        length=round((max(end_seconds)+2+delay_tail)*SR)
        mix=np.zeros((length,2),np.float32)
        key=fingerprint(p);folder=OUTPUT/key[:16];folder.mkdir(exist_ok=True)
        started=time.time(); stems=[]
        steps=sum(t['singers'] if t['role'] in VOCALS and t['voice']!='imported' else 1 for t in tracks);done=0
        for t in tracks:
            if cancel and cancel.is_set():raise Cancelled()
            stem=np.zeros_like(mix)
            if t['role'] in VOCALS and t['voice']=='imported':
                if t.get('stem_score')!=section_signature(t,p['tempo']):
                    raise ValueError(f'{t["name"]}: notes or tempo changed since the WAV was imported. Re-render and import this section again.')
                path=STEMS/(t['stem']+'.wav')
                if not path.exists():raise ValueError(f'{t["name"]}: imported WAV is missing on this computer. Import it again.')
                wav,_=sf.read(path,dtype='float32',always_2d=True)
                wav=wav.mean(axis=1)
                if t['tuning']['enabled']:
                    progress('Correcting pitch · '+t['name'],done/steps)
                    ck=fingerprint({'engine':'world-tuning-v1','stem':t['stem'],'settings':t['tuning']});corrected=CACHE/(ck+'.wav')
                    if corrected.exists():wav,_=sf.read(corrected,dtype='float32')
                    else:
                        wav=correct_pitch(wav,SR,t['tuning']);sf.write(corrected,wav,SR,subtype='FLOAT')
                stereo=pan_mono(wav,t['pan'])*t['gain'];stem[:min(len(wav),length)]+=stereo[:length];done+=1
            elif t['role'] in VOCALS and t['voice'] in bank_voices():
                for index in range(t['singers']):
                    if cancel and cancel.is_set():raise Cancelled()
                    progress(f'{t["name"]} · recorded voice {index+1} of {t["singers"]}',done/steps)
                    wav=bank_synthesize(t,p['tempo'],index)
                    width=0 if t['singers']==1 else (index/(t['singers']-1)*2-1)*t['spread']
                    stereo=pan_mono(wav,float(np.clip(t['pan']+width,-1,1)))
                    offset=round((index%4)*.005*SR);amount=min(len(wav),length-offset)
                    stem[offset:offset+amount]+=stereo[:amount]*t['gain']/math.sqrt(t['singers']);done+=1
            elif t['role'] in VOCALS:
                if t['voice'] not in self.singers:
                    progress('Loading singing models',done/steps)
                    # Keep at most two acoustic models resident on typical laptops.
                    if len(self.singers)>=2:self.singers.pop(next(iter(self.singers)))
                    self.singers[t['voice']]=Singer(t['voice'])
                for index in range(t['singers']):
                    if cancel and cancel.is_set():raise Cancelled()
                    progress(f'{t["name"]} · singer {index+1} of {t["singers"]}',done/steps)
                    ck=fingerprint({'engine':'cantabile-onnx-v1-5','voice':t['voice'],'notes':t['notes'],'tempo':p['tempo'],'quality':p['quality'],'singer':index,'delivery':t['delivery'],'vox':{k:v for k,v in t['vox'].items() if k not in ('tone','grit','delay')}})
                    path=CACHE/(ck+'.wav')
                    if path.exists():wav,_=sf.read(path,dtype='float32')
                    else:
                        wav=self.singers[t['voice']].synthesize(t['notes'],p['tempo'],p['quality'],cancel,index,t['delivery'],t['vox'])
                        tmp=path.with_suffix('.tmp.wav');sf.write(tmp,wav,SR,subtype='FLOAT');tmp.replace(path)
                    width=0 if t['singers']==1 else (index/(t['singers']-1)*2-1)*t['spread']
                    stereo=pan_mono(wav,float(np.clip(t['pan']+width,-1,1)))
                    offset=round((index%4)*.003*SR)
                    amount=min(len(wav),length-offset)
                    stem[offset:offset+amount]+=stereo[:amount]*t['gain']/math.sqrt(t['singers'])
                    done+=1
            else:
                progress('Rendering '+t['name'],done/steps)
                stem=orchestra(t,p['tempo'],length);done+=1
            if t['role'] in VOCALS:
                fx=t['vox']
                if fx['tone']<0:
                    smooth=sosfilt(butter(2,2600,fs=SR,output='sos'),stem,axis=0)
                    stem=stem*(1+fx['tone'])+smooth*(-fx['tone'])
                elif fx['tone']>0:
                    bright=sosfilt(butter(2,1800,btype='highpass',fs=SR,output='sos'),stem,axis=0)
                    stem=stem+bright*fx['tone']*.8
                if fx['grit']:
                    driven=np.tanh(stem*(1+fx['grit']*12))/(1+fx['grit']*3)
                    stem=stem*(1-fx['grit'])+driven*fx['grit']
                if fx['delay']:
                    dry=stem.copy();offset=round(60/p['tempo']/2*SR)
                    for repeat in range(1,5):
                        delay=offset*repeat
                        if delay<length:stem[delay:]+=dry[:-delay]*fx['delay']*(.4**(repeat-1))
            mix+=stem
            stems.append((t['id'],stem))
        if cancel and cancel.is_set():raise Cancelled()
        progress('Mixing the hall and writing WAV files',.96)
        if p['reverb']:
            rng=np.random.default_rng(312)
            n=round(1.4*SR);time_axis=np.arange(n)/SR
            ir=rng.normal(0,1,(n,2))*np.exp(-time_axis[:,None]*5)
            ir[:int(.022*SR)]=0
            ir/=np.sqrt(np.sum(ir*ir,axis=0))
            for channel in range(2):mix[:,channel]+=fftconvolve(mix[:,channel],ir[:,channel])[:length]*p['reverb']*.55
        if not np.all(np.isfinite(mix)):raise ValueError('Render contains invalid audio samples.')
        # A quiet mix can hide loud, cancelling stems. Protect both exports.
        peak=max([float(np.max(np.abs(mix)))]+[float(np.max(np.abs(stem))) for _,stem in stems])
        gain=min(1,.94/max(.0001,peak))
        mix*=gain
        for name,stem in stems:sf.write(folder/(name+'.wav'),stem*gain,SR,subtype='PCM_24')
        sf.write(folder/'mix.wav',mix,SR,subtype='PCM_24')
        (folder/'project.json').write_text(json.dumps(p,indent=2))
        info={'id':key[:16],'duration':len(mix)/SR,'elapsed':round(time.time()-started,2),'peak':float(np.max(np.abs(mix))), 'stems':[x[0] for x in stems], 'title':p['title']}
        (folder/'render.json').write_text(json.dumps(info,indent=2));progress('Render ready',1)
        return info
