import base64
import io
import json
from pathlib import Path
import sys
import threading
import time
import unittest
import urllib.request
import urllib.error
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from cantabile.score import demo


class LocalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        cls.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()

    def request(self,path,data=None,headers=None):
        h={'Content-Type':'application/json'};h.update(headers or {})
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=h)
        with self.opener.open(req,timeout=10) as r:return json.load(r)

    def test_state_and_foreign_origin(self):
        self.assertIn('demo',self.request('/api/state'))
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/validate',demo(),{'Origin':'https://example.com'})
        self.assertEqual(e.exception.code,400)

    def test_hardware_script_is_served(self):
        with self.opener.open(self.base+'/hardware.js',timeout=10) as response:
            self.assertIn('javascript',response.headers['Content-Type'])
            self.assertIn(b'CantabileHardware',response.read())

    def test_invalid_project_returns_actionable_error(self):
        p=demo();p['tracks'][0]['notes'][0]['pitch']=float('nan')
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/validate',p)
        self.assertIn('MIDI pitch',json.load(e.exception)['error'])

    def test_import_recording_and_reject_stale_score(self):
        sr=16000;t=np.arange(sr)/sr;b=io.BytesIO();sf.write(b,.1*np.sin(2*np.pi*220*t),sr,format='WAV')
        p=demo();r=self.request('/api/stem',{'project':p,'track':'solo','data':base64.b64encode(b.getvalue()).decode()})
        p['tracks'][0].update(r,voice='imported');p['tempo']+=1
        job=self.request('/api/render',p)
        for _ in range(50):
            state=self.request('/api/jobs/'+job['id'])
            if state['state']!='running':break
            time.sleep(.1)
        self.assertEqual(state['state'],'error');self.assertIn('changed since the WAV',state['message'])

    def test_path_traversal_is_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/renders/../../app.py')
        self.assertEqual(e.exception.code,404)


if __name__=='__main__':unittest.main()
