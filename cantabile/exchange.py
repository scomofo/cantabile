import io
import math
import mido
import xml.etree.ElementTree as ET
from .score import validate, VOCALS, note_name


def midi_export(source):
    p=validate(source);out=mido.MidiFile(ticks_per_beat=480)
    conductor=mido.MidiTrack();out.tracks.append(conductor)
    conductor.append(mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(p['tempo']),time=0))
    programs={'violin':48,'cello':42,'horn':60,'flute':73}
    for i,t in enumerate(p['tracks']):
        if not t['enabled']:continue
        track=mido.MidiTrack();out.tracks.append(track)
        track.append(mido.MetaMessage('track_name',name=t['name']))
        channel=i if i<9 else i+1
        channel=min(channel,15)
        track.append(mido.Message('program_change',program=programs.get(t['role'],53),channel=channel))
        events=[]
        for n in t['notes']:
            at=round(n['start']*480);end=round((n['start']+n['duration'])*480)
            if n['lyric']:events.append((at,1,mido.MetaMessage('lyrics',text=n['lyric'])))
            events.append((at,2,mido.Message('note_on',note=n['pitch'],velocity=115 if n.get('accent') else 80,channel=channel)))
            events.append((end,0,mido.Message('note_off',note=n['pitch'],velocity=0,channel=channel)))
        prev=0
        for tick,_,msg in sorted(events,key=lambda e:(e[0],e[1])):
            msg.time=tick-prev;track.append(msg);prev=tick
    buff=io.BytesIO();out.save(file=buff);return buff.getvalue()


def midi_import(data):
    midi=mido.MidiFile(file=io.BytesIO(data))
    if midi.type==2:raise ValueError('MIDI type 2 uses independent timelines. Export type 0 or 1.')
    tempos=set();tracks=[]
    for ti,track in enumerate(midi.tracks):
        at=0;active={};notes=[];lyrics={};name=f'MIDI track {ti+1}'
        for msg in track:
            at+=msg.time
            if msg.type=='set_tempo':tempos.add(msg.tempo)
            elif msg.type=='track_name':name=msg.name
            elif msg.type=='lyrics':lyrics[at]=msg.text
            elif msg.type=='note_on' and msg.velocity:
                k=(msg.channel,msg.note)
                if k in active:raise ValueError('MIDI contains overlapping repetitions of the same note.')
                active[k]=at
            elif msg.type in ('note_off','note_on'):
                start=active.pop((msg.channel,msg.note),None)
                if start is not None and at>start:
                    notes.append(dict(start=start/midi.ticks_per_beat,duration=(at-start)/midi.ticks_per_beat,pitch=msg.note,lyric=lyrics.get(start,'ah')))
        if active:raise ValueError('MIDI has notes with no matching note-off.')
        if notes:tracks.append(dict(name=name,notes=sorted(notes,key=lambda n:n['start'])))
    if len(tempos)>1:raise ValueError('Tempo changes are not supported yet. Export a constant-tempo MIDI.')
    if not tracks:raise ValueError('No pitched notes found in this MIDI.')
    return {'tempo':round(mido.tempo2bpm(next(iter(tempos),500000)),3),'tracks':tracks}


def musicxml_export(source):
    p=validate(source);root=ET.Element('score-partwise',version='4.0')
    work=ET.SubElement(root,'work');ET.SubElement(work,'work-title').text=p['title']
    listing=ET.SubElement(root,'part-list')
    selected=[t for t in p['tracks'] if t['enabled'] and t['role'] in VOCALS and t['notes']]
    if not selected:raise ValueError('Enable at least one vocal section to export lyrics.')
    for ti,t in enumerate(selected):
        pid='P'+str(ti+1);sp=ET.SubElement(listing,'score-part',id=pid);ET.SubElement(sp,'part-name').text=t['name']
        part=ET.SubElement(root,'part',id=pid)
        total=math.ceil(max(n['start']+n['duration'] for n in t['notes'])/4)
        for bar in range(total):
            measure=ET.SubElement(part,'measure',number=str(bar+1));pos=bar*1920;stop=(bar+1)*1920
            if bar==0:
                attrs=ET.SubElement(measure,'attributes');ET.SubElement(attrs,'divisions').text='480'
                meter=ET.SubElement(attrs,'time');ET.SubElement(meter,'beats').text='4';ET.SubElement(meter,'beat-type').text='4'
                clef=ET.SubElement(attrs,'clef');ET.SubElement(clef,'sign').text='F' if t['role'] in ('bass','baritone') else 'G';ET.SubElement(clef,'line').text='4' if t['role'] in ('bass','baritone') else '2'
                direction=ET.SubElement(measure,'direction');dt=ET.SubElement(direction,'direction-type');ET.SubElement(dt,'words').text=f'{t["singers"]} singer(s)';ET.SubElement(direction,'sound',tempo=str(p['tempo']))
            for n in t['notes']:
                a=round(n['start']*480);b=round((n['start']+n['duration'])*480)
                if b<=bar*1920 or a>=stop:continue
                if a>pos:
                    rest=ET.SubElement(measure,'note');ET.SubElement(rest,'rest');ET.SubElement(rest,'duration').text=str(a-pos);pos=a
                node=ET.SubElement(measure,'note');pitch=ET.SubElement(node,'pitch');name=note_name(n['pitch'])
                ET.SubElement(pitch,'step').text=name[0]
                if '#' in name:ET.SubElement(pitch,'alter').text='1'
                ET.SubElement(pitch,'octave').text=str(n['pitch']//12-1)
                ET.SubElement(node,'duration').text=str(min(b,stop)-max(a,bar*1920))
                if a<bar*1920:ET.SubElement(node,'tie',type='stop')
                if b>stop:ET.SubElement(node,'tie',type='start')
                if a>=bar*1920:
                    lyric=ET.SubElement(node,'lyric')
                    if n['lyric']=='+':ET.SubElement(lyric,'extend')
                    else:ET.SubElement(lyric,'text').text=n['lyric']
                pos=min(b,stop)
            if pos<stop:
                rest=ET.SubElement(measure,'note');ET.SubElement(rest,'rest');ET.SubElement(rest,'duration').text=str(stop-pos)
    ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)
