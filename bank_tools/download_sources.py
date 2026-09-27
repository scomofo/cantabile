import json,struct,zlib,binascii,time,concurrent.futures
from pathlib import Path
from vocalset_remote import span,ROOT
items=json.loads((Path(__file__).resolve().parent/'source-selection.json').read_text())
selected=[x for x in items if x['name'].startswith('FULL/') and x['name'].endswith('.wav') and ('/long_tones/straight/' in x['name'] or any('/scales/'+t+'/' in x['name'] for t in ('vibrato','breathy','belt')))]
selected.sort(key=lambda x:x['offset'])
batches=[]
for x in selected:
    # Local ZIP header + file name + typical extended fields; range is clipped later.
    end=x['offset']+30+len(x['name'].encode())+1024+x['compressed']
    if batches and x['offset']-batches[-1]['end']<160000 and end-batches[-1]['start']<6000000:
        batches[-1]['items'].append(x);batches[-1]['end']=end
    else:batches.append(dict(start=x['offset'],end=end,items=[x]))

def task(batch):
    pending=[x for x in batch['items'] if not (ROOT/'vocalset-raw'/x['name']).exists()]
    if not pending:return len(batch['items']),0
    for attempt in range(3):
        try:data=span(batch['start'],batch['end']);break
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt*2)
    for x in batch['items']:
        offset=x['offset']-batch['start'];parts=struct.unpack('<4s5H3I2H',data[offset:offset+30]);a=offset+30+parts[-2]+parts[-1]
        raw=zlib.decompress(data[a:a+x['compressed']],-15)
        if len(raw)!=x['size'] or (binascii.crc32(raw)&0xffffffff)!=x['crc']:raise RuntimeError('CRC mismatch '+x['name'])
        dest=ROOT/'vocalset-raw'/x['name'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    return len(batch['items']),len(data)

print('Selected',len(selected),'recordings in',len(batches),'range batches;',round(sum(b['end']-b['start'] for b in batches)/1e6,1),'MB',flush=True)
count=total=0
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for f in concurrent.futures.as_completed([pool.submit(task,b) for b in batches]):
        n,size=f.result();count+=n;total+=size;print(f'{count}/{len(selected)} source recordings · {total/1e6:.1f} MB transferred',flush=True)
(ROOT/'vocalset-selection.json').write_text(json.dumps(selected,indent=2))
