"""Monophonic guide transcription. Lyrics are entered separately."""
import io
import math
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, medfilt


def melody_from_wav(raw,tempo):
    info=sf.info(io.BytesIO(raw))
    if info.frames/info.samplerate>60 or info.channels>2:raise ValueError('Record one voice for at most 60 seconds.')
    wav,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True)
    wav=wav.mean(axis=1)
    if not len(wav) or not np.all(np.isfinite(wav)):raise ValueError('Recording is empty or invalid.')
    g=math.gcd(sr,16000);wav=resample_poly(wav,16000//g,sr//g)
    size=1024;hop=160;minimum=16;maximum=246
    if len(wav)<size:raise ValueError('Sing or hum for at least a second.')
    gate=max(.003,float(np.sqrt(np.mean(wav**2)))*.18)
    pitches=[]
    for start in range(0,len(wav)-size,hop):
        x=wav[start:start+size].astype(np.float64);x-=x.mean()
        if np.sqrt(np.mean(x*x))<gate:pitches.append(0);continue
        spec=np.fft.rfft(x,2*size);acf=np.fft.irfft(spec*spec.conj())[:maximum+1]
        cumulative=np.concatenate([[0],np.cumsum(x*x)])
        lags=np.arange(maximum+1)
        difference=cumulative[size-lags]+cumulative[size]-cumulative[lags]-2*acf
        cmnd=np.ones(maximum+1);cmnd[1:]=difference[1:]*lags[1:]/np.maximum(np.cumsum(difference[1:]),1e-12)
        under=np.flatnonzero(cmnd[minimum:]<.18)
        lag=int(under[0]+minimum) if len(under) else int(np.argmin(cmnd[minimum:])+minimum)
        while lag<maximum and cmnd[lag+1]<cmnd[lag]:lag+=1
        if cmnd[lag]>.32:pitches.append(0);continue
        pitch=round(69+12*np.log2((16000/lag)/440))
        pitches.append(pitch if 36<=pitch<=90 else 0)
    pitches=medfilt(np.array(pitches),5)
    notes=[];a=0
    for b in range(1,len(pitches)+1):
        if b<len(pitches) and pitches[b]==pitches[a]:continue
        if pitches[a] and (b-a)*.01>=.10:
            start=max(0,round(a*.01*tempo/60*4)/4)
            end=max(start+.25,round(b*.01*tempo/60*4)/4)
            if notes and start<notes[-1]['start']+notes[-1]['duration']:start=notes[-1]['start']+notes[-1]['duration']
            if end>start:notes.append({'start':start,'duration':end-start,'pitch':int(pitches[a]),'lyric':'ah'})
        a=b
    if not notes:raise ValueError('No stable melody found. Try humming one note at a time in a quiet room.')
    first=notes[0]['start']
    for n in notes:n['start']-=first
    return {'notes':notes,'message':'Guide melody detected. Check pitches and timing, then assign your lyrics.'}
