import copy
import math
import re
from .bank import voices as bank_voices, vowel as bank_vowel

VOCALS = {'solo', 'soprano', 'mezzo', 'alto', 'tenor', 'baritone', 'bass'}
PARTS = VOCALS | {'violin', 'cello', 'flute', 'horn'}
RANGES = {'solo': [48,84], 'soprano': [60,84], 'mezzo': [57,81], 'alto': [53,77], 'tenor': [48,72], 'baritone': [45,69], 'bass': [40,64]}
VOX_DEFAULTS={'transpose':0,'formant':0,'vibrato':.14,'vibrato_rate':5.2,'glide':0,'accent_gain':1.65,'tone':0,'grit':0,'delay':0}
VOX_LIMITS={'transpose':(-12,12),'formant':(-5,5),'vibrato':(0,.7),'vibrato_rate':(3,9),'glide':(0,.2),'accent_gain':(1,2.5),'tone':(-1,1),'grit':(0,1),'delay':(0,.5)}


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}.')
    return value


def validate(source):
    if not isinstance(source, dict) or source.get('version') != 1:
        raise ValueError('Use a Cantabile version 1 project.')
    p = copy.deepcopy(source)
    p['title'] = str(p.get('title', 'Untitled'))[:100]
    number(p.get('tempo'), 40, 200, 'Tempo')
    number(p.get('reverb', .18), 0, .6, 'Reverb')
    p.setdefault('reverb', .18)
    if p.get('quality', 'draft') not in ('draft', 'standard'):
        raise ValueError('Quality must be draft or standard.')
    p.setdefault('quality', 'draft')
    tracks = p.get('tracks')
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 16:
        raise ValueError('A project needs 1–16 tracks.')
    ids = set()
    for t in tracks:
        if not isinstance(t, dict) or not isinstance(t.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',t['id']) or t['id'] in ids:
            raise ValueError('Track IDs must be unique letters, numbers, underscores or hyphens.')
        ids.add(t['id'])
        t.setdefault('role',t['id'])
        if t['role'] not in PARTS: raise ValueError('Unsupported section or instrument.')
        t['name'] = str(t.get('name', t['role'].title()))[:60]
        t.setdefault('singers',1); number(t['singers'],1,8,'Singer count')
        if int(t['singers']) != t['singers']: raise ValueError('Singer count must be a whole number.')
        t.setdefault('voice','hanami')
        if t['voice'] not in ('hanami','tiger','tiger-vinyl','imported') and t['voice'] not in bank_voices():raise ValueError('Choose an installed voice or an imported WAV stem.')
        if t['voice'] in bank_voices():
            t.setdefault('bank_technique','straight')
            if t['bank_technique'] not in bank_voices()[t['voice']]['techniques']:raise ValueError('Choose an available recorded vocal technique.')
        if t['voice']=='imported' and not re.fullmatch(r'[a-f0-9]{64}',str(t.get('stem',''))):raise ValueError('Import a voice WAV for this section first.')
        t.setdefault('spread',.35);number(t['spread'],0,1,'Ensemble spread')
        t.setdefault('delivery','sing')
        if t['delivery'] not in ('sing','rhythmic'):raise ValueError('Choose singing or rhythmic delivery.')
        t.setdefault('vox',{})
        from .tuning import validate as validate_tuning
        t['tuning']=validate_tuning(t.get('tuning',{}))
        if not isinstance(t['vox'],dict):raise ValueError('Voice settings must be an object.')
        for key,value in VOX_DEFAULTS.items():
            t['vox'].setdefault(key,value);number(t['vox'][key],*VOX_LIMITS[key],key)
        if int(t['vox']['transpose'])!=t['vox']['transpose']:raise ValueError('Transpose must be a whole number of semitones.')
        if 'pattern' in t:
            from .pattern import compile_pattern
            compile_pattern(t['pattern'])
        t.setdefault('enabled', True)
        if not isinstance(t['enabled'], bool):
            raise ValueError('Track enabled must be true or false.')
        number(t.get('gain', .7), 0, 1.5, 'Track level')
        number(t.get('pan', 0), -1, 1, 'Track pan')
        t.setdefault('gain', .7); t.setdefault('pan', 0)
        notes = t.get('notes')
        if not isinstance(notes, list) or len(notes) > 256:
            raise ValueError('Each track supports at most 256 notes.')
        if any(not isinstance(n,dict) for n in notes):raise ValueError('Notes must be objects with start, duration and pitch.')
        end = 0
        sung = False
        for n in sorted(notes, key=lambda n: n.get('start', -1)):
            number(n.get('start'), 0, 160, 'Note start')
            number(n.get('duration'), .03125, 32, 'Note length')
            pitch = number(n.get('pitch'), 24, 96, 'MIDI pitch')
            if int(pitch) != pitch: raise ValueError('MIDI pitch must be a whole number.')
            n['pitch']=int(pitch)
            number(pitch+t['vox']['transpose'],24,96,'Transposed pitch')
            if t['role'] in VOCALS and n['start'] < end - 1e-6:
                raise ValueError(f'{t["id"].title()} notes overlap. Put harmony on another track.')
            lyric = n.setdefault('lyric', '')
            if not isinstance(lyric, str) or len(lyric) > 60:
                raise ValueError('Each note lyric must be text under 60 characters.')
            if t['role'] in VOCALS:
                if not lyric.strip(): raise ValueError('Every vocal note needs a word, or + to continue a vowel.')
                if lyric == '+' and (not sung or abs(n['start'] - end) > 1e-6):
                    raise ValueError('A + continuation must directly follow a sung note.')
                sung = True
            if 'phonemes' in n:
                if not isinstance(n['phonemes'], str) or len(n['phonemes']) > 200:
                    raise ValueError('Phonemes must be a short space-separated string.')
            if 'accent' in n and not isinstance(n['accent'],bool):raise ValueError('Note accent must be true or false.')
            if t['voice'] in bank_voices() and lyric!='+':
                v=bank_vowel(n)
                if v not in bank_voices()[t['voice']]['coverage'][t['bank_technique']]:raise ValueError('That vowel is unavailable in this recorded technique.')
            end = max(end, n['start'] + n['duration'])
        if end * 60 / p['tempo'] > 60:
            raise ValueError('This prototype supports up to 60 seconds per project.')
        t['notes'] = sorted(notes, key=lambda n: n['start'])
    if not any(t['enabled'] and (t['notes'] or t['voice']=='imported') for t in tracks):
        raise ValueError('Enable at least one track containing notes.')
    if sum(t['singers'] for t in tracks if t['enabled'] and t['role'] in VOCALS)>32:
        raise ValueError('This prototype supports up to 32 enabled singers per render.')
    return p


def note_name(midi):
    return ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][int(midi)%12] + str(int(midi)//12-1)


def demo():
    words = 'Hold the light through the night let our song rise to the sky'.split()
    melody = [64, 67, 69, 67, 64, 62, 64, 67, 72, 71, 69, 67, 64]
    lengths = [2, 1, 3, 1, 1, 4, 1, 1, 3, 2, 1, 1, 3]
    notes=[]; beat=1
    for word,pitch,d in zip(words,melody,lengths):
        notes.append(dict(start=beat,duration=d,pitch=pitch,lyric=word));beat+=d
    tracks=[dict(id='solo',name='Solo voice',enabled=True,gain=.9,pan=0,notes=notes)]
    for part,shift,pan in [('soprano',0,-.3),('alto',-5,.3),('tenor',-12,-.15),('bass',-24,.15)]:
        tracks.append(dict(id=part,name=part.title(),enabled=False,gain=.42,pan=pan,voice='tiger' if part in ('tenor','bass') else 'hanami',notes=[{**n,'pitch':n['pitch']+shift} for n in notes]))
    for part,pitches,gain,pan in [('violin',[64,65,67,64],.28,-.4),('cello',[48,45,43,48],.48,.25),('horn',[55,57,59,55],.22,.1),('flute',[76,77,79,76],.15,-.2)]:
        tracks.append(dict(id=part,name=part.title(),enabled=True,gain=gain,pan=pan,notes=[dict(start=i*7,duration=7,pitch=pitch,lyric='') for i,pitch in enumerate(pitches)]))
    return validate(dict(version=1,title='Hold the Light',tempo=88,reverb=.18,quality='draft',tracks=tracks))
