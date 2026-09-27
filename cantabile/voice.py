"""Direct ONNX inference for the pinned Hanami NoTension beta voicebank.

Uses the model's learned phoneme duration predictor and acoustic network.
No speech pitch shifting, canned phrases, or replacement lyric audio.
"""
from pathlib import Path
import os
import re
import threading
import cmudict
import numpy as np
# Opt out before native-runtime initialization, including its initialization event.
# See microsoft/onnxruntime docs/Privacy.md. Local inference needs no telemetry.
os.environ['ORT_DISABLE_TELEMETRY']='1'
import onnxruntime as ort
ort.disable_telemetry_events()
from .score import VOX_DEFAULTS

SR = 44100
HOP = 512
ROOT = Path(__file__).resolve().parents[1]
_dictionary = None


def model_root(voice='hanami'):
    if voice.startswith('tiger'):
        root=ROOT/'models/tiger'
        if not (root/'dsconfig.yaml').is_file():raise ValueError('TIGER voice is not installed. Run python setup_assets.py.')
        return root
    candidates = sorted((ROOT/'models/hanami').glob('*/dsconfig.yaml'))
    if not candidates:
        raise ValueError('Singing voice is not installed. Run python setup_assets.py first.')
    return candidates[0].parent


def phonemes(note, inventory):
    global _dictionary
    if note.get('phonemes', '').strip():
        phones = note['phonemes'].lower().split()
    else:
        word = re.sub(r"[^a-z']", '', note['lyric'].lower())
        if _dictionary is None: _dictionary = cmudict.dict()
        entries = _dictionary.get(word)
        if not entries:
            raise ValueError(f'No pronunciation for “{note["lyric"]}”. Enter ARPAbet phonemes for this note, e.g. l ay t for light.')
        phones = [re.sub(r'\d', '', x.lower()) for x in entries[0]]
    unknown = set(phones) - set(inventory)
    if unknown or not phones:
        raise ValueError('Unsupported phonemes: ' + ', '.join(sorted(unknown)))
    return phones


class Cancelled(Exception):
    pass


