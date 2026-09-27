import copy,sys,unittest
from pathlib import Path
import numpy as np
import pyworld as pw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cantabile.bank import voices,baseline,synthesize
from cantabile.score import validate
from cantabile.tuning import correct,target_f0,DEFAULTS

class BankTests(unittest.TestCase):
    def test_every_voice_has_valid_neutral_baseline_and_sound(self):
        self.assertEqual(len(voices()),20)
        for voice in voices():
            b=baseline(voice);before=copy.deepcopy(b)
            t={'id':'test',**b};p=validate(dict(version=1,tempo=100,reverb=0,tracks=[t]))
            y=synthesize(p['tracks'][0],100)
            self.assertTrue(np.all(np.isfinite(y)));self.assertGreater(float(np.sqrt(np.mean(y*y))),.005)
            self.assertEqual(b,before);self.assertEqual(b['vox']['grit'],0)

    def test_sampled_voice_rejects_unrecorded_words(self):
        t={'id':'test',**baseline('vs-f1')};t['notes'][0]['lyric']='hello'
        with self.assertRaisesRegex(ValueError,'neural voice'):validate(dict(version=1,tempo=100,tracks=[t]))

    def test_holds_pitch_change_and_accent(self):
        t={'id':'test',**baseline('vs-m1')};t['notes']=[dict(start=0,duration=1,pitch=55,lyric='a'),dict(start=1,duration=1,pitch=57,lyric='+',accent=True)]
        t=validate(dict(version=1,tempo=100,tracks=[t]))['tracks'][0]
        y=synthesize(t,100);self.assertTrue(np.isfinite(y).all());self.assertGreater(np.max(abs(y)),.01)

class TuningTests(unittest.TestCase):
    def test_scale_mapping_unvoiced_and_strength(self):
        midi=np.array([60.3,61.2,63.2]);f0=440*2**((midi-69)/12)
        settings={**DEFAULTS,'enabled':True,'scale':'major','key':0,'speed_ms':0}
        result=69+12*np.log2(target_f0(f0,settings)/440)
        np.testing.assert_allclose(result,[60,62,64],atol=1e-8)
        self.assertEqual(target_f0(np.array([0.,440.]),settings)[0],0)
        np.testing.assert_array_equal(correct(np.ones(2000),44100,{**settings,'enabled':False}),np.ones(2000,dtype=np.float32))

    def test_real_audio_retunes_detuned_harmonic_voice(self):
        sr=44100;t=np.arange(sr*2)/sr;hz=440*2**(.35/12)
        y=sum(np.sin(2*np.pi*hz*k*t)/k for k in range(1,9))*.08
        before=y.copy();out=correct(y,sr,{**DEFAULTS,'enabled':True,'speed_ms':0})
        self.assertEqual(len(out),len(y));np.testing.assert_array_equal(y,before)
        self.assertTrue(np.isfinite(out).all())
        f0,times=pw.dio(out.astype(float),sr,f0_floor=80,f0_ceil=1000);f0=pw.stonemask(out.astype(float),f0,times,sr)
        mid=f0[(times>.3)&(times<1.7)&(f0>0)]
        self.assertGreater(len(mid),100);self.assertLess(abs(1200*np.log2(np.median(mid)/440)),12)

if __name__=='__main__':unittest.main()
