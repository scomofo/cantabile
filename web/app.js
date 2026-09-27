'use strict';
const $=id=>document.getElementById(id);
const vocalRoles=['solo','soprano','mezzo','alto','tenor','baritone','bass'];
const names={solo:'Solo voice',soprano:'Soprano',mezzo:'Mezzo-soprano',alto:'Alto',tenor:'Tenor',baritone:'Baritone',bass:'Bass'};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pitchName=n=>['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][n%12]+(Math.floor(n/12)-1);
let hardware=null,hardwarePart=null,hardwareProject=null,recordBusy=false;
let project,active='solo',ranges={},job=null,pendingMidi=null,recorded=null,recording=null,renderSnapshot=null,bank=[],renderKind='score';
const current=()=>project.tracks.find(t=>t.id===active)||project.tracks[0];
const bankVoice=t=>bank.find(v=>v.id===t.voice);
const isVocal=t=>vocalRoles.includes(t.role);
const voxDefaults={transpose:0,formant:0,vibrato:.14,vibrato_rate:5.2,glide:0,accent_gain:1.65,tone:0,grit:0,delay:0};
const voxControls=[['transpose','Transpose',-12,12,1,' st'],['formant','Formant / vocal color',-5,5,.1,''],['vibrato','Vibrato depth',0,.7,.01,' st'],['vibrato_rate','Vibrato rate',3,9,.1,' Hz'],['glide','Note glide',0,.2,.005,' s'],['accent_gain','Accent strength',1,2.5,.05,'×'],['tone','Dark ↔ bright',-1,1,.05,''],['grit','Grit',0,1,.05,''],['delay','Eighth-note delay',0,.5,.025,'']];
const clone=x=>JSON.parse(JSON.stringify(x));
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
async function api(path,body){const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed.');return data;}
function changed(){try{localStorage.setItem('cantabile-project-v1',JSON.stringify(project));}catch{status('Autosave is unavailable. Use Save project to keep your work.',true);}if(!$('result').hidden)$('render-info').textContent='Score changed · the player contains the previous render.';}
function download(data,name,type){const url=URL.createObjectURL(data instanceof Blob?data:new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
function safeName(){return (project.title.replace(/[^a-z0-9]+/gi,'-').replace(/^-|-$/g,'')||'cantabile').toLowerCase();}
async function base64(file){const buffer=file instanceof ArrayBuffer?file:await file.arrayBuffer();let binary='';const bytes=new Uint8Array(buffer);for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(binary);}
function binary(text){return Uint8Array.from(atob(text),c=>c.charCodeAt(0));}
function handle(fn){return async e=>{try{await fn(e);}catch(error){status(error.message,true);}};}
function drawSections(){
 const target=(tracks)=>tracks.map(t=>`<div class="section-row ${t.id===active?'selected':''} ${t.enabled?'':'disabled'}" data-id="${esc(t.id)}"><input type="checkbox" aria-label="Enable ${esc(t.name)}" ${t.enabled?'checked':''}><span class="part-icon" aria-hidden="true">${isVocal(t)?'♩':'♫'}</span><button class="label" data-select="${esc(t.id)}" style="border:0;background:transparent;text-align:left;padding:0"><strong>${esc(t.name)}</strong><small>${isVocal(t)?`${t.singers===1?'Soloist':t.singers+' singers'} · ${names[t.role]||t.role}`:'Sampled '+t.role}</small></button><span style="font-size:10px;color:var(--muted)">${t.notes.length}</span></div>`).join('');
 $('sections').innerHTML=target(project.tracks.filter(isVocal));$('instruments').innerHTML=target(project.tracks.filter(t=>!isVocal(t)));
 document.querySelectorAll('.section-row').forEach(row=>{row.querySelector('button').onclick=()=>{active=row.dataset.id;draw();};row.querySelector('input').onchange=e=>{project.tracks.find(t=>t.id===row.dataset.id).enabled=e.target.checked;changed();drawSections();};});
 $('singer-total').textContent=project.tracks.filter(t=>t.enabled&&isVocal(t)).reduce((n,t)=>n+t.singers,0)+' SINGERS';
}
function options(values,chosen){return values.map(([value,label])=>`<option value="${esc(value)}" ${value===chosen?'selected':''}>${esc(label)}</option>`).join('');}
function drawControls(){
 const t=current();$('part-title').textContent=t.name;
 $('part-controls').innerHTML=`<label>Section name<input class="section-name" id="section-name" value="${esc(t.name)}" maxlength="60"></label>`+(isVocal(t)?`<label>Vocal range<select id="role">${options(vocalRoles.filter(r=>r!=='solo').map(r=>[r,names[r]]),t.role==='solo'?'soprano':t.role)}</select></label><label>Performance<select id="mode">${options([['solo','Soloist'],['ensemble','Ensemble']],t.singers===1?'solo':'ensemble')}</select></label><label>Singers<input class="small" id="singers" type="number" min="1" max="8" value="${t.singers}"></label><label>Delivery<select id="delivery">${options([['sing','Singing'],['rhythmic','Rhythmic / rap sketch']],t.delivery||'sing')}</select></label><label>Voice source<select id="voice">${options([['hanami','Hanami · female'],['tiger','TIGER · male / Fresh'],['tiger-vinyl','TIGER · male / Vinyl'],...bank.map(v=>[v.id,'Recorded · '+v.name]),['imported',t.stem?'Recorded/imported voice':'Import a male or female voice…']],t.voice)}</select></label>${bankVoice(t)?`<label>Recorded technique<select id="bank-technique">${options(bankVoice(t).techniques.map(x=>[x,x]),t.bank_technique||'straight')}</select></label>`:''}`:'')+`<label>Level<input aria-label="Section level" type="range" id="gain" min="0" max="1.5" step="0.01" value="${t.gain}"></label><label>Pan<input aria-label="Section pan" type="range" id="pan" min="-1" max="1" step="0.05" value="${t.pan}"></label>`+(isVocal(t)?`<label>Spread<input aria-label="Ensemble spread" type="range" id="spread" min="0" max="1" step="0.05" value="${t.spread}"></label><button id="remove" aria-label="Remove selected section" style="font-size:11px">Remove</button>`:'');
 $('section-name').onchange=e=>{t.name=e.target.value.trim()||names[t.role]||t.role;changed();draw();};
 for(const prop of ['gain','pan','spread'])if($(prop))$(prop).oninput=e=>{t[prop]=Number(e.target.value);changed();};
 if(isVocal(t)){
  if($('bank-technique'))$('bank-technique').onchange=e=>{t.bank_technique=e.target.value;changed();drawControls();};
  $('delivery').onchange=e=>{t.delivery=e.target.value;changed();};
  $('role').onchange=e=>{t.role=e.target.value;changed();draw();};
  $('mode').onchange=e=>{t.singers=e.target.value==='solo'?1:4;changed();draw();};
  $('singers').onchange=e=>{t.singers=Math.max(1,Math.min(8,Math.round(Number(e.target.value)||1)));changed();draw();};
  $('voice').onchange=e=>{if(e.target.value==='imported'&&!t.stem){$('file-stem').click();e.target.value=t.voice;return;}t.voice=e.target.value;if(bankVoice(t))t.bank_technique='straight';if(t.voice==='imported')t.singers=1;changed();draw();};
  $('remove').onclick=()=>{if(!confirm('Remove '+t.name+' and its notes?'))return;project.tracks=project.tracks.filter(x=>x.id!==t.id);if(!project.tracks.length){status('Keep at least one track.',true);project.tracks.push(t);return;}active=project.tracks[0].id;changed();draw();};
  for(const id of ['mode','singers','spread','delivery'])$(id).disabled=t.voice==='imported';
 }
 let hint='';
 if(bankVoice(t)){const v=bankVoice(t);hint=`Recorded ${v.name}. Sampled pitches ${pitchName(v.sampled_range[0])}–${pitchName(v.sampled_range[1])}. Available ${t.bank_technique||'straight'} vowels: ${(v.coverage[t.bank_technique||'straight']||[]).join(', ')}. Other notes are resampled; timbre can change. Create baseline for a fitted vowel phrase.`;}
 else if(isVocal(t)){const range=ranges[t.role]||ranges.soprano;const outside=t.notes.filter(n=>n.pitch<range[0]||n.pitch>range[1]).length;hint=`Suggested ${names[t.role]||t.role} range: ${pitchName(range[0])}–${pitchName(range[1])}. `+(outside?`${outside} note(s) outside this guide. `:'')+(t.voice==='imported'?'Using your recorded/imported voice. Export it from the project start for alignment.':`Voice: ${t.voice==='hanami'?'Hanami · female soprano':'TIGER · male'}. Range labels guide composition; extreme registers need listening checks.`);}
 else hint='Recorded VSCO instrument samples. Change pitch, duration, level and pan below.';
 $('range-hint').textContent=hint;$('lyrics').value=t.notes.map(n=>n.lyric).join(' ');$('lyrics').disabled=!isVocal(t);$('apply-lyrics').disabled=!isVocal(t);
}
function drawRoll(){
 const t=current(),end=Math.max(16,...t.notes.map(n=>n.start+n.duration));
 const lo=Math.max(24,Math.min(60,...t.notes.map(n=>n.pitch))-2),hi=Math.min(96,Math.max(72,...t.notes.map(n=>n.pitch))+2);
 const w=940,h=230,left=42,top=22,bottom=25,dy=(h-top-bottom)/(hi-lo+1),dx=(w-left-12)/end;
 let s='';
 for(let p=lo;p<=hi;p++){const y=top+(hi-p)*dy;s+=`<line x1="${left}" y1="${y}" x2="${w}" y2="${y}" stroke="#24362e"/>`;if(p%12===0||p===lo||p===hi)s+=`<text x="6" y="${y+dy*.75}" font-size="9" fill="#93a698">${pitchName(p)}</text>`;}
 for(let beat=0;beat<=end;beat++){const x=left+beat*dx;s+=`<line x1="${x}" y1="${top}" x2="${x}" y2="${h-bottom}" stroke="${beat%4===0?'#455248':'#22352c'}"/>`;if(beat%4===0)s+=`<text x="${x+3}" y="13" font-size="9" fill="#9eac9c">${Math.floor(beat/4)+1}</text>`;}
 t.notes.forEach(n=>{const x=left+n.start*dx,y=top+(hi-n.pitch)*dy;s+=`<g><rect x="${x}" y="${y+1}" width="${Math.max(3,n.duration*dx-2)}" height="${Math.max(4,dy-2)}" rx="2" fill="${isVocal(t)?'#dbba79':'#91b69f'}"/><title>${esc(n.lyric)} · ${pitchName(n.pitch)} · beat ${n.start}</title><text x="${x+2}" y="${h-7}" font-size="9" fill="#bdc7b8">${esc(n.lyric.slice(0,8))}</text></g>`;});
 $('roll').setAttribute('viewBox',`0 0 ${w} ${h}`);$('roll').innerHTML=s;
}
function drawNotes(){
 const t=current();$('note-count').textContent=t.notes.length+' notes';
 $('notes').innerHTML=t.notes.map((n,i)=>`<tr data-index="${i}"><td><input aria-label="Note ${i+1} start" type="number" min="0" step="0.25" data-prop="start" value="${n.start}"></td><td><input aria-label="Note ${i+1} length" type="number" min="0.03125" max="32" step="0.25" data-prop="duration" value="${n.duration}"></td><td><input aria-label="Note ${i+1} MIDI pitch" type="number" min="24" max="96" data-prop="pitch" value="${n.pitch}" title="${pitchName(n.pitch)}"></td><td><input aria-label="Note ${i+1} word" class="word" data-prop="lyric" value="${esc(n.lyric)}" maxlength="60" ${isVocal(t)?'':'disabled'}></td><td><input aria-label="Note ${i+1} phonemes" class="phonemes" data-prop="phonemes" value="${esc(n.phonemes||'')}" placeholder="e.g. l ay t" ${isVocal(t)?'':'disabled'}></td><td><input type="checkbox" aria-label="Accent note ${i+1}" data-prop="accent" ${n.accent?'checked':''} ${isVocal(t)?'':'disabled'}></td><td><button aria-label="Delete note ${i+1}">×</button></td></tr>`).join('');
 document.querySelectorAll('#notes tr').forEach(row=>{const i=Number(row.dataset.index);row.querySelectorAll('input').forEach(input=>input.onchange=()=>{const prop=input.dataset.prop;t.notes[i][prop]=prop==='accent'?input.checked:['start','duration','pitch'].includes(prop)?Number(input.value):input.value;changed();drawRoll();$('lyrics').value=t.notes.map(n=>n.lyric).join(' ');});row.querySelector('button').onclick=()=>{t.notes.splice(i,1);changed();draw();};});
}
function drawVox(){
 const t=current();$('voice-lab').hidden=!isVocal(t);if(!isVocal(t))return;
 t.vox={...voxDefaults,...t.vox};
 $('vox-controls').innerHTML=voxControls.map(([key,label,min,max,step,unit])=>`<label for="vox-${key}">${label}<output id="vox-value-${key}">${t.vox[key]}${unit}</output><input id="vox-${key}" type="range" min="${min}" max="${max}" step="${step}" value="${t.vox[key]}" ${(t.voice==='imported'&&!['tone','grit','delay'].includes(key))||(bankVoice(t)&&key==='formant')?'disabled':''}></label>`).join('');
 for(const [key,,,,,unit] of voxControls)$('vox-'+key).oninput=e=>{t.vox[key]=Number(e.target.value);$('vox-value-'+key).textContent=t.vox[key]+unit;changed();};
 $('baseline-create').disabled=t.voice==='imported';$('baseline-reset').disabled=!t.baseline;$('baseline-listen').disabled=!t.baseline;$('baseline-info').textContent=t.baseline?'Baseline saved · adjustments leave it intact.':'Create a neutral starting performance for this voice.';
 $('vox-hint').textContent=bankVoice(t)?'Recorded techniques keep their natural expression. Vibrato adds modulation; formant shaping is unavailable for samples.':t.voice==='imported'?'Tone, grit and delay affect your recording. Synthesis controls require a neural voice.':'Glide connects adjacent notes. Rhythmic delivery suppresses vibrato. Formant changes vocal color; pitch remains separate.';
}
function draw(){if(!project)return;if(hardware&&(hardwarePart!==active||hardwareProject!==project)){hardware.reset('Part changed. Note entry disarmed.');hardwarePart=active;hardwareProject=project;}drawSections();drawControls();drawRoll();drawNotes();drawVox();drawPattern();drawBank();drawTuning();$('title').value=project.title;$('tempo').value=project.tempo;$('quality').value=project.quality;$('reverb').value=project.reverb;$('wet').textContent=Math.round(project.reverb*100)+'%';}
async function render(solo=false,override=null,kind='score'){
 if(job)return;const snapshot=clone(override||project);renderKind=kind;if(solo)snapshot.tracks.forEach(t=>t.enabled=t.id===active);
 renderSnapshot=JSON.stringify(project);const result=await api('/api/render',snapshot);job=result.id;
 $('render').disabled=true;$('audition').disabled=true;$('cancel').hidden=false;$('progress').hidden=false;$('progress').value=0;status('Preparing the performance…');poll();
}
async function poll(){
 if(!job)return;
 try{const data=await api('/api/jobs/'+job);status(data.message,data.state==='error');$('progress').value=data.progress;
  if(data.state==='running'){setTimeout(poll,800);return;}
  if(data.state==='complete'){const r=data.result;$('result').hidden=false;$('player').src=`/renders/${r.id}/mix.wav`;$('downloads').innerHTML=`<a download="${safeName()}.wav" href="/renders/${r.id}/mix.wav">↓ Full mix · WAV</a>`+r.stems.map(s=>`<a download="${esc(s)}.wav" href="/renders/${r.id}/${s}.wav">${esc(s)} stem</a>`).join('');$('render-info').textContent=renderKind==='baseline'?'Neutral baseline audition · your adjusted score is unchanged.':renderSnapshot===JSON.stringify(project)?`${r.duration.toFixed(1)} seconds · rendered in ${r.elapsed}s · 44.1 kHz / 24-bit WAV`:'Score changed during rendering · this performance uses the earlier score.';}
 }catch(e){status('Cannot check render: '+e.message,true);}
 job=null;$('render').disabled=false;$('audition').disabled=false;$('cancel').hidden=true;$('progress').hidden=true;
}
$('render').onclick=handle(()=>render());$('audition').onclick=handle(()=>render(true));$('cancel').onclick=handle(()=>api('/api/cancel',{id:job}));
$('title').onchange=e=>{project.title=e.target.value||'Untitled';changed();};$('tempo').onchange=e=>{project.tempo=Number(e.target.value);changed();};$('quality').onchange=e=>{project.quality=e.target.value;changed();};$('reverb').oninput=e=>{project.reverb=Number(e.target.value);$('wet').textContent=Math.round(project.reverb*100)+'%';changed();};
$('add').onclick=()=>{if(project.tracks.length>=16){status('This prototype supports up to 16 parts.',true);return;}const role=$('new-role').value;const source=project.tracks.find(isVocal);const range=ranges[role];const notes=source?clone(source.notes):[];for(const n of notes){while(n.pitch>range[1])n.pitch-=12;while(n.pitch<range[0])n.pitch+=12;}const t={id:role+'-'+Date.now(),role,name:names[role],enabled:true,gain:.5,pan:0,singers:1,spread:.35,voice:['tenor','baritone','bass'].includes(role)?'tiger':'hanami',notes};project.tracks.push(t);active=t.id;changed();draw();status(names[role]+' added as a soloist. Choose Ensemble for multiple singers.');};
$('add-note').onclick=()=>{const t=current();t.notes.push({start:Math.max(0,...t.notes.map(n=>n.start+n.duration)),duration:1,pitch:ranges[t.role]?.[0]||60,lyric:isVocal(t)?'ah':''});changed();draw();};
$('apply-lyrics').onclick=()=>{const t=current(),words=$('lyrics').value.trim().split(/\s+/);if(words.length!==t.notes.length){status(`You have ${words.length} words for ${t.notes.length} notes. Add + where a vowel continues. Nothing changed.`,true);return;}words.forEach((word,i)=>{t.notes[i].lyric=word;delete t.notes[i].phonemes;});changed();draw();status('Lyrics assigned to '+t.name+'.');};
$('about').onclick=()=>$('info').showModal();$('load').onclick=()=>$('file-project').click();
$('save').onclick=handle(async()=>{const p=(await api('/api/validate',project)).project;download(JSON.stringify(p,null,2),safeName()+'.json','application/json');status('Project saved. Imported voice WAVs are stored separately; keep their originals.');});
$('file-project').onchange=handle(async e=>{const f=e.target.files[0];if(!f)return;if(f.size>2_000_000)throw Error('Project file exceeds 2 MB.');const p=(await api('/api/validate',JSON.parse(await f.text()))).project;if(!confirm('Replace the current score with '+p.title+'?'))return;project=p;active=p.tracks[0].id;changed();draw();e.target.value='';status('Project opened.');});
$('demo').onclick=handle(async()=>{if(!confirm('Replace the current score with the example?'))return;project=(await api('/api/state')).demo;active=project.tracks[0].id;changed();draw();});
$('xml-export').onclick=handle(async()=>{const r=await api('/api/musicxml/export',project);download(binary(r.data),safeName()+'.musicxml','application/vnd.recordare.musicxml+xml');status('Enabled vocal sections exported with notes and lyrics.');});
$('midi-import').onclick=()=>$('file-midi').click();$('file-midi').onchange=handle(async e=>{const f=e.target.files[0];if(!f)return;if(f.size>2_000_000)throw Error('Use a MIDI file smaller than 2 MB.');pendingMidi=await api('/api/midi/import',{data:await base64(f)});$('midi-track').innerHTML=pendingMidi.tracks.map((t,i)=>`<option value="${i}">${esc(t.name)} · ${t.notes.length} notes</option>`).join('');$('midi-dialog').showModal();e.target.value='';});
$('midi-cancel').onclick=()=>$('midi-dialog').close();$('midi-confirm').onclick=handle(async()=>{const p=clone(project),t=p.tracks.find(t=>t.id===active);t.notes=pendingMidi.tracks[Number($('midi-track').value)].notes;if($('midi-tempo').checked)p.tempo=pendingMidi.tempo;try{project=(await api('/api/validate',p)).project;}catch(e){alert(e.message);return;}$('midi-dialog').close();changed();draw();status('MIDI imported. Review notes and assign lyrics.');});
async function importStem(file){const t=current();if(!isVocal(t))throw Error('Select a vocal section first.');const r=await api('/api/stem',{project,track:t.id,data:await base64(file)});Object.assign(t,r,{voice:'imported',singers:1});changed();draw();status(`Voice recording assigned to ${t.name}. It plays from the project start.`);}
$('import-stem').onclick=()=>$('file-stem').click();$('file-stem').onchange=handle(async e=>{const f=e.target.files[0];if(!f)return;if(f.size>30_000_000)throw Error('Use a WAV smaller than 30 MB.');await importStem(f);e.target.value='';});
function wavBlob(samples,sampleRate){const out=new ArrayBuffer(44+samples.length*2),v=new DataView(out);function str(at,s){[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));}str(0,'RIFF');v.setUint32(4,36+samples.length*2,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,sampleRate,true);v.setUint32(28,sampleRate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,samples.length*2,true);samples.forEach((x,i)=>v.setInt16(44+i*2,Math.round(Math.max(-1,Math.min(1,x))*32767),true));return new Blob([out],{type:'audio/wav'});}
async function stopRecording(){
 const r=recording;if(!r)return;recording=null;recordBusy=true;$('record').disabled=true;clearInterval(r.timer);
 try{
  r.node.port.onmessage=null;r.node.disconnect();r.source.disconnect();r.stream.getTracks().forEach(t=>t.stop());
  await r.context.close();
  const len=r.chunks.reduce((n,c)=>n+c.length,0);
  if(!len){status('No audio was captured. Check the selected input and try again.',true);return;}
  const all=new Float32Array(len);let offset=0;for(const c of r.chunks){all.set(c,offset);offset+=c.length;}
  recorded=wavBlob(all,r.rate);if($('recording').src)URL.revokeObjectURL($('recording').src);
  $('recording').src=URL.createObjectURL(recorded);$('recording').hidden=false;$('use-notes').disabled=false;$('use-stem').disabled=false;
  $('record-clock').textContent=(len/r.rate).toFixed(1)+' seconds recorded';status('Recording ready. Turn it into notes or use it as the selected section’s voice.');
 }finally{recordBusy=false;$('record').disabled=false;$('record').textContent='● Record mic';$('record').classList.remove('active');hardware?.setRecording(false);}
}
$('record').onclick=handle(async()=>{
 if(recordBusy)return;if(recording){await stopRecording();return;}
 if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone input requires localhost or HTTPS in a supported browser.');
 recordBusy=true;$('record').disabled=true;hardware?.setRecording(true);let stream,context;
 try{
  stream=await navigator.mediaDevices.getUserMedia({audio:hardware.audioConstraints(),video:false});
  context=new AudioContext();await context.audioWorklet.addModule('/recorder.js');await context.resume();
  const source=context.createMediaStreamSource(stream),node=new AudioWorkletNode(context,'cantabile-recorder'),mute=context.createGain();
  mute.gain.value=0;source.connect(node).connect(mute).connect(context.destination);
  const r={stream,context,source,node,chunks:[],rate:context.sampleRate,start:performance.now()};recording=r;
  node.port.onmessage=e=>{if(recording===r)r.chunks.push(e.data);};
  for(const track of stream.getTracks())track.addEventListener('ended',()=>{if(recording===r)stopRecording().catch(e=>status(e.message,true));},{once:true});
  r.timer=setInterval(()=>{const seconds=(performance.now()-r.start)/1000;$('record-clock').textContent=seconds.toFixed(1)+' / 60 seconds';if(seconds>=60)stopRecording().catch(e=>status(e.message,true));},100);
  $('record').textContent='■ Stop recording';$('record').classList.add('active');status('Recording the selected input. Sing one melody at a time.');
 }catch(e){
  stream?.getTracks().forEach(t=>t.stop());if(context)await context.close();
  throw Error(e.name==='NotAllowedError'?'Microphone permission was denied. Allow it in your browser, then try Record mic again.':['NotFoundError','OverconstrainedError'].includes(e.name)?'Selected audio input is unavailable. Reconnect it, refresh inputs, and select a device.':e.message);
 }finally{recordBusy=false;$('record').disabled=false;hardware?.setRecording(!!recording);}
});
$('use-stem').onclick=handle(()=>importStem(recorded));
$('use-notes').onclick=handle(async()=>{if(!recorded)return;status('Finding the guide melody…');const r=await api('/api/mic/notes',{data:await base64(recorded),tempo:project.tempo});if(!confirm(`Replace ${current().name} with ${r.notes.length} detected notes? You can edit them afterward.`))return;const p=clone(project),t=p.tracks.find(t=>t.id===active);t.notes=r.notes;if(t.voice==='imported')t.voice=['tenor','baritone','bass'].includes(t.role)?'tiger':'hanami';project=(await api('/api/validate',p)).project;changed();draw();status(r.message);});
let selectedStep=0;
function newPattern(preset='hook'){
 const pitch=['tenor','baritone','bass'].includes(current().role)?55:64;
 const cells=Array.from({length:16},()=>({on:false,onset:'',vowel:'ah',coda:'',label:'',pitch,gate:.85,accent:false,tie:false,ratchet:1}));
 const set=(i,onset,vowel,coda,label,accent=false)=>Object.assign(cells[i],{on:true,onset,vowel,coda,label,accent});
 if(preset==='hook'){
  set(0,'b r','ih','ng','bring',true);set(4,'dh','ae','t','that');set(8,'b','iy','t','beat',true);set(12,'b','ae','k','back',true);
  for(const i of [1,5,9,13])Object.assign(cells[i],{on:true,tie:true,label:'hold'});
 }else if(preset==='percussive'){
  for(const i of [0,6,8,14])set(i,'b','uw','m','boom',i===0||i===8);
  for(const i of [4,12])set(i,'t s','','','tss',true);
  for(const i of [3,7,11,15])set(i,'k','ah','','kah');
 }else set(0,'b','ah','','bah',true);
 return {division:.25,swing:0,start:0,repeats:1,cells};
}
function drawPattern(){
 const t=current();$('sequencer').hidden=!isVocal(t);if(!isVocal(t))return;
 if(!t.pattern)t.pattern=newPattern();const p=t.pattern;
 $('pattern-division').value=String(p.division);$('pattern-repeats').value=p.repeats;$('pattern-swing').value=p.swing;$('swing-value').textContent=Math.round(p.swing*100)+'%';
 $('step-grid').innerHTML=p.cells.map((c,i)=>`<button class="step ${c.on?'active-step':''} ${c.accent?'accented':''} ${i===selectedStep?'selected-step':''}" data-step="${i}" aria-label="Step ${i+1}: ${esc(c.on?(c.tie?'hold':c.label||[c.onset,c.vowel,c.coda].filter(Boolean).join(' ')):'rest')}${c.accent?', accented':''}" aria-pressed="${i===selectedStep}"><small>${String(i+1).padStart(2,'0')} ${c.accent?'▲ ACCENT':''}</small><strong>${c.on?esc(c.tie?'— hold':c.label||[c.onset,c.vowel,c.coda].filter(Boolean).join('·')):'·'}</strong><small>${c.on?pitchName(c.pitch):'REST'}</small></button>`).join('');
 $('step-grid').querySelectorAll('button').forEach(b=>b.onclick=()=>{selectedStep=Number(b.dataset.step);drawPattern();$('step-on').focus();});
 const c=p.cells[selectedStep];$('step-title').textContent='Step '+String(selectedStep+1).padStart(2,'0');
 for(const prop of ['on','accent','tie'])$('step-'+prop).checked=c[prop];
 for(const prop of ['onset','vowel','coda','pitch','gate','label'])$('step-'+prop).value=c[prop];
 $('step-ratchet').value=c.ratchet||1;$('step-ratchet').disabled=c.tie;
 for(const prop of ['onset','vowel','coda','label'])$('step-'+prop).disabled=c.tie;
}
for(const prop of ['on','accent','tie','onset','vowel','coda','pitch','gate','label','ratchet'])$('step-'+prop).onchange=e=>{const c=current().pattern.cells[selectedStep];c[prop]=['on','accent','tie'].includes(prop)?e.target.checked:['pitch','gate','ratchet'].includes(prop)?Number(e.target.value):e.target.value;if(c.tie)c.ratchet=1;changed();drawPattern();$('pattern-status').textContent='Pattern edited. Send it to this part to update its notes.';};
for(const prop of ['division','repeats','swing'])$('pattern-'+prop).onchange=e=>{current().pattern[prop]=Number(e.target.value);changed();drawPattern();};
$('pattern-load').onclick=()=>{current().pattern=newPattern($('pattern-preset').value);selectedStep=0;changed();drawPattern();$('pattern-status').textContent='Pattern loaded. Send it to this part to replace its notes.';};
$('pattern-apply').onclick=handle(async()=>{
 try{const t=current();if(!isVocal(t))throw Error('Select a vocal part.');const result=await api('/api/pattern',t.pattern);
  if(!confirm('Replace the notes in '+t.name+' with this vocal pattern?'))return;
  const p=clone(project),dest=p.tracks.find(x=>x.id===active);dest.notes=result.notes;dest.delivery='rhythmic';
  if(dest.voice==='imported')dest.voice=['tenor','baritone','bass'].includes(dest.role)?'tiger':'hanami';
  project=(await api('/api/validate',p)).project;changed();draw();$('pattern-status').textContent=`${result.notes.length} syllable/hold events sent to ${current().name}. Use Solo this part to render.`;status('Rhythmic pattern is in the score. Ready to render.');
 }catch(e){$('pattern-status').textContent=e.message;throw e;}
});
$('vox-apply').onclick=()=>{
 const t=current(),preset=$('vox-preset').value;
 const settings={choir:{},tight:{vibrato:0,glide:.015,accent_gain:1.9,formant:-.5,tone:.2,grit:.1,delay:.05},wide:{vibrato:.1,glide:.07,delay:.175,grit:.1},rough:{vibrato:0,formant:-1.5,grit:.55,tone:-.15,delay:.125,accent_gain:1.9}};
 t.vox={...voxDefaults,...settings[preset]};t.delivery=['tight','rough'].includes(preset)?'rhythmic':'sing';
 if(preset==='wide'&&t.voice!=='imported'){t.singers=4;t.spread=.8;}
 changed();draw();status('Vocal preset applied. Every control remains editable.');
};

function drawBank(){
 $('bank-panel').hidden=!bank.length;$('bank-count').textContent=bank.length+' singers';
 const filter=$('bank-filter').value;
 $('bank-cards').innerHTML=bank.filter(v=>filter==='all'||v.gender===filter).map(v=>`<article class="bank-card"><strong>${esc(v.name)}</strong><small>${esc(v.gender)} · ${v.samples?.length||v.techniques.length+' techniques'} · ${pitchName(v.sampled_range[0])}–${pitchName(v.sampled_range[1])}</small><div class="row"><button data-bank-preview="${v.id}">▶ Baseline</button><button data-bank-use="${v.id}">Use voice</button></div></article>`).join('');
 document.querySelectorAll('[data-bank-preview]').forEach(b=>b.onclick=()=>{$('bank-preview').hidden=false;$('bank-preview').src='/vocal-bank/previews/'+b.dataset.bankPreview+'.wav';$('bank-preview').play().catch(()=>{});});
 document.querySelectorAll('[data-bank-use]').forEach(b=>b.onclick=()=>{if(!isVocal(current())){status('Select or add a vocal section first.',true);return;}const v=bank.find(x=>x.id===b.dataset.bankUse);current().voice=v.id;current().bank_technique='straight';changed();draw();status(v.name+' selected. Create baseline to hear its fitted vowel phrase.');});
}
$('bank-filter').onchange=drawBank;
$('baseline-create').onclick=handle(async()=>{
 const t=current();const b=(await api('/api/voice/baseline',{voice:t.voice})).baseline;
 if(!confirm('Create a neutral vowel/lyric baseline for '+t.name+'? This replaces this part’s notes and voice settings.'))return;
 Object.assign(t,clone(b));t.baseline=clone(b);changed();draw();await render(true);
});
$('baseline-reset').onclick=()=>{const t=current();if(!t.baseline||!confirm('Restore this voice’s saved baseline notes and settings?'))return;Object.assign(t,clone(t.baseline));changed();draw();status('Baseline restored.');};
$('baseline-listen').onclick=handle(async()=>{const t=current();if(!t.baseline)return;const p=clone(project);p.tracks.forEach(x=>{x.enabled=x.id===t.id;if(x.enabled)Object.assign(x,clone(t.baseline));});await render(false,p,'baseline');});


const tuningDefaults={enabled:false,key:0,scale:'chromatic',strength:1,speed_ms:35,wet:1};
$('tune-key').innerHTML=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'].map((x,i)=>`<option value="${i}">${x}</option>`).join('');
function drawTuning(){
 const t=current();$('tuning-panel').hidden=t.voice!=='imported';if(t.voice!=='imported')return;
 t.tuning={...tuningDefaults,...t.tuning};$('tune-enabled').checked=t.tuning.enabled;$('tune-key').value=t.tuning.key;$('tune-scale').value=t.tuning.scale;
 for(const prop of ['strength','speed_ms','wet']){$('tune-'+prop).value=t.tuning[prop];$('tune-'+prop+'-value').textContent=prop==='speed_ms'?t.tuning[prop]+' ms':Math.round(t.tuning[prop]*100)+'%';}
 const url='/imports/'+t.stem+'.wav';if($('input-original').getAttribute('src')!==url)$('input-original').src=url;
}
for(const prop of ['enabled','key','scale','strength','speed_ms','wet'])$('tune-'+prop).onchange=e=>{const t=current();t.tuning[prop]=prop==='enabled'?e.target.checked:prop==='scale'?e.target.value:Number(e.target.value);changed();drawTuning();};
$('tune-apply').onclick=()=>{const t=current();t.tuning={...tuningDefaults,...t.tuning,enabled:true,strength:$('tune-preset').value==='hard'?1:.65,speed_ms:$('tune-preset').value==='hard'?0:100,wet:1};changed();drawTuning();status('Pitch correction configured. Solo this part to hear it.');};

hardware=window.CantabileHardware.mount({
 recording:()=>!!recording||recordBusy,
 stop:()=>{for(const id of ['player','bank-preview','recording','input-original']){const player=$(id);if(player.getAttribute('src')){player.pause();player.currentTime=0;}}},
 play:()=>{const player=$('player');if(!player.getAttribute('src')){status('Render a performance first, then play it from your pad.',true);return;}player.currentTime=0;player.play().catch(()=>status('Press Play latest render once in the page to allow audio playback.',true));},
 note:(pitch,velocity,duration,vowel)=>{
  if(!project)throw Error('Wait for the project to load.');const t=current();
  if(!isVocal(t)||t.voice==='imported')throw Error('Choose a generated vocal part for MIDI note entry.');
  if(pitch<24||pitch>96)throw Error('Use MIDI pitches 24–96; adjust the keyboard octave.');
  const start=Math.max(0,...t.notes.map(n=>n.start+n.duration));
  if(t.notes.length>=256||start>160||(start+duration)*60/project.tempo>60)throw Error('This part has reached the prototype note or 60-second limit.');
  const phonemes={a:'aa',e:'eh',i:'iy',o:'ow',u:'uw'};
  t.notes.push({start,duration,pitch,lyric:vowel,phonemes:phonemes[vowel],accent:velocity>=100});changed();draw();
 },
 vowel:v=>{if(!project||!isVocal(current()))return;const cell=current().pattern?.cells[selectedStep];if(cell&&!cell.tie){cell.vowel={a:'aa',e:'eh',i:'iy',o:'ow',u:'uw'}[v];changed();drawPattern();}},
 next:()=>{if(!project||!isVocal(current()))return;selectedStep=(selectedStep+1)%16;drawPattern();},
 control:(target,value,mode,map)=>{
  if(!project)throw Error('Wait for the project to load.');
  const id=target==='strength'?'tune-strength':['gain','pan'].includes(target)?target:'vox-'+target;
  const input=$(id);
  if(!input||input.disabled||(target==='strength'&&current().voice!=='imported')||(!['gain','pan','strength'].includes(target)&&!isVocal(current())))throw Error('This control is unavailable for the selected voice.');
  input.value=map(value,mode,Number(input.value),Number(input.min),Number(input.max),Number(input.step));
  input.dispatchEvent(new Event(target==='strength'?'change':'input'));
 }
});
window.addEventListener('beforeunload',()=>recording?.stream.getTracks().forEach(t=>t.stop()));
(async()=>{try{const state=await api('/api/state');ranges=state.ranges;bank=state.bank||[];project=state.demo;const saved=localStorage.getItem('cantabile-project-v1');if(saved){try{project=(await api('/api/validate',JSON.parse(saved))).project;}catch(e){status('Saved draft needs repair; the example is open. Your saved data has not been overwritten. '+e.message,true);}}active=project.tracks[0].id;$('engine-status').textContent=state.voiceInstalled&&state.tigerInstalled?'English neural voices ready · male + female · local rendering':`${bank.length} recorded voices ready · neural lyrics need setup-voices-windows.bat`;draw();}catch(e){status('Cannot open the local engine: '+e.message,true);}})();
