import copy
import io
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cantabile.score import demo,validate,VOCALS,RANGES
from cantabile.render import section_signature,sample_pitch
from cantabile.exchange import midi_export,midi_import,musicxml_export
from cantabile.microphone import melody_from_wav
from cantabile.pattern import compile_pattern


class ScoreTests(unittest.TestCase):
    def test_all_ranges_allow_solo_and_ensemble(self):
        for role in VOCALS:
            for count in [1,4,8]:
                p=demo();t=p['tracks'][0];t['role']=role;t['singers']=count
                self.assertEqual(validate(p)['tracks'][0]['singers'],count)

    def test_validation_does_not_mutate_input(self):
        p=demo();before=copy.deepcopy(p);p['tracks'][0]['notes'][1]['start']=1
        with self.assertRaisesRegex(ValueError,'overlap'):validate(p)
        self.assertEqual(before['tracks'][0]['notes'][0],p['tracks'][0]['notes'][0])

    def test_invalid_numbers_and_notes(self):
        for value in [float('nan'),float('inf'),True,0,500]:
            p=demo();p['tempo']=value
            with self.assertRaises(ValueError):validate(p)
        p=demo();p['tracks'][0]['notes']=[None]
        with self.assertRaises(ValueError):validate(p)

    def test_melisma_requires_adjacent_word(self):
        p=demo();p['tracks'][0]['notes'][0]['lyric']='+'
        with self.assertRaisesRegex(ValueError,'continuation'):validate(p)
        p=demo();p['tracks'][0]['notes'][1]['lyric']='+'
        validate(p)

    def test_unknown_voice_and_unbounded_choir_rejected(self):
        p=demo();p['tracks'][0]['voice']='madeup'
        with self.assertRaisesRegex(ValueError,'voice'):validate(p)
        p=demo()
        for t in p['tracks'][:5]:t['enabled']=True;t['singers']=8
        with self.assertRaisesRegex(ValueError,'32'):validate(p)

    def test_stem_identity_changes_with_score_not_mix(self):
        p=demo();t=p['tracks'][0];a=section_signature(t,p['tempo']);t['gain']=.1
        self.assertEqual(a,section_signature(t,p['tempo']))
        self.assertNotEqual(a,section_signature(t,p['tempo']+1))
        t['notes'][0]['lyric']='sing';self.assertNotEqual(a,section_signature(t,p['tempo']))

    def test_sample_octave_convention(self):
        self.assertEqual(sample_pitch('LDFlute_susNV_C4_v1_1.wav'),72)


class ExchangeTests(unittest.TestCase):
    def test_midi_roundtrip_preserves_melody_words_and_tempo(self):
        p=demo();p['tracks']=p['tracks'][:1]
        result=midi_import(midi_export(p))
        self.assertAlmostEqual(result['tempo'],p['tempo'],places=2)
        self.assertEqual(result['tracks'][0]['notes'],p['tracks'][0]['notes'])

    def test_xml_duration_lyrics_and_ties(self):
        p=demo();root=ET.fromstring(musicxml_export(p))
        self.assertEqual(root.findtext('.//work-title'),p['title'])
        self.assertEqual([x.text for x in root.findall('.//lyric/text')],[n['lyric'] for n in p['tracks'][0]['notes']])
        for m in root.findall('.//measure'):
            self.assertEqual(sum(int(x.text) for x in m.findall('note/duration')),1920)
        self.assertTrue(root.findall('.//tie'))


class VocalPatternTests(unittest.TestCase):
    def pattern(self):
        return {'division':.25,'swing':.3,'repeats':2,'cells':[{'on':True,'onset':'b','vowel':'iy','coda':'t','pitch':55,'gate':.85,'accent':i%4==0} for i in range(16)]}

    def test_swing_accents_and_no_overlap(self):
        notes=compile_pattern(self.pattern())
        self.assertEqual(len(notes),32);self.assertEqual(notes[1]['start'],.325)
        self.assertEqual(notes[0]['phonemes'],'b iy t');self.assertTrue(notes[0]['accent'])
        self.assertTrue(all(a['start']+a['duration']<=b['start']+1e-6 for a,b in zip(notes,notes[1:])))

    def test_holds_and_ratchets(self):
        pattern=self.pattern();pattern['cells'][1]['tie']=True
        pattern['cells'][2]['ratchet']=2
        notes=compile_pattern(pattern)
        self.assertEqual(notes[1]['lyric'],'+')
        self.assertEqual(notes[0]['start']+notes[0]['duration'],notes[1]['start'])
        self.assertEqual(len(notes),34)
        p=demo();p['tracks']=p['tracks'][:1];p['tracks'][0]['notes']=notes
        validate(p)

    def test_invalid_hold_phone_and_ratchet(self):
        for changes in [{'tie':True},{'vowel':'notaphone'},{'ratchet':0},{'ratchet':1.5}]:
            p=self.pattern();p['cells'][0].update(changes)
            with self.assertRaises(ValueError):compile_pattern(p)

    def test_invalid_voice_controls(self):
        for key,value in [('grit',float('nan')),('formant',6),('transpose',.5),('delay',1)]:
            p=demo();p['tracks'][0]['vox'][key]=value
            with self.assertRaises(ValueError):validate(p)


class MicrophoneTests(unittest.TestCase):
    def wav(self,y,sr=48000):
        b=io.BytesIO();sf.write(b,y,sr,format='WAV');return b.getvalue()

    def test_three_note_guide(self):
        sr=48000;t=np.arange(sr)/sr
        wav=np.concatenate([.2*np.sin(2*np.pi*440*2**((p-69)/12)*t) for p in [60,64,67]])
        result=melody_from_wav(self.wav(wav),120)
        self.assertEqual([n['pitch'] for n in result['notes']],[60,64,67])
        self.assertEqual([n['start'] for n in result['notes']],[0,2,4])

    def test_silence_is_not_a_melody(self):
        with self.assertRaisesRegex(ValueError,'No stable melody'):melody_from_wav(self.wav(np.zeros(48000)),120)


if __name__=='__main__':unittest.main()
