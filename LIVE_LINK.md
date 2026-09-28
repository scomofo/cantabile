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

## What it can and cannot do

- **Can:** live, polyphonic singing of the recorded vowel bank — the same
  samples and pitch-shifting as the offline renderer, streamed per note with a
  short attack and a 90 ms release.
- **Cannot:** neural voices (`hanami`, `tiger`) — they are render-first and stay
  in the offline app. No lyrics or consonants live; the singer holds one vowel.
  No pitch bend yet — Volta's glide is not transmitted, so gliding notes sing
  as stepped pitches.

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
