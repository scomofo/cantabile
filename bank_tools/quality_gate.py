import json
from pathlib import Path
import numpy as np
import pyworld as pw
import soundfile as sf
root=Path(__file__).resolve().parents[1]/'vocal-bank';manifest=json.loads((root/'manifest.json').read_text());report=[]
for voice in manifest['voices']:
    for sample in voice['samples']:
        y,sr=sf.read(root/sample['file']);f0,t=pw.dio(y,sr,f0_floor=50,f0_ceil=1100,frame_period=10);f0=pw.stonemask(y,f0,t,sr)
        valid=f0>0
        median=float(np.median(69+12*np.log2(f0[valid]/440))) if valid.any() else None
        report.append(dict(voice=voice['id'],file=sample['file'],yin=sample['root_midi'],world=median,voiced=float(valid.mean()),difference=abs(median-sample['root_midi']) if median is not None else None))
    print('Audited',voice['id'],flush=True)
(root/'PITCH_AUDIT.json').write_text(json.dumps(report,indent=2))
print('AUDIT',len(report),'samples;',sum(x['difference'] is not None and x['difference']<.6 for x in report),'agree within 60 cents;',sum(x['difference'] is None or x['difference']>=.6 for x in report),'need filtering',flush=True)
print([x for x in report if x['difference'] is not None and x['difference']>5][:15],flush=True)

# Retain only samples whose independent estimators agree.
from sfz import write as write_sfz
by_file={x['file']:x for x in report};removed=[]
for voice in manifest['voices']:
    kept=[]
    for sample in voice['samples']:
        audit=by_file[sample['file']]
        if audit['difference'] is None or audit['difference']>=.6 or audit['voiced']<.55:
            removed.append(sample['file']);(root/sample['file']).unlink();continue
        sample['root_midi']=round(audit['world'],5)
        sample['pitch_validation']={'method':'WORLD DIO + StoneMask versus YIN','difference_semitones':round(audit['difference'],4),'voiced_fraction':round(audit['voiced'],4)}
        kept.append(sample)
    voice['samples']=kept;voice['techniques']=sorted({x['technique'] for x in kept})
    voice['sampled_range']=[round(min(s['root_midi'] for s in kept)),round(max(s['root_midi'] for s in kept))]
    voice['coverage']={t:sorted({s['vowel'] for s in kept if s['technique']==t}) for t in voice['techniques']}
manifest['quality_gate']='Independent YIN and WORLD pitch estimates agree within 0.6 semitone; WORLD voiced-frame fraction >= 0.55. Estimated roots refined with WORLD.'
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');write_sfz(manifest['voices'],root)
report_path=root/'BUILD_REPORT.json';build=json.loads(report_path.read_text());build['samples_before_pitch_audit']=build['samples'];build['samples']=sum(len(v['samples']) for v in manifest['voices']);build['pitch_audit_rejections']=removed;build['coverage']={v['id']:v['coverage'] for v in manifest['voices']};report_path.write_text(json.dumps(build,indent=2))
print('QUALITY GATE',build['samples'],'samples retained;',len(removed),'removed',flush=True)
