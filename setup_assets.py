"""Download the pinned original voicebanks directly from their creators.

No paid services, account credentials, model conversion, or voice training.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent
ASSETS={
 'hanami':{
  'url':'https://github.com/lottev1991/LotteV-Voicebank-Update-Repo/releases/download/v0.0.1b/Hoshino.Hanami.-LoveSong-.AI.for.DiffSinger.NoTension-BETA.zip',
  'sha256':'41bad5281f90d375a282513395c953ceae6a5903a5395bfef3e6974a16deec15',
  'size':536685428,
  'license':'https://lottev.moe/utau/voicebank-license/',
 },
 'tiger':{
  'url':'https://github.com/spicytigermeat/tiger_diffsinger/releases/download/v103/TIGER_DS_v103_PACK.zip',
  'sha256':'dc1e2e7efd2960c5f672cb5719fbd5af602a2fc21d1742716c8ac4399b6e243a',
  'size':555597571,
  'license':'https://github.com/spicytigermeat/tiger_diffsinger/blob/master/LICENSE.md',
 },
}


def checksum(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive,root):
    root=root.resolve()
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>2_000_000_000:raise ValueError('Archive exceeds the expected size.')
        for item in z.infolist():
            dest=(root/item.filename).resolve()
            if not dest.is_relative_to(root):raise ValueError('Unsafe archive path.')
            z.extract(item,root)


def installed(voice):
    base=ROOT/'models'/voice
    config=next(base.glob('*/dsconfig.yaml'),None) if voice=='hanami' else base/'dsconfig.yaml'
    if not config or not config.is_file():return False
    folder=config.parent
    required=['dsmain/acoustic.onnx','dsdur/dur.onnx','dsmain/linguistic.onnx','dsvocoder/titaniagan.onnx'] if voice=='hanami' else ['dsacoustic/acoustic.onnx','dsdur/files/dur.onnx','dsdur/files/linguistic.onnx','dsvocoder/tgm_hifigan.onnx']
    return all((folder/name).is_file() for name in required)


def install(voice):
    if installed(voice):print(voice+': already installed.');return
    item=ASSETS[voice];cache=ROOT/'.downloads';cache.mkdir(exist_ok=True)
    archive=cache/(voice+'.zip')
    if not archive.is_file() or checksum(archive)!=item['sha256']:
        print(f'Downloading {voice}: {item["size"]/1e6:.0f} MB. Creator terms: {item["license"]}',flush=True)
        request=urllib.request.Request(item['url'],headers={'User-Agent':'Cantabile-Prototype/0.1'})
        temporary=archive.with_suffix('.part');count=0;previous=-1
        with urllib.request.urlopen(request,timeout=120) as response,temporary.open('wb') as out:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                out.write(chunk);count+=len(chunk);percent=int(100*count/item['size'])
                if percent//10!=previous:print(f'  {percent}%',flush=True);previous=percent//10
        if checksum(temporary)!=item['sha256']:
            temporary.unlink(missing_ok=True);raise ValueError('Download checksum did not match. Please retry; no model was installed.')
        temporary.replace(archive)
    models=ROOT/'models';models.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='voice-setup-',dir=models) as temp:
        temp=Path(temp);staging=temp/'voice';staging.mkdir()
        if voice=='tiger':
            with zipfile.ZipFile(archive) as z:
                inner=z.read('TIGER_DS_v103_PACK/Voice Library/TIGER_DS_v103.zip')
            import io
            safe_extract(io.BytesIO(inner),staging)
        else:safe_extract(archive,staging)
        target=models/voice
        if target.exists():raise ValueError(f'{target} is incomplete. Rename that folder and run setup again to preserve any custom files.')
        shutil.move(str(staging),str(target))
    print(voice+': installed. Original files and license notices are preserved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--voice',choices=['all','hanami','tiger'],default='all');args=parser.parse_args()
    print('Cantabile personal prototype setup. Downloads two voicebanks (~1.1 GB).\nThe voice dependencies include noncommercial terms; see THIRD_PARTY.md.\n')
    for voice in ASSETS if args.voice=='all' else [args.voice]:install(voice)
    print('\nReady. Run python app.py to open Cantabile.')
