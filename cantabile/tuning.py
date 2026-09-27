"""Offline monophonic pitch correction; never overwrites the input recording."""
import math
import numpy as np
from scipy.ndimage import gaussian_filter1d,median_filter

DEFAULTS={'enabled':False,'key':0,'scale':'chromatic','strength':1,'speed_ms':35,'wet':1}
SCALES={'chromatic':list(range(12)),'major':[0,2,4,5,7,9,11],'minor':[0,2,3,5,7,8,10],'major-pentatonic':[0,2,4,7,9],'minor-pentatonic':[0,3,5,7,10]}


def validate(settings):
    from .score import number
    if not isinstance(settings,dict):raise ValueError('Pitch correction settings must be an object.')
    result={**DEFAULTS,**settings}
    if not isinstance(result['enabled'],bool):raise ValueError('Pitch correction enabled must be true or false.')
    number(result['key'],0,11,'Pitch correction key')
    if int(result['key'])!=result['key']:raise ValueError('Key must be a whole-number pitch class.')
    if result['scale'] not in SCALES:raise ValueError('Choose a supported correction scale.')
    number(result['strength'],0,1,'Correction strength');number(result['speed_ms'],0,250,'Retune speed');number(result['wet'],0,1,'Correction mix')
    return result


def target_f0(f0,settings,frame_ms=5):
    settings=validate(settings);voiced=f0>0;out=np.zeros_like(f0);valid=np.flatnonzero(voiced)
    if not len(valid):return out
    midi=69+12*np.log2(f0[valid]/440)
    permitted=np.array([n for n in range(20,109) if (n-settings['key'])%12 in SCALES[settings['scale']]])
    targets=permitted[np.argmin(abs(midi[:,None]-permitted[None,:]),axis=1)]
    correction=(targets-midi)*settings['strength'];alpha=0 if settings['speed_ms']==0 else math.exp(-frame_ms/settings['speed_ms'])
    last=None;previous=0
    for j,index in enumerate(valid):
        if last is None or index!=last+1:previous=0
        previous=alpha*previous+(1-alpha)*correction[j];out[index]=440*2**((midi[j]+previous-69)/12);last=index
    return out


def correct(wav,sr,settings):
    settings=validate(settings)
    original=np.asarray(wav,dtype=np.float64)
    if not settings['enabled'] or not settings['wet'] or not settings['strength']:return original.astype(np.float32)
    try:import pyworld as pw
    except ImportError:raise ValueError('Pitch correction needs PyWORLD. Run setup-windows.bat or install requirements.txt.')
    if original.ndim!=1 or sr<16000 or len(original)<sr*.2:raise ValueError('Pitch correction needs a mono vocal longer than 0.2 seconds at 16 kHz or higher.')
    x=np.ascontiguousarray(original-original.mean(),dtype=np.float64)
    f0,times=pw.dio(x,sr,f0_floor=50,f0_ceil=1100,frame_period=5,speed=2)
    f0=pw.stonemask(x,f0,times,sr)
    if np.count_nonzero(f0)<10:raise ValueError('No stable voiced pitch found for correction. Use an isolated sung vocal, or turn correction off.')
    sp=pw.cheaptrick(x,f0,times,sr);ap=pw.d4c(x,f0,times,sr)
    target=target_f0(f0,settings)
    synthesized=pw.synthesize(target,sp,ap,sr,5)
    synthesized=np.pad(synthesized,(0,max(0,len(x)-len(synthesized))))[:len(x)]
    # Keep unvoiced consonants and breaths from the original; crossfade boundaries.
    mask=np.interp(np.arange(len(x))/sr,times,(f0>0).astype(float))
    mask=gaussian_filter1d(mask,sr*.004)*settings['wet']
    result=original*(1-mask)+synthesized*mask
    if not np.all(np.isfinite(result)):raise ValueError('Pitch correction produced invalid audio.')
    return result.astype(np.float32)
