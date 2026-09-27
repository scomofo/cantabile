"""Read selected members from the original public VocalSet archive by HTTP range."""
import io,json,urllib.request,zipfile,zlib,struct,binascii,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'.bank_sources'
URL='https://zenodo.org/api/records/1442513/files/VocalSet11.zip/content'
SIZE=2077243579

def span(start,end):
    req=urllib.request.Request(URL,headers={'User-Agent':'Cantabile-VocalBank/0.2','Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(req,timeout=40) as r:
        data=r.read(end-start+2)
        if r.status!=206 or r.headers.get('Content-Range','')!=f'bytes {start}-{end}/{SIZE}' or len(data)!=end-start+1:
            raise RuntimeError(f'Archive server did not honor requested range: {r.status}, {r.headers.get("Content-Range")}, {len(data)} bytes')
        return data

class Remote(io.RawIOBase):
    def __init__(self):self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else SIZE+offset
        return self.pos
    def tell(self):return self.pos
    def read(self,count=-1):
        n=SIZE-self.pos if count<0 else min(count,SIZE-self.pos)
        if n<=0:return b''
        out=span(self.pos,self.pos+n-1);self.pos+=n;return out

def fetch(item):
    dest=ROOT/'vocalset-raw'/item['name'];dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and binascii.crc32(dest.read_bytes())&0xffffffff==item['crc']:return dest
    offset=item['offset'];header=span(offset,offset+29)
    parts=struct.unpack('<4s5H3I2H',header);extra=parts[-2]+parts[-1]
    data=span(offset+30+extra,offset+30+extra+item['compressed']-1)
    raw=zlib.decompress(data,-15) if item['method']==8 else data
    if len(raw)!=item['size'] or (binascii.crc32(raw)&0xffffffff)!=item['crc']:raise RuntimeError('Archive member integrity failed: '+item['name'])
    dest.write_bytes(raw);return dest

if __name__=='__main__':
    with zipfile.ZipFile(Remote()) as archive:
        items=[dict(name=x.filename,offset=x.header_offset,compressed=x.compress_size,size=x.file_size,crc=x.CRC,method=x.compress_type) for x in archive.infolist() if not x.is_dir()]
    (ROOT/'vocalset-index.json').write_text(json.dumps(items,indent=2))
    print('Indexed',len(items),'members',flush=True)
    for x in items:
        if ('readme' in x['name'].lower() or x['name'].lower().endswith('.txt')) and '__MACOSX' not in x['name']:
            p=fetch(x);print(p.relative_to(ROOT),p.read_text(errors='replace')[:12000],flush=True)
    print('Example paths:',[x['name'] for x in items if x['name'].endswith('.wav') and '__MACOSX' not in x['name']][:30],flush=True)
