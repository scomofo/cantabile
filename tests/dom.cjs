// Interface logic checks without browser hardware, layout or audio permissions.
const {JSDOM}=require('jsdom');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
function waitForServer(server){
 return new Promise((resolve,reject)=>{
  let output='';
  const finish=error=>{
   clearTimeout(timer);
   server.stdout.off('data',onOutput);server.stderr.off('data',onOutput);
   server.off('error',onError);server.off('exit',onExit);
   if(error)reject(error);else resolve();
  };
  const onOutput=data=>{output+=data.toString();if(output.includes('ready at'))finish();};
  const onError=error=>finish(error);
  const onExit=code=>finish(Error(`Server exited (${code}): ${output}`));
  const timer=setTimeout(()=>finish(Error(`Server start timeout: ${output}`)),20000);
  server.stdout.on('data',onOutput);server.stderr.on('data',onOutput);
  server.once('error',onError);server.once('exit',onExit);
 });
}
(async()=>{
 const server=spawn(process.env.PYTHON||'python',[path.join(root,'app.py'),'--no-browser','--port','8775'],{cwd:root});
 let dom;
 try{
  await waitForServer(server);
  dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'http://127.0.0.1:8775',runScripts:'outside-only'});
  const w=dom.window;const $=id=>w.document.getElementById(id);
  w.fetch=(url,options)=>fetch('http://127.0.0.1:8775'+url,options);
  w.confirm=()=>true;w.alert=()=>{};
  // Use one score whether optional neural models are installed or absent.
  // Only the included recorded bank is rendered during this interface test.
  w.localStorage.setItem('cantabile-project-v1',fs.readFileSync(path.join(root,'examples/hold-the-light.json'),'utf8'));
  w.eval(fs.readFileSync(path.join(root,'web/hardware.js'),'utf8'));
  w.eval(fs.readFileSync(path.join(root,'web/app.js'),'utf8'));
  for(let i=0;i<100&&!$('sections').children.length;i++)await pause(20);
  assert.equal($('sections').children.length,5);
  const change=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new w.Event('change'));};
  for(const role of ['soprano','mezzo','alto','tenor','baritone','bass']){
   $('new-role').value=role;$('add').click();assert.equal($('mode').value,'solo');
   change('mode','ensemble');assert.equal($('singers').value,'4');
   change('mode','solo');assert.equal($('singers').value,'1');
  }
  change('voice','hanami');assert.equal(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).voice,'hanami');
  change('voice','tiger');assert.equal(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).voice,'tiger');
  const before=JSON.stringify(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).notes);$('lyrics').value='too short';$('apply-lyrics').click();
  assert.equal(JSON.stringify(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).notes),before);
  const words=Array(13).fill('sing').join(' ');$('lyrics').value=words;$('apply-lyrics').click();
  assert.equal(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).notes[0].lyric,'sing');
  change('section-name','My male baritone');assert.equal($('part-title').textContent,'My male baritone');
  assert.equal(JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1).name,'My male baritone');
  assert($('roll').innerHTML.includes('<rect'));assert.equal($('notes').children.length,13);
  const savedTrack=()=>JSON.parse(w.localStorage.getItem('cantabile-project-v1')).tracks.at(-1);
  $('vox-preset').value='rough';$('vox-apply').click();
  assert.equal(savedTrack().vox.grit,.55);assert.equal($('delivery').value,'rhythmic');
  $('vox-formant').value='-2';$('vox-formant').dispatchEvent(new w.Event('input'));
  assert.equal(savedTrack().vox.formant,-2);
  assert.equal($('step-grid').children.length,16);
  change('pattern-repeats','2');change('pattern-swing','0.2');
  change('step-ratchet','2');$('pattern-apply').click();
  for(let i=0;i<100&&!$('pattern-status').textContent.includes('events sent');i++)await pause(20);
  assert($('pattern-status').textContent.includes('events sent'),$('pattern-status').textContent);
  assert.equal(savedTrack().notes.length,18);assert.equal(savedTrack().notes[2].lyric,'+');
  assert(savedTrack().notes[0].accent);assert.equal(savedTrack().notes[0].phonemes,'b r ih ng');
  const accent=$('notes').querySelector('[data-prop="accent"]');accent.checked=false;accent.dispatchEvent(new w.Event('change'));
  assert.equal(savedTrack().notes[0].accent,false);
  assert.equal($('bank-cards').children.length,20);
  change('bank-filter','female');assert.equal($('bank-cards').children.length,9);
  change('voice','vs-f5');assert($('bank-technique'));assert.equal($('vox-formant').disabled,true);
  $('baseline-create').click();
  for(let i=0;i<200&&(!savedTrack().baseline||$('render').disabled);i++)await pause(20);
  assert.equal(savedTrack().baseline.voice,'vs-f5');assert.equal(savedTrack().notes.length,5);
  $('vox-grit').value='.4';$('vox-grit').dispatchEvent(new w.Event('input'));
  assert.equal(savedTrack().baseline.vox.grit,0);assert.equal(savedTrack().vox.grit,.4);
  $('baseline-reset').click();assert.equal(savedTrack().vox.grit,0);
  // Exercise the real app bridge, not just the hardware controller in isolation.
  for(const id of ['player','bank-preview','recording','input-original']){$(id).pause=()=>{};$(id).play=async()=>{};}
  const midiPort={id:'akai',name:'MPK mini IV',manufacturer:'Akai',state:'connected',close:async()=>{}};
  const midiAccess={inputs:new Map([['akai',midiPort]])};
  Object.defineProperty(w.navigator,'requestMIDIAccess',{value:async()=>midiAccess});
  $('midi-connect').click();await pause(10);change('midi-input','akai');
  const hit=(status,n,v)=>midiPort.onmidimessage({data:new Uint8Array([status,n,v])});
  change('midi-target','vowel:u');$('midi-learn').click();hit(0x99,36,100);hit(0x89,36,0);hit(0x99,36,100);
  assert.equal($('midi-vowel').value,'u');assert.equal(savedTrack().notes.length,5);
  $('midi-arm').checked=true;hit(0x90,60,120);hit(0x80,60,0);
  assert.equal(savedTrack().notes.length,6);assert.equal(savedTrack().notes.at(-1).lyric,'u');assert.equal(savedTrack().notes.at(-1).phonemes,'uw');assert.equal(savedTrack().notes.at(-1).accent,true);
  const validateResponse=await fetch('http://127.0.0.1:8775/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:w.localStorage.getItem('cantabile-project-v1')});
  assert.equal(validateResponse.status,200);
  change('midi-target','grit');$('midi-learn').click();hit(0xb0,17,0);hit(0xb0,17,127);assert.equal(savedTrack().vox.grit,1);
  change('midi-target','formant');$('midi-learn').click();hit(0xb0,18,0);hit(0xb0,18,127);assert.equal(savedTrack().vox.formant,0);assert($('midi-status').textContent.includes('unavailable'));
  const count=savedTrack().notes.length;$('midi-arm').checked=true;hit(0x90,12,100);assert.equal(savedTrack().notes.length,count);assert($('midi-status').textContent.includes('24–96'));
  $('midi-panic').click();assert.equal($('midi-arm').checked,false);$('midi-disconnect').click();assert.equal(midiPort.onmidimessage,null);
  const recordingBytes=fs.readFileSync(path.join(root,'tests/fixtures/mic-guide.wav'));
  Object.defineProperty($('file-stem'),'files',{configurable:true,value:[{size:recordingBytes.length,arrayBuffer:async()=>recordingBytes.buffer.slice(recordingBytes.byteOffset,recordingBytes.byteOffset+recordingBytes.byteLength)}]});
  $('file-stem').dispatchEvent(new w.Event('change'));
  for(let i=0;i<100&&savedTrack().voice!=='imported';i++)await pause(20);
  assert.equal(savedTrack().voice,'imported');assert.equal($('tuning-panel').hidden,false);
  $('tune-preset').value='hard';$('tune-apply').click();
  assert.equal(savedTrack().tuning.enabled,true);assert.equal(savedTrack().tuning.speed_ms,0);
  change('tune-key','7');change('tune-scale','minor');assert.equal(savedTrack().tuning.key,7);
  assert($('input-original').src.includes('/imports/'));
  // Permission failure must leave recording inactive and present a useful error.
  Object.defineProperty(w.navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{const e=Error('denied');e.name='NotAllowedError';throw e;}}});
  $('record').click();await pause(50);assert($('status').textContent.includes('permission was denied'));
  assert.equal($('record').classList.contains('active'),false);
  // Selected-device constraints and sequential recordings with fake Web Audio.
  let stopped=0,closed=0,requests=[],nodes=[],ended;
  const tracks=()=>[{stop:()=>stopped++,addEventListener:(name,callback)=>{if(name==='ended')ended=callback;}}];
  const media={getUserMedia:async options=>{requests.push(options);return {getTracks:tracks};},enumerateDevices:async()=>[{kind:'audioinput',deviceId:'sp404',label:'SP-404MKII'}]};
  Object.defineProperty(w.navigator,'mediaDevices',{configurable:true,value:media});
  $('audio-refresh').click();await pause(10);assert.equal(stopped,1);change('audio-input','sp404');
  const audioNode=()=>({connect:node=>node,disconnect:()=>{}});
  w.AudioContext=class{constructor(){this.sampleRate=16000;this.audioWorklet={addModule:async()=>{}};}resume(){return Promise.resolve();}close(){closed++;return Promise.resolve();}createMediaStreamSource(){return audioNode();}createGain(){return {...audioNode(),gain:{value:1}};}};
  w.AudioWorkletNode=class{constructor(){Object.assign(this,audioNode());this.port={};nodes.push(this);}};
  w.URL.createObjectURL=()=> 'blob:recording';w.URL.revokeObjectURL=()=>{};
  for(let take=0;take<2;take++){
   $('record').click();$('record').click();await pause(10);
   assert.equal(requests.length,take+2);assert.equal(requests.at(-1).audio.deviceId.exact,'sp404');assert.equal($('audio-input').disabled,true);
   nodes.at(-1).port.onmessage({data:new Float32Array(1600)});
   if(take===0)$('record').click();else ended();await pause(10);
   assert.equal($('record').classList.contains('active'),false);assert.equal($('audio-input').disabled,false);
  }
  assert.equal(closed,2);assert.equal(stopped,3);assert.equal($('use-stem').disabled,false);
  media.getUserMedia=async()=>{throw Object.assign(Error('missing'),{name:'OverconstrainedError'});};
  $('record').click();await pause(10);assert($('status').textContent.includes('Selected audio input is unavailable'));assert.equal($('record').disabled,false);
  console.log('PASS: six ranges; solo/ensemble; male/female; lyric guard; names/autosave; score SVG/table; voice presets/sliders; 16-step syllables, swing, repeats, holds, accents and API score transfer; bank catalog, baseline render/reset, recording import, correction controls; microphone denial feedback; live MIDI bridge, learned controls, selected audio input and repeated capture cleanup.');
 }finally{dom?.window.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
