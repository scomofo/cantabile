import sys
import threading
from pathlib import Path
import unittest
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cantabile.score import demo
from cantabile.render import Renderer,OUTPUT
from cantabile.voice import model_root,Cancelled


class AudioTests(unittest.TestCase):
    def test_real_two_singer_render_cache_and_cancellation(self):
        try:model_root();model_root('tiger')
        except ValueError:self.skipTest('Install voice models to run actual synthesis acceptance.')
        p=demo();p['title']='Audio acceptance';p['tracks']=p['tracks'][:1]
        t=p['tracks'][0];t['singers']=2;t['voice']='tiger';t['spread']=.6
        t['notes']=[{'start':.5,'duration':1,'pitch':55,'lyric':'light'}]
        renderer=Renderer();events=[]
        result=renderer.run(p,lambda message,_:events.append(message))
        self.assertTrue(any('singer 2 of 2' in x for x in events))
        wav,sr=sf.read(OUTPUT/result['id']/'mix.wav')
        self.assertEqual(sr,44100);self.assertEqual(wav.shape[1],2)
        self.assertTrue(np.all(np.isfinite(wav)));self.assertGreater(np.max(np.abs(wav)),.005)
        self.assertLessEqual(np.max(np.abs(wav)),.941)
        self.assertGreater(np.mean(np.abs(wav[:,0]-wav[:,1])),1e-5)
        repeat=renderer.run(p);wav2,_=sf.read(OUTPUT/repeat['id']/'mix.wav');np.testing.assert_array_equal(wav,wav2)
        event=threading.Event();event.set()
        with self.assertRaises(Cancelled):renderer.run(p,cancel=event)


if __name__=='__main__':unittest.main()