class Singer:
    def __init__(self,voice='hanami'):
        root = model_root(voice)
        self.voice=voice
        tiger=voice.startswith('tiger')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.sessions = {}
        paths=[('acoustic','dsacoustic/acoustic.onnx'),('vocoder','dsvocoder/tgm_hifigan.onnx'),('linguistic','dsdur/files/linguistic.onnx'),('duration','dsdur/files/dur.onnx')] if tiger else [('acoustic','dsmain/acoustic.onnx'),('vocoder','dsvocoder/titaniagan.onnx'),('linguistic','dsmain/linguistic.onnx'),('duration','dsdur/dur.onnx')]
        for name,path in paths:
            self.sessions[name] = ort.InferenceSession(str(root/path),options,providers=['CPUExecutionProvider'])
        self.inventory = (root/('dsacoustic/phonemes.txt' if tiger else 'dsmain/phonemes.txt')).read_text().splitlines()
        mode='vinyl' if voice=='tiger-vinyl' else 'fresh'
        self.acoustic_embedding = np.fromfile(root/(f'dsacoustic/tiger_{mode}.emb' if tiger else 'dsmain/embeds/acoustic/acoustic_Hanami.emb'),dtype='<f4')
        self.duration_embedding = np.fromfile(root/(f'dsdur/files/tiger_{mode}.emb' if tiger else 'dsmain/embeds/variance/variance_Hanami.emb'),dtype='<f4')

    def synthesize(self, notes, tempo, quality='draft', cancel=None, singer_index=0, delivery='sing',vox=None):
        if cancel and cancel.is_set(): raise Cancelled()
        vox={**VOX_DEFAULTS,**(vox or {})}
        sec = 60/tempo
        # One phoneme group per word, with + notes extending the preceding vowel.
        groups=[]; end=0
        for note in notes:
            start=round(note['start']*sec*SR/HOP)
            stop=round((note['start']+note['duration'])*sec*SR/HOP)
            if start>end: groups.append((['SP'],start-end,60))
            if note['lyric']=='+':
                ph,d,m=groups[-1];groups[-1]=(ph,d+stop-start,m)
            else:
                ph=phonemes(note,self.inventory)
                if stop-start<len(ph):raise ValueError('Note is too short for this word. Lengthen it or simplify its pronunciation.')
                groups.append((ph,stop-start,note['pitch']+vox['transpose']))
            end=stop
        groups.append((['SP'],round(.3*SR/HOP),60))
        phs=[ph for g,_,_ in groups for ph in g]
        tokens=np.array([[self.inventory.index(ph) for ph in phs]],np.int64)
        div=np.array([[len(g) for g,_,_ in groups]],np.int64)
        durations=np.array([[d for _,d,_ in groups]],np.int64)
        enc,mask=self.sessions['linguistic'].run(None,{'tokens':tokens,'word_div':div,'word_dur':durations})
        midi=np.array([[m for g,_,m in groups for _ in g]],np.int64)
        embedding=np.broadcast_to(self.duration_embedding,(1,len(phs),256)).copy()
        raw=self.sessions['duration'].run(None,{'encoder_out':enc,'x_masks':mask,'ph_midi':midi,'spk_embed':embedding})[0].reshape(-1)
        # Conserve each word's exact score duration, including consonants and melismas.
        phone_durs=[];i=0
        for g,total,_ in groups:
            pred=np.maximum(raw[i:i+len(g)],.1);i+=len(g)
            if len(g)>1:
                allocation=pred/pred.sum()*max(0,total-len(g))
                d=np.floor(allocation).astype(np.int64)+1
                for k in np.argsort(-(allocation-np.floor(allocation)))[:total-int(d.sum())]:d[k]+=1
            else:d=np.array([total],np.int64)
            phone_durs.extend(d.tolist())
        frames=sum(phone_durs)
        f0=np.zeros(frames,np.float32)
        prev=None
        for note in notes:
            a=round(note['start']*sec*SR/HOP);b=round((note['start']+note['duration'])*sec*SR/HOP)
            t=np.arange(b-a)*HOP/SR
            vib=vox['vibrato']*np.sin(2*np.pi*(vox['vibrato_rate']+.09*singer_index)*t+singer_index*.6)*np.minimum(1,np.maximum(0,(t-.22)/.3))
            if delivery=='rhythmic':vib=np.zeros_like(t)
            cents=0 if singer_index==0 else .035*np.sin(singer_index*2.4)
            contour=np.full(b-a,note['pitch']+vox['transpose'],np.float64)
            if prev and abs(prev['start']+prev['duration']-note['start'])<1e-5 and vox['glide']:
                count=min(len(contour),round(vox['glide']*SR/HOP))
                contour[:count]=np.linspace(prev['pitch']+vox['transpose'],note['pitch']+vox['transpose'],count)
            f0[a:b]=440*2**((contour-69+vib+cents)/12)
            prev=note
        if cancel and cancel.is_set(): raise Cancelled()
        mel=self.sessions['acoustic'].run(None,{
            'tokens':tokens,'durations':np.array([phone_durs],np.int64),'f0':f0[None],
            'gender':np.full((1,frames),np.clip(vox['formant']+.12*np.sin(singer_index*1.7),-5,5),np.float32),'velocity':np.ones((1,frames),np.float32),
            'spk_embed':np.broadcast_to(self.acoustic_embedding,(1,frames,256)).copy(),
            'depth':np.array(400,np.int64),'speedup':np.array(40 if quality=='draft' else 10,np.int64),
        })[0]
        if cancel and cancel.is_set(): raise Cancelled()
        wav=self.sessions['vocoder'].run(None,{'mel':mel,'f0':f0[None]})[0].reshape(-1)
        if not np.all(np.isfinite(wav)):raise ValueError('Voice model produced invalid audio.')
        # Step accents are local loudness emphasis, with short ramps to avoid clicks.
        envelope=np.ones(len(wav),np.float32)
        for note in notes:
            if not note.get('accent'):continue
            a=round(note['start']*sec*SR);b=min(len(wav),round((note['start']+note['duration'])*sec*SR))
            if b<=a:continue
            shape=np.ones(b-a,np.float32);ramp=min(round(.005*SR),len(shape)//3)
            if ramp:shape[:ramp]=np.linspace(0,1,ramp);shape[-ramp:]=np.linspace(1,0,ramp)
            envelope[a:b]+=(vox['accent_gain']-1)*shape
        wav*=envelope
        return wav.astype(np.float32)
