# Hardware controls

Cantabile now accepts live MIDI to edit the score and voice controls. It remains
render-first: keys append notes rather than producing live synthesized lyrics.
Pads can select vowels, advance the sequencer selection, or play/stop the latest
render. Volta and Cantabile remain separate applications.

## Akai MPK mini IV

1. Open **Play from hardware**, click **Connect MIDI**, grant permission, and
   choose the Akai's performance MIDI input. Use a desktop browser supporting
   Web MIDI, such as Chrome or Edge. Permission is requested only on this click.
2. Under **Assign to**, choose a vowel or playback action, click **Learn control**,
   then press its pad. Repeat for the pads you want to use. Learning consumes the
   message without changing the score. Learn pads before arming the keyboard.
3. Choose a voice control, choose the knob message mode, click **Learn control**,
   and turn the knob. Absolute 0–127, relative two's complement and relative
   binary-offset messages are supported; match the setting to your hardware
   program. There are no guessed factory note/CC assignments.
4. Select a generated vocal part, a vowel and note length, then enable **Arm note
   entry**. Each unassigned note-on appends one note. Release before repeating
   the same key. Velocity 100–127 adds an accent. Note entry uses MIDI pitches
   24–96 and respects the 256-note and 60-second prototype limits.
5. Disarm and **Solo this part** or **Render ensemble**. Voice-knob edits affect
   the next render. **Play latest render** starts the most recent output from
   the beginning; a learned pad does the same. If browser autoplay prevents a
   pad from starting audio, click the page's playback button once.

| Control | Available action |
| --- | --- |
| Keys | Armed step entry into the selected generated vocal part |
| Pads | a/e/i/o/u selection, next sequencer step, latest-render play/stop |
| Knobs | Level, pan, vibrato, formant, glide, accent strength, tone, grit, delay, input-tuning strength |

Vowel pads also change the selected sequencer cell's vowel when it is not a
hold. They preserve its consonants. Sample voices still support only their
recorded vowels. Disabled voice controls remain unavailable over MIDI: for
example, formant does not affect the sampled bank. Tuning strength applies only
to imported recordings and does not automatically enable correction.

Mappings are stored in this browser, per device and MIDI channel, separately
from song files. A saved device with a changed ID is relinked only when its name
and manufacturer identify exactly one live port. Ambiguous matches require
manual selection. Only the selected input receives messages. A disconnect,
port replacement, channel change, part/project change or **Stop / reset controls**
disarms note entry and cancels learning. Disconnecting retains saved mappings.
Reset also stops audio playback; use the mic's Stop button to finish recording.

Use the main **MPK Mini IV MIDI Port** for keys, pads and knobs. Akai's separate
DAW/plugin ports require separate control handling; DAW transport scripts are
not implemented here. See the official
[MPK mini IV FAQ](https://support.akaipro.com/en/support/solutions/articles/69000872348-mpk-mini-iv-frequently-asked-questions).

## Roland SP-404MKII — confirmed

Scott confirmed this model. The proposed physical arrangement uses the Roland
for audio input/output and sampling rendered vocal WAVs, with the Akai handling
melody entry and vocal controls.

In **Microphone input**, click **Refresh audio inputs**. The browser asks for
microphone permission briefly to reveal input labels, then releases that
permission stream. Choose the SP-404MKII if the operating system exposes it.
**Record mic** captures that exact input; unavailable devices produce an error
instead of silently using another microphone. The selector is locked while a
recording is starting or active. Input loss ends capture and keeps any captured
audio. A permission refusal does not change the selected input.

Playback uses the computer/browser's system output. Select the Roland as your
system output when required; this version has no per-player output selector,
live input monitoring or MIDI clock/transport synchronization. Pitch correction
still renders offline. Hardware routing and latency have not been tested here.

Official reference: [Roland SP-404MKII computer connection](https://static.roland.com/manuals/sp-404mk2_reference/eng/17805250.html).

## Reuse and validation

The channel-specific learning, unique device-identity relinking, and stale-port
handler cleanup patterns were adapted from Scott's Padlab project:
`src/midi/midiManager.ts` and `src/midi/deviceMemory.ts`. Padlab's factory pad
profiles were inspected; this app uses explicit learning so a custom hardware
program cannot silently trigger the wrong voice action.

Run `npm run test:hardware` and `npm run test:dom` in this directory. Tests use
simulated Web MIDI, media devices and Web Audio lifecycle objects. They verify
message routing and UI state, not USB drivers, physical timing, actual browser
permissions or audible output. Real browser/hardware acceptance remains open.

For physical acceptance: learn one vowel pad and one knob, enter three notes,
render and play, unplug/reconnect the Akai and confirm entry is disarmed, then
select the Roland input and record two short takes. Verify the sound and device
routing for each take before using it in a longer session.
