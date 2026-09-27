"""Local application server. Run python app.py (Python 3.10+)."""
import argparse
import base64
import hashlib
import io
import json
import math
import mimetypes
from pathlib import Path
import re
import threading
import uuid
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from cantabile.score import demo, validate, RANGES
from cantabile.voice import model_root, Cancelled, SR, ROOT
from cantabile.render import Renderer, STEMS, OUTPUT, section_signature
from cantabile.exchange import midi_import, midi_export, musicxml_export
from cantabile.microphone import melody_from_wav
from cantabile.pattern import compile_pattern
from cantabile.bank import public_voices, baseline

renderer=Renderer();jobs={};lock=threading.Lock()


def work(job,project):
    def progress(message,value):job.update(message=message,progress=value)
    try:
        result=renderer.run(project,progress,job['cancel'])
        if job['cancel'].is_set():raise Cancelled()
        job.update(state='complete',result=result)
    except Cancelled:job.update(state='cancelled',message='Render cancelled. Your score is unchanged.')
    except Exception as e:job.update(state='error',message=str(e))


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def respond(self,data,status=200,kind='application/json'):
        if kind=='application/json':data=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)

    def local(self):
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed:raise ValueError('Use the local application address.')
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+x for x in allowed}:raise ValueError('Cross-origin requests are not accepted.')

    def do_GET(self):
        try:
            self.local();path=urlparse(self.path).path
            if path=='/api/state':
                try:model_root();installed=True
                except ValueError:installed=False
                try:model_root('tiger');tiger=True
                except ValueError:tiger=False
                example=demo()
                if not installed and (ROOT/'examples/recorded-choir.json').exists():example=validate(json.loads((ROOT/'examples/recorded-choir.json').read_text()))
                return self.respond({'demo':example,'ranges':RANGES,'voiceInstalled':installed,'tigerInstalled':tiger,'bank':public_voices()})
            if path.startswith('/api/jobs/'):
                job=jobs.get(path.rsplit('/',1)[1])
                if not job:return self.respond({'error':'Render not found.'},404)
                return self.respond({k:v for k,v in job.items() if k!='cancel'})
            if re.fullmatch(r'/renders/[a-f0-9]{16}/[a-zA-Z0-9_-]+\.(wav|json)',path):
                file=ROOT/path.lstrip('/')
            elif re.fullmatch(r'/vocal-bank/previews/vs-[fm][0-9]+\.wav',path):file=ROOT/path.lstrip('/')
            elif re.fullmatch(r'/imports/[a-f0-9]{64}\.wav',path):file=ROOT/path.lstrip('/')
            elif path in ('/','/app.js','/style.css','/recorder.js'):file=ROOT/'web'/('index.html' if path=='/' else path[1:])
            else:return self.respond({'error':'Not found'},404)
            if not file.is_file():return self.respond({'error':'Not found'},404)
            return self.respond(file.read_bytes(),kind=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        except (ValueError,TypeError) as e:self.respond({'error':str(e)},400)

    def do_POST(self):
        try:
            self.local();size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=45_000_000:raise ValueError('Request is empty or too large (45 MB limit).')
            if self.headers.get_content_type()!='application/json':raise ValueError('Expected a JSON request.')
            body=json.loads(self.rfile.read(size));path=urlparse(self.path).path
            if path=='/api/validate':return self.respond({'project':validate(body)})
            if path=='/api/pattern':return self.respond({'notes':compile_pattern(body)})
            if path=='/api/voice/baseline':return self.respond({'baseline':baseline(body['voice'])})
            if path=='/api/render':
                project=validate(body)
                with lock:
                    if any(j['state']=='running' for j in jobs.values()):return self.respond({'error':'A render is already running. Wait or cancel it first.'},409)
                    jid=uuid.uuid4().hex;job={'id':jid,'state':'running','progress':0,'message':'Preparing score','cancel':threading.Event()};jobs[jid]=job
                    for old in list(jobs)[:-30]:jobs.pop(old,None)
                threading.Thread(target=work,args=(job,project),daemon=True).start();return self.respond({'id':jid},202)
            if path=='/api/cancel':
                job=jobs.get(body.get('id'))
                if job and job['state']=='running':job['cancel'].set();job['message']='Cancelling after the current voice operation…'
                return self.respond({'ok':True})
            if path=='/api/midi/import':return self.respond(midi_import(base64.b64decode(body['data'],validate=True)))
            if path=='/api/mic/notes':
                tempo=float(body['tempo'])
                if not math.isfinite(tempo) or not 40<=tempo<=200:raise ValueError('Tempo must be 40–200 BPM.')
                return self.respond(melody_from_wav(base64.b64decode(body['data'],validate=True),tempo))
            if path in ('/api/midi/export','/api/musicxml/export'):
                data=midi_export(body) if '/midi/' in path else musicxml_export(body)
                return self.respond({'data':base64.b64encode(data).decode()})
            if path=='/api/stem':
                p=validate(body['project']);t=next((t for t in p['tracks'] if t['id']==body['track']),None)
                if t is None:raise ValueError('Select a section first.')
                raw=base64.b64decode(body['data'],validate=True)
                info=sf.info(io.BytesIO(raw))
                if info.frames/info.samplerate>62 or info.channels>2:raise ValueError('Use a mono or stereo WAV shorter than 62 seconds.')
                if not info.format.startswith('WAV'):raise ValueError('Use an uncompressed WAV file.')
                wav,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True)
                if not len(wav) or not np.all(np.isfinite(wav)):raise ValueError('WAV audio is empty or invalid.')
                if sr!=SR:
                    g=math.gcd(sr,SR);wav=resample_poly(wav,SR//g,sr//g,axis=0)
                key=hashlib.sha256(raw).hexdigest();sf.write(STEMS/(key+'.wav'),wav,SR,subtype='FLOAT')
                return self.respond({'stem':key,'stem_score':section_signature(t,p['tempo']),'duration':len(wav)/SR})
            return self.respond({'error':'Not found'},404)
        except (ValueError,KeyError,TypeError,StopIteration,EOFError,OSError,RuntimeError) as e:self.respond({'error':str(e)},400)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    from prepare_bank import prepare_bank
    prepare_bank()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Cantabile is ready at http://127.0.0.1:{args.port}',flush=True)
    if not args.no_browser:webbrowser.open(f'http://127.0.0.1:{args.port}')
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
