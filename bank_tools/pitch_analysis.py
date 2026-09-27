import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,medfilt
from pathlib import Path
import math

def pitch_track(wav,sr):
    g=math.gcd(sr,16000);y=resample_poly(wav,16000//g,sr//g);size=2048;hop=160;minimum=11;maximum=320
    gate=max(.001,float(np.sqrt(np.mean(y*y)))*.12);out=[];confidence=[]
    for start in range(0,len(y)-size,hop):
        x=y[start:start+size].astype(float);x-=x.mean()
        if np.sqrt(np.mean(x*x))<gate:out.append(0);confidence.append(0);continue
        spec=np.fft.rfft(x,2*size);acf=np.fft.irfft(spec*spec.conj())[:maximum+1]
        cumulative=np.r_[0,np.cumsum(x*x)];lags=np.arange(maximum+1)
        diff=np.maximum(0,cumulative[size-lags]+cumulative[size]-cumulative[lags]-2*acf)
        cmnd=np.ones(maximum+1);cmnd[1:]=diff[1:]*lags[1:]/np.maximum(np.cumsum(diff[1:]),1e-12)
        under=np.flatnonzero(cmnd[minimum:]<.15);lag=int(under[0]+minimum) if len(under) else int(np.argmin(cmnd[minimum:])+minimum)
        while lag<maximum and cmnd[lag+1]<cmnd[lag]:lag+=1
        if cmnd[lag]>.35 or lag>=maximum:out.append(0);confidence.append(0);continue
        a,b,c=cmnd[lag-1:lag+2];delta=.5*(a-c)/max(1e-12,a-2*b+c)
        hz=16000/(lag+np.clip(delta,-.5,.5));pitch=69+12*np.log2(hz/440)
        out.append(pitch if 32<=pitch<=92 else 0);confidence.append(1-cmnd[lag])
    return np.array(out),np.array(confidence)

def segments(pitches,confidence):
    labels=medfilt(np.round(pitches),9);out=[];a=0
    for b in range(1,len(labels)+1):
        if b<len(labels) and labels[b]==labels[a]:continue
        valid=pitches[a:b]>0
        if labels[a] and (b-a)*.01>=.23 and valid.mean()>.9:
            vals=pitches[a:b][valid];root=np.median(vals);mad=np.median(abs(vals-root))
            if mad<.55:
                out.append(dict(start=a*.01+.08,end=b*.01+.045,root=float(root),confidence=float(np.median(confidence[a:b])),mad=float(mad)))
        a=b
    return out

if __name__=='__main__':
    for p in Path('research/vocalset-raw').rglob('*.wav'):
        if p.name not in ('f1_long_straight_a.wav','m8_long_straight_a.wav','f1_scales_vibrato_a.wav','m1_scales_belt_a.wav'):continue
        y,sr=sf.read(p);pit,conf=pitch_track(y,sr);print(p.name,'duration',len(y)/sr,'segments',segments(pit,conf),flush=True)
