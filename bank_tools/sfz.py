"""Write portable SFZ key-switched vowel patches from bank metadata."""
import math

def write(voices,dest):
    folder=dest/'sfz';folder.mkdir(exist_ok=True)
    expected={f'{v["source_singer"]}_{t}.sfz' for v in voices for t in v['techniques']}
    # Remove generated patches whose last usable sample was rejected by the gate.
    for voice in voices:
        for technique in ('straight','vibrato','breathy','belt'):
            old=folder/f'{voice["source_singer"]}_{technique}.sfz'
            if old.name not in expected:old.unlink(missing_ok=True)
    for voice in voices:
        singer=voice['source_singer']
        for technique in voice['techniques']:
            lines=['// VocalSet by Wilkins, Seetharaman, Wahl & Pardo. CC BY 4.0. See ATTRIBUTION.md.','// Edited/looped by Cantabile. Select vowel: MIDI 24 a, 25 e, 26 i, 27 o, 28 u.','<global> sw_lokey=24 sw_hikey=28 sw_default=24 ampeg_attack=0.015 ampeg_release=0.18']
            for vindex,vowel in enumerate('aeiou'):
                samples=sorted([s for s in voice['samples'] if s['technique']==technique and s['vowel']==vowel],key=lambda s:s['root_midi'])
                if not samples:continue
                lines.append(f'<group> sw_last={24+vindex} sw_label={vowel}')
                for i,s in enumerate(samples):
                    center=round(s['root_midi']);low=math.floor((samples[i-1]['root_midi']+s['root_midi'])/2)+1 if i else max(29,center-7)
                    high=math.floor((samples[i+1]['root_midi']+s['root_midi'])/2) if i+1<len(samples) else min(96,center+7)
                    lines.append(f'<region> sample=../{s["file"]} pitch_keycenter={center} tune={round((center-s["root_midi"])*100)} lokey={low} hikey={high} loop_mode=loop_continuous loop_start={s["loop_start"]} loop_end={s["loop_end"]}')
            (folder/f'{singer}_{technique}.sfz').write_text('\n'.join(lines)+'\n')
