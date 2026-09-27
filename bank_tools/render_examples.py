import copy,json,shutil,sys
from pathlib import Path
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cantabile.bank import voices,baseline,synthesize,ROOT as BANK
from cantabile.render import Renderer,OUTPUT
from cantabile.score import validate
from cantabile.tuning import correct,DEFAULTS
ROOT=Path(__file__).resolve().parents[1]
renderer=Renderer();tour=[];tourmap=[];cursor=0
(BANK/'previews').mkdir(exist_ok=True);(BANK/'baselines').mkdir(exist_ok=True)
for voice in voices():
    base=baseline(voice);track={'id':voice,**copy.deepcopy(base),'baseline':copy.deepcopy(base)}
    p=validate(dict(version=1,title=voices()[voice]['name']+' — neutral baseline',tempo=100,reverb=0,quality='draft',tracks=[track]))
    r=renderer.run(p);shutil.copy2(OUTPUT/r['id']/'mix.wav',BANK/'previews'/f'{voice}.wav')
    (BANK/'baselines'/f'{voice}.json').write_text(json.dumps(p,indent=2))
    audio,sr=sf.read(BANK/'previews'/f'{voice}.wav');clip=audio[:round(1.2*sr)];tour.append(clip);tour.append(np.zeros((round(.3*sr),2)))
    tourmap.append({'voice':voice,'name':voices()[voice]['name'],'start_seconds':round(cursor,2),'end_seconds':round(cursor+1.2,2)});cursor+=1.5
    print('Baseline rendered',voice,flush=True)
sf.write(BANK/'Voice_Tour.wav',np.concatenate(tour),44100,subtype='PCM_24');(BANK/'Voice_Tour_Timing.json').write_text(json.dumps(tourmap,indent=2))

tracks=[]
for i,(voice,role,name,pitches) in enumerate([('vs-f1','soprano','Soprano F1',[72,72,74,72]),('vs-f5','alto','Alto F5',[64,65,62,64]),('vs-f8','mezzo','Mezzo F8',[67,69,67,67]),('vs-m2','tenor','Tenor M2',[60,60,59,60]),('vs-m1','baritone','Baritone M1',[55,57,55,55]),('vs-m8','bass','Bass M8',[48,53,55,48])]):
    b=baseline(voice);b.update(id=voice,role=role,name=name,pan=(i-2.5)*.16,gain=.52,notes=[dict(start=j*4,duration=3.8,pitch=pitch,lyric=['a','o','u','a'][j]) for j,pitch in enumerate(pitches)])
    b['baseline']=copy.deepcopy({k:v for k,v in b.items() if k!='id'});tracks.append(b)
p=validate(dict(version=1,title='Six Human Voices — Recorded Choir',tempo=84,reverb=.22,quality='draft',tracks=tracks));(ROOT/'examples/recorded-choir.json').write_text(json.dumps(p,indent=2))
r=renderer.run(p);shutil.copy2(OUTPUT/r['id']/'mix.wav',ROOT/'examples/audio/recorded-choir.wav');shutil.copy2(OUTPUT/r['id']/'mix.wav',ROOT.parent/'Cantabile_Recorded_Choir_Demo.wav')
# Four independent male singers, a neutral quartet arrangement for further tuning.
quartet=[]
for voice,role,name,pitches in [('vs-m2','tenor','Tenor',[67,69,71,67]),('vs-m11','tenor','Lead',[60,60,62,60]),('vs-m1','baritone','Baritone',[52,53,55,52]),('vs-m8','bass','Bass',[48,53,55,48])]:
    t=baseline(voice);t.update(id=voice,role=role,name=name,gain=.6,notes=[dict(start=j*4,duration=3.8,pitch=n,lyric='a') for j,n in enumerate(pitches)]);quartet.append(t)
p=validate(dict(version=1,title='Barbershop Starting Quartet — Vowels',tempo=90,reverb=.04,tracks=quartet));(ROOT/'examples/barbershop-start.json').write_text(json.dumps(p,indent=2))
# Actual sampled vocal input deliberately shifted +35 cents for the tuning demo.
t={'id':'input',**baseline('vs-m1')};t['notes']=[dict(start=i*2,duration=1.8,pitch=n+.35,lyric=v) for i,(n,v) in enumerate([(55,'a'),(57,'o'),(59,'u')])]
source=synthesize(t,100);hard=correct(source,44100,{**DEFAULTS,'enabled':True,'scale':'major','speed_ms':0});gentle=correct(source,44100,{**DEFAULTS,'enabled':True,'scale':'major','strength':.65,'speed_ms':100})
for name,audio in [('pitch-input-detuned',source),('pitch-corrected-gentle',gentle),('pitch-corrected-hard',hard)]:sf.write(ROOT/'examples/audio'/f'{name}.wav',audio,44100,subtype='PCM_24')
pause=np.zeros(round(.6*44100));comparison=np.concatenate([source,pause,gentle,pause,hard]);sf.write(ROOT.parent/'Cantabile_Pitch_Correction_Demo.wav',comparison,44100,subtype='PCM_24')
print('Rendered choir and pitch-correction comparison; order: original, gentle, hard.',flush=True)
