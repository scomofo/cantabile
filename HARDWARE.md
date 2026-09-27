# Hardware control plan

The current Cantabile prototype imports MIDI files; it does not yet accept live
MIDI controllers. Volta already accepts live MIDI notes and supports MIDI Learn
for its synth knobs. A separate integration pass is needed for the vocal editor.

## Akai MPK mini IV

Assuming Scott's “Akai mk 4 mini” is the MPK mini IV, a useful proposed mapping is:

| Control | Proposed Cantabile action |
| --- | --- |
| Keyboard | Enter melody notes for the selected vocal part |
| Pads | Select vowels/syllables or trigger previously rendered phrases |
| Strike velocity | Accent or phrase level |
| Eight knobs | Assignable voice expression and effects through MIDI Learn |

Use the main **MPK Mini IV MIDI Port** for performance data. Akai documents
separate DAW and plugin ports; transport buttons should be mapped and tested
separately, rather than assuming a DAW script controls this app. Controller
messages and physical behavior have not been tested here.

Akai's official [MPK mini IV FAQ](https://support.akaipro.com/en/support/solutions/articles/69000872348-mpk-mini-iv-frequently-asked-questions)
documents 25 velocity-sensitive keys, eight velocity-sensitive pads, eight
endless knobs, USB-C MIDI, five-pin MIDI output, and the port roles.

## Roland SP-404MKII — confirmed

Scott confirmed that his 404 is the **Roland SP-404MKII**. Roland documents USB
audio and MIDI, so the proposed setup uses it as the computer's audio
input/output device and as a sampler for rendered vocal WAVs, with the Akai
handling melody entry and assignable vocal controls.
This is a proposed workflow, not verified compatibility with this prototype.
Cantabile currently records the browser-selected default audio input.

Official reference: [Roland SP-404MKII computer connection](https://static.roland.com/manuals/sp-404mk2_reference/eng/17805250.html).

The first hardware slice should add device selection, incoming-message feedback,
assignable controls, saved mappings, and a disconnect/reset path. Pad playback
should use rendered audio; neural lyric generation remains render-first.
