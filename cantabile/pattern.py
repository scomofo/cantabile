"""Compile a 16-step syllable pattern into the existing vocal score format."""
from .score import number

PHONES=set('aa ae ah ao aw ay eh er ey ih iy ow oy uh uw b ch d dh f g hh jh k l m n ng p r s sh t th v w y z zh'.split())


def compile_pattern(pattern):
    if not isinstance(pattern,dict):raise ValueError('Vocal pattern must be an object.')
    cells=pattern.get('cells')
    if not isinstance(cells,list) or len(cells)!=16:raise ValueError('A vocal pattern needs exactly 16 steps.')
    division=number(pattern.get('division',.25),.25,.5,'Step division')
    if division not in (.25,.5):raise ValueError('Choose eighth or sixteenth notes.')
    swing=number(pattern.get('swing',0),0,.6,'Swing')
    start=number(pattern.get('start',0),0,120,'Pattern start')
    repeats=number(pattern.get('repeats',1),1,4,'Pattern repeats')
    if int(repeats)!=repeats:raise ValueError('Repeats must be a whole number.')
    notes=[]
    for index in range(16*int(repeats)):
        cell=cells[index%16]
        if not isinstance(cell,dict):raise ValueError('Every pattern step must be an object.')
        if not isinstance(cell.get('on',False),bool):raise ValueError('Step enabled must be true or false.')
        if not cell.get('on'):continue
        pitch=number(cell.get('pitch',60),24,96,'Step pitch')
        if int(pitch)!=pitch:raise ValueError('Step pitch must be a MIDI whole number.')
        gate=number(cell.get('gate',.85),.4,1,'Vowel gate')
        if not isinstance(cell.get('accent',False),bool) or not isinstance(cell.get('tie',False),bool):raise ValueError('Accent and tie must be true or false.')
        a=start+index*division+(swing*division if index%2 else 0)
        b=start+(index+1)*division+(swing*division if (index+1)%2 else 0)
        tie=cell.get('tie',False)
        ratchet=number(cell.get('ratchet',1),1,4,'Step repeats')
        if int(ratchet)!=ratchet:raise ValueError('Step repeats must be a whole number.')
        if tie and ratchet!=1:raise ValueError('A vowel hold cannot also retrigger. Set step repeats to 1.')
        if tie:
            if not notes or notes[-1].get('_step')!=index-1:raise ValueError(f'Step {index%16+1}: a hold must follow an enabled syllable.')
            notes[-1]['duration']=a-notes[-1]['start']
            lyric='+'
            phones=''
        else:
            fields=[cell.get(k,'') for k in ('onset','vowel','coda')]
            if any(not isinstance(v,str) or len(v)>40 for v in fields):raise ValueError('Use short ARPAbet sounds in each step.')
            phones=' '.join(' '.join(fields).lower().split())
            unknown=set(phones.split())-PHONES
            if not phones or unknown:raise ValueError(f'Step {index%16+1}: enter supported consonants/vowels. Unknown: '+', '.join(sorted(unknown)))
            label=cell.get('label','')
            if not isinstance(label,str) or len(label)>40:raise ValueError('Step label must be text under 40 characters.')
            lyric=label.strip() or phones.replace(' ','·')
        for hit in range(int(ratchet)):
            notes.append({'start':round(a+(b-a)*hit/ratchet,6),'duration':round((b-a)*gate/ratchet,6),'pitch':int(pitch),'lyric':lyric,'phonemes':phones,'accent':cell.get('accent',False),'_step':index})
    if not notes:raise ValueError('Turn on at least one syllable step.')
    for note in notes:note.pop('_step')
    return notes
