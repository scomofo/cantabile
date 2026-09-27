"""Build an attributed multisample bank from selected original VocalSet WAVs."""
import argparse,hashlib,json,math,re,shutil
from pathlib import Path
import numpy as np
import soundfile as sf
from pitch_analysis import pitch_track,segments

ROOT=Path(__file__).resolve().parents[1]
TYPES={'f1':'soprano','f2':'soprano','f3':'soprano','f4':'soprano','f5':'mezzo-soprano','f6':'soprano','f7':'soprano','f8':'mezzo-soprano','f9':'soprano','m1':'baritone','m2':'tenor','m3':'tenor','m4':'bass (?)','m5':'baritone','m6':'baritone','m7':'tenor (?)','m8':'bass','m9':'countertenor','m10':'bass-baritone','m11':'tenor'}


def build(source,dest):
    voices={};rejected=[];provenance=[]
    paths=sorted(source.glob('FULL/*/long_tones/straight/*.wav'))+sorted(p for tech in ('vibrato','breathy','belt') for p in source.glob('FULL/*/scales/'+tech+'/*.wav'))
    for index,path in enumerate(paths):
        match=re.match(r'([fm]\d+)_',path.name)
        if not match:continue
        singer=match[1];vowel=path.stem[-1];technique=path.parent.name
        if vowel not in 'aeiou':continue
        y,sr=sf.read(path,dtype='float32',always_2d=True);y=y.mean(axis=1)
        pitches,confidence=pitch_track(y,sr);candidates=segments(pitches,confidence)
        # Favor stable sustained material while retaining pitch diversity.
        candidates.sort(key=lambda c:(c['end']-c['start'])*c['confidence'],reverse=True)
        selected=[]
        for c in candidates:
            if c['end']-c['start']<.20 or c['confidence']<.72:continue
            if any(abs(c['root']-x['root'])<1.6 for x in selected):continue
            selected.append(c)
            if len(selected)>=4:break
        if not selected:rejected.append({'source':str(path.relative_to(source)),'reason':'No sufficiently stable pitched segment'});continue
        voice=voices.setdefault(singer,dict(id='vs-'+singer,name=singer.upper()+' · '+TYPES[singer],gender='female' if singer[0]=='f' else 'male',voice_type=TYPES[singer],role='mezzo' if TYPES[singer]=='mezzo-soprano' else 'alto' if singer=='m9' else 'baritone' if singer=='m10' else TYPES[singer].split()[0],source_singer=singer,engine='sample',license='CC-BY-4.0',samples=[]))
        source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        for take,c in enumerate(sorted(selected,key=lambda c:c['root'])):
            a=round(c['start']*sr);b=min(len(y),round(min(c['end'],c['start']+2.4)*sr));clip=y[a:b].copy()
            if len(clip)<sr*.18:continue
            clip-=clip.mean();rms=float(np.sqrt(np.mean(clip**2)));peak=float(np.max(abs(clip)))
            if rms<.001 or not np.isfinite(peak):continue
            clip*=min(4,.11/rms,.8/max(.001,peak))
            fade=min(round(.008*sr),len(clip)//10);clip[:fade]*=np.linspace(0,1,fade);clip[-fade:]*=np.linspace(1,0,fade)
            # Bake a crossfade into the sustain loop; ordinary SFZ loop opcodes suffice.
            loop_a=round(len(clip)*.22);loop_b=round(len(clip)*.85);xfade=min(round(.035*sr),(loop_b-loop_a)//5)
            alpha=np.linspace(0,1,xfade);clip[loop_b-xfade:loop_b]=clip[loop_b-xfade:loop_b]*(1-alpha)+clip[loop_a:loop_a+xfade]*alpha
            loop_start=loop_a+xfade;loop_end=loop_b-1
            filename=f'samples/{singer}/{technique}_{vowel}_{round(c["root"]):02d}_{take}.wav';out=dest/filename;out.parent.mkdir(parents=True,exist_ok=True)
            sf.write(out,clip,sr,subtype='PCM_24')
            voice['samples'].append(dict(file=filename,technique=technique,vowel=vowel,root_midi=round(c['root'],5),sample_rate=sr,frames=len(clip),loop_start=loop_start,loop_end=loop_end,confidence=round(c['confidence'],4),source=str(path.relative_to(source)),source_start=round(a/sr,5),source_end=round(b/sr,5),source_sha256=source_hash,sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
        if index%20==0:print(f'Processed {index+1}/{len(paths)} recordings',flush=True)
    outvoices=[]
    for singer,voice in sorted(voices.items(),key=lambda kv:(kv[0][0],int(kv[0][1:]))):
        voice['techniques']=sorted(set(x['technique'] for x in voice['samples']))
        roots=[s['root_midi'] for s in voice['samples']];voice['sampled_range']=[round(min(roots)),round(max(roots))]
        voice['coverage']={t:sorted(set(s['vowel'] for s in voice['samples'] if s['technique']==t)) for t in voice['techniques']}
        outvoices.append(voice)
        for technique in voice['techniques']:
            lines=['// VocalSet by Wilkins, Seetharaman, Wahl & Pardo. CC BY 4.0. See ATTRIBUTION.md.','// Edited/looped by Cantabile. Vowels: MIDI 24 a, 25 e, 26 i, 27 o, 28 u.','<global> sw_lokey=24 sw_hikey=28 sw_default=24 ampeg_attack=0.015 ampeg_release=0.18']
            for vindex,vowel in enumerate('aeiou'):
                samples=sorted([s for s in voice['samples'] if s['technique']==technique and s['vowel']==vowel],key=lambda s:s['root_midi'])
                if not samples:continue
                lines.append(f'<group> sw_last={24+vindex} sw_label={vowel}')
                for i,s in enumerate(samples):
                    center=round(s['root_midi']);low=math.floor((samples[i-1]['root_midi']+s['root_midi'])/2)+1 if i else max(29,center-7)
                    high=math.floor((samples[i+1]['root_midi']+s['root_midi'])/2) if i+1<len(samples) else min(96,center+7)
                    lines.append(f'<region> sample=../{s["file"]} pitch_keycenter={center} tune={round((center-s["root_midi"])*100)} lokey={low} hikey={high} loop_mode=loop_continuous loop_start={s["loop_start"]} loop_end={s["loop_end"]}')
            p=dest/'sfz'/f'{singer}_{technique}.sfz';p.parent.mkdir(exist_ok=True);p.write_text('\n'.join(lines)+'\n')
    manifest=dict(version=1,name='Cantabile Vocal Bank 01',source_title='VocalSet: A Singing Voice Dataset',authors=['Julia Wilkins','Prem Seetharaman','Alison Wahl','Bryan Pardo'],source='https://doi.org/10.5281/zenodo.1442513',license='CC-BY-4.0',license_url='https://creativecommons.org/licenses/by/4.0/',modifications='Pitch-analyzed, excerpted, DC-corrected, level-adjusted, faded and loop-crossfaded. Source offsets and hashes accompany every sample.',voices=outvoices)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'BUILD_REPORT.json').write_text(json.dumps(dict(source_recordings=len(paths),voices=len(outvoices),samples=sum(len(v['samples']) for v in outvoices),rejected=rejected,coverage={v['id']:v['coverage'] for v in outvoices}),indent=2))
    print('DONE',len(outvoices),'voices;',sum(len(v['samples']) for v in outvoices),'samples;',len(rejected),'rejected recordings',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'.bank_sources/vocalset-raw');parser.add_argument('--output',type=Path,default=ROOT/'vocal-bank');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);build(args.source,args.output)
