/* Cantabile hardware controls. Device identity/lifecycle patterns adapted from Padlab. */
'use strict';
(() => {
  const KEY = 'cantabile-hardware-v1';
  const vowels = ['a', 'e', 'i', 'o', 'u'];
  const targets = [
    ...vowels.map(v => ['vowel:' + v, 'Vowel ' + v, 'note']),
    ['next', 'Next sequencer step', 'note'], ['play', 'Play latest render', 'note'],
    ['stop', 'Stop playback', 'note'],
    ['gain', 'Part level', 'cc'], ['pan', 'Part pan', 'cc'],
    ['vibrato', 'Vibrato depth', 'cc'], ['formant', 'Formant', 'cc'],
    ['glide', 'Glide', 'cc'], ['accent_gain', 'Accent strength', 'cc'],
    ['tone', 'Tone', 'cc'], ['grit', 'Grit', 'cc'], ['delay', 'Delay', 'cc'],
    ['strength', 'Input tuning strength', 'cc'],
  ];
  function decode(data) {
    if (!data || data.length !== 3 || !Array.from(data).every(Number.isInteger)) return null;
    const [status, number, value] = data;
    if (status < 128 || status > 239 || number < 0 || number > 127 || value < 0 || value > 127) return null;
    const kind = status & 240;
    if (![128, 144, 176].includes(kind)) return null;
    return {kind: kind === 176 ? 'cc' : kind === 128 || value === 0 ? 'off' : 'note', channel: (status & 15) + 1, number, value};
  }
  function resolveDevice(saved, inputs) {
    if (!saved) return null;
    const direct = inputs.find(x => x.id === saved.id);
    if (direct) return direct;
    const same = inputs.filter(x => x.name === saved.name && x.manufacturer === saved.manufacturer);
    return saved.name && same.length === 1 ? same[0] : null;
  }
  function identity(port) {
    return {id: port.id, name: port.name || '', manufacturer: port.manufacturer || ''};
  }
  function validIdentity(x) {
    return x && ['id', 'name', 'manufacturer'].every(k => typeof x[k] === 'string' && x[k].length <= 500);
  }
  function cleanPrefs(raw) {
    const result = {version: 1, device: null, profiles: [], audio: ''};
    if (!raw || raw.version !== 1) return result;
    if (validIdentity(raw.device)) result.device = identity(raw.device);
    if (typeof raw.audio === 'string' && raw.audio.length < 1000) result.audio = raw.audio;
    if (!Array.isArray(raw.profiles)) return result;
    for (const p of raw.profiles.slice(0, 32)) {
      if (!validIdentity(p.device) || !Array.isArray(p.bindings)) continue;
      const bindings = [], seen = new Set();
      for (const b of p.bindings.slice(0, 64)) {
        const target = targets.find(t => t[0] === b?.target);
        if (!target || target[2] !== b.kind || !Number.isInteger(b.channel) || b.channel < 1 || b.channel > 16 ||
            !Number.isInteger(b.number) || b.number < 0 || b.number > 127 || !['absolute', 'twos', 'offset'].includes(b.mode)) continue;
        const key = `${b.kind}:${b.channel}:${b.number}`;
        if (seen.has(key)) continue;
        seen.add(key); bindings.push({target: b.target, kind: b.kind, channel: b.channel, number: b.number, mode: b.mode});
      }
      result.profiles.push({device: identity(p.device), bindings});
    }
    return result;
  }
  function controlValue(value, mode, current, min, max, step) {
    let next;
    if (mode === 'twos') next = current + (value === 64 ? 0 : value > 64 ? value - 128 : value) * step;
    else if (mode === 'offset') next = current + (value === 0 ? 0 : value - 64) * step;
    else next = min + value / 127 * (max - min);
    return Math.max(min, Math.min(max, Number((Math.round(next / step) * step).toFixed(6))));
  }
  function mount(bridge) {
    const $ = id => document.getElementById(id);
    let prefs;
    const say = message => { $('midi-status').textContent = message; };
    try { prefs = cleanPrefs(JSON.parse(localStorage.getItem(KEY))); }
    catch { prefs = cleanPrefs(null); say('Mappings unavailable; controls can still be learned for this session.'); }
    const save = () => {
      try { localStorage.setItem(KEY, JSON.stringify(prefs)); }
      catch { say('Mappings work this session, but browser storage is unavailable.'); }
    };
    let access = null, input = null, epoch = 0, learning = null, audioBusy = false;
    const held = new Set();
    const profile = () => prefs.profiles.find(p => p.device.id === input?.id);
    const options = (element, rows, selected) => {
      element.replaceChildren();
      for (const [value, label] of rows) {
        const option = document.createElement('option'); option.value = value; option.textContent = label; element.append(option);
      }
      element.value = selected;
    };
    const showMappings = () => {
      $('midi-mappings').replaceChildren();
      for (const b of profile()?.bindings || []) {
        const row = document.createElement('li'), remove = document.createElement('button');
        row.append(`${targets.find(t => t[0] === b.target)[1]} ← ch ${b.channel}, ${b.kind} ${b.number}${b.kind === 'cc' ? ' · ' + b.mode : ''} `);
        remove.textContent = 'Remove'; remove.setAttribute('aria-label', 'Remove ' + targets.find(t => t[0] === b.target)[1] + ' mapping');
        remove.onclick = () => { profile().bindings = profile().bindings.filter(x => x !== b); save(); showMappings(); };
        row.append(remove); $('midi-mappings').append(row);
      }
      $('midi-mapping-count').textContent = `${profile()?.bindings.length || 0} mappings on this device`;
    };
    const reset = (message = 'Controls reset. Note entry is disarmed.') => {
      held.clear(); learning = null; $('midi-arm').checked = false; $('midi-learn').textContent = 'Learn control';
      bridge.stop(); say(message);
    };
    const detach = () => {
      if (input) { input.onmidimessage = null; input.close?.().catch(() => {}); }
      input = null;
    };
    const receive = event => {
      const m = decode(event.data); if (!m) return;
      const key = `${m.channel}:${m.number}`;
      if (m.kind === 'off') { held.delete(key); return; }
      const channel = Number($('midi-channel').value);
      if (channel && channel !== m.channel) return;
      $('midi-monitor').textContent = `Ch ${m.channel} · ${m.kind === 'note' ? 'Note' : 'CC'} ${m.number} · ${m.value}`;
      if (m.kind === 'note') { if (held.has(key)) return; held.add(key); }
      if (learning) {
        const target = targets.find(t => t[0] === learning);
        if (target[2] !== m.kind) { say(`Waiting for a ${target[2] === 'note' ? 'pad press' : 'CC knob'} for ${target[1]}.`); return; }
        const p = profile();
        p.bindings = p.bindings.filter(b => b.target !== learning && !(b.kind === m.kind && b.channel === m.channel && b.number === m.number));
        p.bindings.push({target: learning, kind: m.kind, channel: m.channel, number: m.number, mode: $('midi-encoder').value});
        learning = null; $('midi-learn').textContent = 'Learn control'; say('Control learned. Mappings are specific to this device and channel.'); save(); showMappings(); return;
      }
      const binding = profile()?.bindings.find(b => b.kind === m.kind && b.channel === m.channel && b.number === m.number);
      try {
        if (binding) {
          if (binding.target.startsWith('vowel:')) {
            $('midi-vowel').value = binding.target.slice(6); bridge.vowel($('midi-vowel').value); say('Vowel ' + $('midi-vowel').value + ' selected.');
          } else if (m.kind === 'cc') bridge.control(binding.target, m.value, binding.mode, controlValue);
          else if (binding.target === 'play') bridge.play();
          else if (binding.target === 'stop') bridge.stop();
          else if (binding.target === 'next') bridge.next();
        } else if (m.kind === 'note' && $('midi-arm').checked) {
          bridge.note(m.number, m.value, Number($('midi-length').value), $('midi-vowel').value);
          say('Note added. Release the key before adding it again.');
        }
      } catch (error) { say(error.message); }
    };
    const select = port => {
      reset(); detach();
      if (port) {
        const remembered = prefs.device;
        let p = prefs.profiles.find(x => x.device.id === port.id);
        if (!p && remembered && resolveDevice(remembered, [...access.inputs.values()].filter(x => x.state !== 'disconnected')) === port) {
          p = prefs.profiles.find(x => x.device.id === remembered.id);
          if (p) p.device = identity(port);
        }
        input = port;
        if (!p) { prefs.profiles.push({device: identity(port), bindings: []}); prefs.profiles = prefs.profiles.slice(-32); }
        prefs.device = identity(port); save();
        port.onmidimessage = event => { if (input === port && port.state !== 'disconnected') receive(event); };
      }
      $('midi-arm').disabled = !input; $('midi-learn').disabled = !input; $('midi-input').value = input?.id || '';
      showMappings(); say(input ? `${input.name || 'MIDI input'} selected. Note entry is disarmed.` : 'Choose a MIDI input.');
    };
    const refresh = () => {
      if (!access) return;
      const live = [...access.inputs.values()].filter(p => p.state !== 'disconnected');
      const previous = input;
      const chosen = previous ? live.find(p => p.id === previous.id) : resolveDevice(prefs.device, live);
      options($('midi-input'), [['', 'Choose an input…'], ...live.map(p => [p.id, p.name || 'Unnamed MIDI input'])], chosen?.id || '');
      if (previous !== chosen) select(chosen || null);
      if (!live.length) say('No MIDI inputs connected. Plug in the Akai and check its USB connection.');
      else if (previous && !chosen) say('MIDI input disconnected. Note entry disarmed; choose an input to resume.');
    };
    const disconnect = () => {
      epoch++; if (access) access.onstatechange = null; access = null; reset(); detach();
      options($('midi-input'), [['', 'MIDI disconnected']], '');
      $('midi-connect').disabled = false; $('midi-disconnect').disabled = true; $('midi-arm').disabled = true; $('midi-learn').disabled = true;
      showMappings(); say('MIDI disconnected. Saved mappings are retained.');
    };
    $('midi-connect').onclick = async () => {
      if (access || $('midi-connect').disabled) return;
      if (!navigator.requestMIDIAccess) { say('Web MIDI is unavailable. Use a supporting desktop browser such as Chrome or Edge.'); return; }
      const ticket = ++epoch; $('midi-connect').disabled = true; $('midi-disconnect').disabled = false;
      try {
        const next = await navigator.requestMIDIAccess({sysex: false});
        if (ticket !== epoch) return;
        access = next; access.onstatechange = refresh; refresh();
      } catch (error) {
        if (ticket === epoch) { disconnect(); say(error.name === 'NotAllowedError' ? 'MIDI permission denied. Allow MIDI access in the browser and try again.' : 'Cannot connect MIDI: ' + error.message); }
      }
    };
    $('midi-disconnect').onclick = disconnect; $('midi-input').onchange = () => select(access?.inputs.get($('midi-input').value) || null);
    $('midi-panic').onclick = () => reset(); $('midi-channel').onchange = () => reset('Channel changed. Note entry disarmed.');
    $('midi-arm').onchange = () => { held.clear(); say($('midi-arm').checked ? 'Armed: each unassigned key appends one note to the selected part.' : 'Note entry disarmed.'); };
    options($('midi-target'), targets.map(t => [t[0], t[1]]), 'vowel:a');
    $('midi-target').onchange = () => { learning = null; $('midi-learn').textContent = 'Learn control'; };
    $('midi-learn').onclick = () => {
      learning = learning ? null : $('midi-target').value;
      $('midi-arm').checked = false; held.clear(); $('midi-learn').textContent = learning ? 'Cancel learning' : 'Learn control';
      say(learning ? 'Move only the pad or knob you want to assign. The learning message will not change the score.' : 'Learning cancelled.');
    };
    $('midi-vowel').onchange = () => bridge.vowel($('midi-vowel').value);
    $('midi-play').onclick = () => bridge.play();
    const audioSelect = $('audio-input');
    const audioStatus = message => { $('audio-input-status').textContent = message; };
    const refreshAudio = async () => {
      if (!navigator.mediaDevices?.enumerateDevices) return;
      const list = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'audioinput');
      const selected = prefs.audio;
      const rows = [['', 'System default'], ...list.filter(d => d.deviceId && d.deviceId !== 'default').map((d, i) => [d.deviceId, d.label || `Audio input ${i + 1}`])];
      if (selected && !rows.some(r => r[0] === selected)) rows.push([selected, 'Selected device unavailable — reconnect or choose another']);
      options(audioSelect, rows, selected);
    };
    options(audioSelect, [['', 'System default'], ...(prefs.audio ? [[prefs.audio, 'Saved input — refresh devices to check']] : [])], prefs.audio);
    $('audio-refresh').onclick = async () => {
      if (audioBusy || bridge.recording()) return;
      if (!navigator.mediaDevices?.getUserMedia) { audioStatus('Audio inputs require a supporting browser on localhost or HTTPS.'); return; }
      audioBusy = true; $('audio-refresh').disabled = true; $('record').disabled = true; let stream;
      try { stream = await navigator.mediaDevices.getUserMedia({audio: true, video: false}); await refreshAudio(); audioStatus('Inputs refreshed. Choose the SP-404MKII if it appears in the list.'); }
      catch (error) { audioStatus(error.name === 'NotAllowedError' ? 'Microphone permission denied; no device was selected.' : error.message); }
      finally { stream?.getTracks().forEach(t => t.stop()); audioBusy = false; $('audio-refresh').disabled = bridge.recording(); $('record').disabled = false; }
    };
    audioSelect.onchange = () => { prefs.audio = audioSelect.value; save(); audioStatus('Input selected for the next recording. Playback uses your system output device.'); };
    const deviceChange = () => { refreshAudio().catch(error => audioStatus(error.message)); };
    navigator.mediaDevices?.addEventListener?.('devicechange', deviceChange);
    window.addEventListener('beforeunload', () => { disconnect(); navigator.mediaDevices?.removeEventListener?.('devicechange', deviceChange); });
    return {
      reset,
      audioConstraints: () => ({echoCancellation: false, noiseSuppression: false, autoGainControl: false, ...(prefs.audio ? {deviceId: {exact: prefs.audio}} : {})}),
      setRecording: busy => { audioSelect.disabled = busy; $('audio-refresh').disabled = busy || audioBusy; },
    };
  }
  const exported = {decode, resolveDevice, cleanPrefs, controlValue, mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = exported;
  else globalThis.CantabileHardware = exported;
})();
