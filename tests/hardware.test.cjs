const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const core=require('../web/hardware.js');
const root=path.resolve(__dirname,'..');
const port=(id,name='MPK mini IV',manufacturer='Akai')=>({id,name,manufacturer,state:'connected',onmidimessage:null,close:async()=>{}});
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
function fixture(t,saved=null){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'http://localhost',runScripts:'outside-only'});
 t.after(()=>dom.window.close());const w=dom.window,$=id=>w.document.getElementById(id);
 const a=port('a'),b=port('b','SP-404MKII','Roland');const access={inputs:new Map([[a.id,a],[b.id,b]]),onstatechange:null};
 const calls={notes:[],controls:[],vowels:[],play:0,stop:0,requests:[],media:[],stopped:0};
 Object.defineProperty(w.navigator,'requestMIDIAccess',{configurable:true,value:async options=>{calls.requests.push(options);return access;}});
 const media={getUserMedia:async options=>{calls.media.push(options);return {getTracks:()=>[{stop:()=>calls.stopped++}]};},enumerateDevices:async()=>[{kind:'audioinput',deviceId:'roland',label:'SP-404MKII'},{kind:'audioinput',deviceId:'laptop',label:'Laptop microphone'}],addEventListener:()=>{},removeEventListener:()=>{}};
 Object.defineProperty(w.navigator,'mediaDevices',{configurable:true,value:media});
 if(saved)w.localStorage.setItem('cantabile-hardware-v1',JSON.stringify(saved));
 w.eval(fs.readFileSync(path.join(root,'web/hardware.js'),'utf8'));
 const bridge={recording:()=>false,stop:()=>calls.stop++,play:()=>calls.play++,note:(...args)=>calls.notes.push(args),control:(...args)=>calls.controls.push(args),vowel:v=>calls.vowels.push(v),next:()=>{}};
 const controller=w.CantabileHardware.mount(bridge);
 const change=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new w.Event('change'));};
 const emit=(p,data)=>p.onmidimessage?.({data:new Uint8Array(data)});
 const connect=async()=>{$('midi-connect').click();await tick();change('midi-input','a');};
 return {w,$,a,b,access,calls,controller,bridge,media,change,emit,connect};
}
test('decode filters malformed/system data and handles all note-off forms',()=>{
 assert.equal(core.decode([0x90,60,0]).kind,'off');assert.equal(core.decode([0x8f,60,55]).kind,'off');
 assert.deepEqual(core.decode([0xb9,17,127]),{kind:'cc',channel:10,number:17,value:127});
 for(const value of [[],[0x90,60],[0xf8,0,0],[0x90,128,1],[0x90,-1,1],[0x90,60,NaN],[0xc0,1,2]])assert.equal(core.decode(value),null);
});
test('device relinking refuses ambiguous identities',()=>{
 const remembered=port('old'),a=port('new');assert.equal(core.resolveDevice(remembered,[a]),a);
 assert.equal(core.resolveDevice(remembered,[a,port('other')]),null);
 assert.equal(core.resolveDevice(remembered,[port('new','Other')]),null);
});
test('mapping storage validates messages, targets, channels, modes and duplicates',()=>{
 const binding={target:'gain',kind:'cc',channel:1,number:7,mode:'absolute'};
 const clean=core.cleanPrefs({version:1,profiles:[{device:port('a'),bindings:[binding,binding,{...binding,number:999},{...binding,target:'script'},{...binding,kind:'note'}]}]});
 assert.equal(clean.profiles[0].bindings.length,1);assert.equal(core.cleanPrefs({version:9}).profiles.length,0);
});
test('absolute and relative knobs clamp at control bounds',()=>{
 assert.equal(core.controlValue(127,'absolute',0,-5,5,.1),5);
 assert.equal(core.controlValue(0,'absolute',0,-5,5,.1),-5);
 assert.equal(core.controlValue(127,'twos',.5,0,1,.01),.49);
 assert.equal(core.controlValue(1,'twos',1,0,1,.01),1);
 assert.equal(core.controlValue(63,'offset',.5,0,1,.01),.49);
 assert.equal(core.controlValue(65,'offset',.5,0,1,.01),.51);
});
test('MIDI permission is explicit; step entry is armed, channel-filtered and key-release gated',async t=>{
 const x=fixture(t);assert.equal(x.calls.requests.length,0);await x.connect();assert.equal(x.calls.requests[0].sysex,false);
 x.emit(x.a,[0x90,60,120]);assert.equal(x.calls.notes.length,0);x.emit(x.a,[0x80,60,0]);
 x.$('midi-arm').checked=true;x.emit(x.a,[0x90,60,120]);x.emit(x.a,[0x90,60,120]);assert.equal(x.calls.notes.length,1);
 x.emit(x.a,[0x90,60,0]);x.emit(x.a,[0x90,60,70]);assert.equal(x.calls.notes.length,2);
 x.change('midi-channel','2');assert.equal(x.$('midi-arm').checked,false);x.$('midi-arm').checked=true;
 x.emit(x.a,[0x90,61,100]);assert.equal(x.calls.notes.length,2);x.emit(x.a,[0x91,61,100]);assert.equal(x.calls.notes.length,3);
});
test('learning consumes the event; pads and keyboard share notes without sharing mappings',async t=>{
 const x=fixture(t);await x.connect();x.change('midi-target','vowel:u');x.$('midi-learn').click();
 x.emit(x.a,[0x99,36,100]);assert.equal(x.calls.notes.length,0);assert.equal(x.calls.vowels.length,0);
 x.emit(x.a,[0x89,36,0]);x.$('midi-arm').checked=true;x.emit(x.a,[0x99,36,100]);assert.equal(x.calls.vowels[0],'u');assert.equal(x.calls.notes.length,0);
 x.emit(x.a,[0x90,36,100]);assert.equal(x.calls.notes.length,1);
 const saved=JSON.parse(x.w.localStorage.getItem('cantabile-hardware-v1'));assert.equal(saved.profiles[0].bindings[0].channel,10);
 const restored=fixture(t,saved);restored.$('midi-connect').click();await tick();assert.equal(restored.$('midi-input').value,'a');
 restored.emit(restored.a,[0x99,36,100]);assert.equal(restored.calls.vowels[0],'u');assert.equal(restored.$('midi-arm').checked,false);
});
test('knob learning ignores note messages, remembers encoder mode and isolates devices',async t=>{
 const x=fixture(t);await x.connect();x.change('midi-target','grit');x.change('midi-encoder','twos');x.$('midi-learn').click();
 x.emit(x.a,[0x90,55,100]);assert.equal(x.$('midi-learn').textContent,'Cancel learning');
 x.emit(x.a,[0xb0,17,1]);assert.equal(x.calls.controls.length,0);x.emit(x.a,[0xb0,17,127]);
 assert.equal(x.calls.controls[0][0],'grit');assert.equal(x.calls.controls[0][2],'twos');
 x.change('midi-input','b');x.emit(x.b,[0xb0,17,1]);assert.equal(x.calls.controls.length,1);
 x.change('midi-input','a');x.emit(x.a,[0xb0,17,1]);assert.equal(x.calls.controls.length,2);
});
test('disconnect, replacement objects and reconnect remove stale handlers and disarm',async t=>{
 const x=fixture(t);await x.connect();x.$('midi-arm').checked=true;const stale=x.a.onmidimessage;
 x.a.state='disconnected';x.access.onstatechange();assert.equal(x.a.onmidimessage,null);assert.equal(x.$('midi-arm').checked,false);
 stale({data:new Uint8Array([0x90,60,100])});assert.equal(x.calls.notes.length,0);
 const replacement=port('a');x.access.inputs.set('a',replacement);x.access.onstatechange();assert.equal(typeof replacement.onmidimessage,'function');
 x.$('midi-arm').checked=true;x.emit(replacement,[0x90,60,100]);assert.equal(x.calls.notes.length,1);
 x.$('midi-panic').click();assert.equal(x.$('midi-arm').checked,false);x.$('midi-disconnect').click();assert.equal(replacement.onmidimessage,null);assert.equal(x.access.onstatechange,null);
});
test('disconnect during a pending permission request cannot reconnect later',async t=>{
 const x=fixture(t);let resolve;Object.defineProperty(x.w.navigator,'requestMIDIAccess',{value:()=>new Promise(r=>{resolve=r;})});
 x.$('midi-connect').click();x.$('midi-disconnect').click();resolve(x.access);await tick();
 assert.equal(x.access.onstatechange,null);assert.equal(x.a.onmidimessage,null);assert.equal(x.$('midi-arm').disabled,true);
});
test('denied MIDI permission and unavailable storage remain recoverable',async t=>{
 const x=fixture(t);Object.defineProperty(x.w.navigator,'requestMIDIAccess',{value:async()=>{throw Object.assign(Error('denied'),{name:'NotAllowedError'});},configurable:true});
 x.$('midi-connect').click();await tick();assert.match(x.$('midi-status').textContent,/permission denied/);assert.equal(x.$('midi-connect').disabled,false);
 Object.defineProperty(x.w.navigator,'requestMIDIAccess',{value:async()=>x.access});
 x.w.Storage.prototype.setItem=()=>{throw Error('quota');};await x.connect();x.change('midi-target','play');x.$('midi-learn').click();x.emit(x.a,[0x99,40,100]);
 x.emit(x.a,[0x89,40,0]);x.emit(x.a,[0x99,40,100]);assert.equal(x.calls.play,1);assert.match(x.$('midi-status').textContent,/storage is unavailable/);
});
test('audio enumeration stops permission stream, saves exact input, and preserves missing selection',async t=>{
 const x=fixture(t);assert.equal(x.calls.media.length,0);x.$('audio-refresh').click();await tick();assert.equal(x.calls.stopped,1);
 x.change('audio-input','roland');assert.equal(x.controller.audioConstraints().deviceId.exact,'roland');
 x.media.enumerateDevices=async()=>[];x.$('audio-refresh').click();await tick();assert.equal(x.controller.audioConstraints().deviceId.exact,'roland');
 assert.match(x.$('audio-input').selectedOptions[0].textContent,/unavailable/);
 x.controller.setRecording(true);assert.equal(x.$('audio-input').disabled,true);assert.equal(x.$('audio-refresh').disabled,true);
 x.controller.setRecording(false);assert.equal(x.$('audio-input').disabled,false);
});
