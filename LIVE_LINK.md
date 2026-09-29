# Live link: play Volta's keyboard, Cantabile's singers sing it

The live link connects the two apps in real time. Volta mirrors every note you
play to a MIDI output port; Cantabile's live player listens on that port and
sings the notes immediately with a recorded singer from the vocal bank.

```
Volta keyboard → Web MIDI out → virtual MIDI cable → live.py → your speakers
```

## What you need

- **A virtual MIDI cable.** On Windows, install
  [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) (free) and
  create a port named `Volta Choir`. On macOS, the built-in IAC Driver does the
  same job (Audio MIDI Setup → MIDI Studio → IAC Driver → enable).
- **Python packages** (in the same environment you use for Cantabile):
  `pip install sounddevice python-rtmidi`
- **The unpacked recorded bank**: `python prepare_bank.py` in `tools/cantabile`
  (same as the normal Cantabile setup).

## Start it

1. Start loopMIDI (or enable the IAC Driver) so the `Volta Choir` port exists.
2. In `tools/cantabile`, run:
   ```
   python live.py --voice vs-f1 --vowel ah --midi-port "Volta Choir"
   ```
   Use `python live.py --list-voices` to see the 20 recorded singers and
   `python live.py --list-ports` to check the port name.
3. In Volta, click **Choir link** in the header, tick **Send notes to choir**,
   and pick the `Volta Choir` port.
4. Play. The singer follows your notes with roughly 10–20 ms of latency.

## Options

- `--vowel`: which vowel the singer holds — `a`, `e`, `i`, `o`, `u`
  (`ah`, `eh`, `ee`, `oh`, `oo` also work). Default: `ah`.
- `--technique`: bank technique; defaults to `straight` when the voice has it.
- `--channel N`: only respond to MIDI channel N (0–15). Run a second instance
  with a different voice and channel for a two-part choir.
- `--midi-port`: exact or partial port name. Defaults to the first available
  input port.

## Expressive control (Volta → choir)

Beyond notes, Volta transmits standard MIDI messages on the same port:

| Control | MIDI message | Effect on the choir |
|---|---|---|
| Pitch wheel | Pitch bend, ±2 semitones | Bends the sung pitch |
| Mod wheel | CC1 (mod wheel) | Vowel morph a → e → i → o → u |
| Choir dynamics slider | CC11 (expression) | Choir volume |
| Glide knob / preset | CC5 (portamento time) | Glide between sung notes |

The pitch wheel also bends Volta's own synth voice ±2 semitones, like the
hardware. The mod wheel is dedicated to the choir — it does not change
Volta's own sound.

**Companion support status:** the live player currently responds to notes and
all-notes-off only. Pitch bend, CC1, CC11, and CC5 are transmitted by Volta
today but need a small live-player update to take effect: handle
`pitch_bend` (scale each active note's pitch increment), CC1 (crossfade the
vowel sample toward the next vowel), CC11 (scale note gain), and CC5 (set the
glide time between notes). Until then they are sent and safely ignored.

## Playing Volta from Cantabile (reverse direction)

The link is bidirectional. Route Cantabile's MIDI output to the same virtual
cable (or a second one, e.g. `Volta In`) and pick it in Volta's MIDI input —
incoming notes play Volta's own Minimoog-style synth directly. Incoming notes
are never echoed back to the MIDI output, so the two directions can't feed
back into each other; use Volta's own keyboard or arpeggiator for choir
parts. MIDI-learn knob mappings are unaffected.

## What it can and cannot do

- **Can:** live, polyphonic singing of the recorded vowel bank — the same
  samples and pitch-shifting as the offline renderer, streamed per note with a
  short attack and a 90 ms release. Volta transmits pitch bend, vowel morph
  (CC1), dynamics (CC11), and portamento time (CC5) for the choir; the live
  player needs the update described above to respond to them.
- **Cannot:** neural voices (`hanami`, `tiger`) — they are render-first and stay
  in the offline app. No lyrics or consonants live; the singer holds one vowel
  per note (vowel morph needs the live-player update). One voice per live
  player instance — run more instances for a bigger choir.

## Troubleshooting

- **"No MIDI input ports found"** — the virtual cable app isn't running, or the
  port wasn't created. Create the port first, then start `live.py`.
- **Volta shows "No MIDI"** — the browser blocked MIDI access, or you're on a
  page served over plain HTTP from another machine. Web MIDI needs a secure
  context; `localhost` counts.
- **The port isn't in Volta's list** — ports appear when the cable app creates
  them; if you created the port after opening Volta, close and reopen the tab.
- **No sound from the choir** — check the voice id (`--list-voices`), make sure
  the bank is unpacked (`prepare_bank.py`), and confirm your system audio
  output is the device you expect.
- **Stuck notes** — Volta sends all-notes-off on panic and on note-off; if a
  note hangs after a crash, restart `live.py`.
