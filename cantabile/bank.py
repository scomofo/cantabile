"""Recorded VocalSet bank: actual singers, pitched vowels, editable baselines."""
from functools import lru_cache
from pathlib import Path
import json,math
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]/'vocal-bank'
VOWELS={'a':'a','ah':'a','aa':'a','e':'e','eh':'e','i':'i','ee':'i','iy':'i','o':'o','oh':'o','ow':'o','u':'u','oo':'u','uw':'u'}

@lru_cache(maxsize=1)
def voices():
    path=ROOT/'manifest.json'
    return {v['id']:v for v in json.loads(path.read_text())['voices']} if path.exists() else {}

def public_voices():
    return [{k:v for k,v in voice.items() if k!='samples'} for voice in voices().values()]

def vowel(note):
    value=(note.get('phonemes') or note['lyric']).strip().lower()
    if value not in VOWELS:raise ValueError('Recorded voices sing a/ah, e/eh, i/ee, o/oh or u/oo. Choose a neural voice for words or consonant sequences.')
    return VOWELS[value]

def baseline(voice_id):
    from .score import VOX_DEFAULTS,RANGES
    sampled=voice_id in voices()
    if sampled:
        voice=voices()[voice_id];technique='straight' if 'straight' in voice['techniques'] else voice['techniques'][0]
        notes=[];available=voice['coverage'][technique]
        center=sum(RANGES[voice['role']])/2
        for i,v in enumerate(available):
            nearest=min((s for s in voice['samples'] if s['technique']==technique and s['vowel']==v),key=lambda s:abs(s['root_midi']-center))
            notes.append(dict(start=i*2,duration=1.6,pitch=round(nearest['root_midi']),lyric=v))
        role=voice['role'];name=voice['name']
    else:
        if voice_id not in ('hanami','tiger','tiger-vinyl'):raise ValueError('Choose a synthesized or sampled voice for a baseline.')
        technique='straight';base=64 if voice_id=='hanami' else 52;role='soprano' if voice_id=='hanami' else 'baritone';name='Hanami' if voice_id=='hanami' else 'TIGER'
        notes=[dict(start=i*2,duration=1.6,pitch=base+shift,lyric=word) for i,(word,shift) in enumerate(zip('let the music rise high'.split(),[0,3,5,3,0]))]
    return dict(voice=voice_id,name=name,role=role,singers=1,spread=.35,gain=.7,pan=0,delivery='sing',vox={**VOX_DEFAULTS,'vibrato':0,'grit':0,'delay':0,'tone':0},bank_technique=technique,notes=notes)

@lru_cache(maxsize=80)
def read_sample(relative):
    y,sr=sf.read(ROOT/relative,dtype='float32');return y,sr

def synthesize(track,tempo,singer_index=0):
    voice=voices()[track['voice']];technique=track.get('bank_technique','straight');sec=60/tempo;sr=44100
    notes=track['notes'];length=round((max(n['start']+n['duration'] for n in notes)*sec+.3)*sr);out=np.zeros(length,np.float32)
    groups=[]
    for note in notes:
        if note['lyric']=='+':groups[-1].append(note)
        else:groups.append([note])
    for group in groups:
        v=vowel(group[0]);pool=[s for s in voice['samples'] if s['technique']==technique and s['vowel']==v]
        if not pool:raise ValueError(f'{voice["name"]}: vowel {v} is unavailable in {technique}; choose another technique.')
        target=float(np.median([n['pitch'] for n in group]))+track['vox']['transpose']
        item=min(pool,key=lambda s:abs(s['root_midi']-target));src,source_sr=read_sample(item['file'])
        start=round(group[0]['start']*sec*sr);end=round((group[-1]['start']+group[-1]['duration'])*sec*sr)
        contour=np.zeros(end-start);envelope=np.ones(end-start);prev=None
        for n in group:
            a=round(n['start']*sec*sr)-start;b=round((n['start']+n['duration'])*sec*sr)-start
            pitch=n['pitch']+track['vox']['transpose'];contour[a:b]=pitch
            if prev and track['vox']['glide']:
                count=min(b-a,round(track['vox']['glide']*sr));contour[a:a+count]=np.linspace(prev+track['vox']['transpose'],pitch,count)
            if n.get('accent'):envelope[a:b]*=track['vox']['accent_gain']
            prev=n['pitch']
        # Recorded technique remains audible; the vibrato control adds modulation.
        times=np.arange(end-start)/sr
        depth=track['vox']['vibrato'] if track['delivery']=='sing' else 0
        contour+=depth*np.sin(2*np.pi*track['vox']['vibrato_rate']*times)*np.minimum(1,times/.25)
        contour+=.025*np.sin(singer_index*2.4)
        increments=2**((contour-item['root_midi'])/12)*(source_sr/sr)
        positions=np.r_[0,np.cumsum(increments[:-1])]
        a=item['loop_start'];b=item['loop_end']+1;period=b-a
        positions=np.where(positions>=b,a+(positions-b)%period,positions)
        # Append loop-start value for interpolation at the final loop sample.
        indices=np.arange(b+1);cyclic=np.r_[src[:b],src[a]]
        tone=np.interp(positions,indices,cyclic)*envelope
        fade=min(round(.018*sr),len(tone)//4);release=min(round(.09*sr),len(tone)//3)
        if fade:tone[:fade]*=np.linspace(0,1,fade)
        if release:tone[-release:]*=np.linspace(1,0,release)
        out[start:end]+=tone
    return out
