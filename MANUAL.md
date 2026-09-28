# Cantabile — User Manual

*Vocal Bank & Choir, prototype 0.2 — a local choir studio that lives on your computer.*

## Contents

1. [What Cantabile is](#1-what-cantabile-is)
2. [Installation](#2-installation)
3. [Quick start — first sound in five minutes](#3-quick-start--first-sound-in-five-minutes)
4. [Concepts](#4-concepts)
5. [The live player](#5-the-live-player)
6. [Web UI reference](#6-web-ui-reference)
7. [MIDI setup](#7-midi-setup)
8. [Volta Choir link](#8-volta-choir-link)
9. [Building the vowel bank](#9-building-the-vowel-bank)
10. [CLI reference](#10-cli-reference)
11. [Configuration files reference](#11-configuration-files-reference)
12. [Troubleshooting](#12-troubleshooting)
13. [FAQ](#13-faq)
14. [Glossary](#14-glossary)

---

## 1. What Cantabile is

Cantabile is a small music studio for voices that runs entirely on your own computer. You build a choir out of vocal sections — soprano, alto, tenor, bass and friends — pick a singer for each section, write notes and words, and render a performance to a WAV file you can keep, sample, or drop into a DAW.

It has three kinds of voices:

- **Recorded singers (the vowel bank).** Twenty real human singers, recorded singing vowels. They can't sing arbitrary words — they sing *ah, eh, ee, oh, oo* — but they sound like actual people, because they are actual people. This is the bank you'll play live.
- **Neural voices.** Two singing synthesizers — **Hanami** (female) and **TIGER** (male, with Fresh and Vinyl modes) — that sing whatever English words you type. They only work when you render; they don't play live.
- **Your own voice.** Record yourself with a microphone, or import a WAV. You can use the recording as-is, have Cantabile detect its melody and re-sing it, or apply pitch correction.

Two ways to use it:

- **The web app** (the composer): open it in your browser, write your choir, shape each voice, hit **Render ensemble**, and get a mix plus stems. This is render-first — you write, then you listen.
- **The live player** (the instrument): run `live.py`, play notes on a MIDI keyboard (or from Volta), and a recorded singer sings them back in real time with about 10–20 ms of latency.

Everything renders locally. No account, no API key, no cloud. Once setup is done, you can unplug the internet and it all still works.

**What it's not:** not a finished commercial product, not a substitute for a session singer, and the neural voices carry noncommercial terms (see [THIRD_PARTY.md](../repo/tools/cantabile/THIRD_PARTY.md) in the project folder — summarized in the FAQ). It's a working prototype, version 0.2, and it's honest about that.

---

## 2. Installation

### What you need

- **Windows 10/11, 64-bit** (the launchers are Windows-first; Mac/Linux instructions are below).
- **Python 3.12 or 3.13, 64-bit**, from [python.org/downloads/windows](https://www.python.org/downloads/windows/). During the Python installer, tick **"Add python.exe to PATH"** — or at least make sure the `py` launcher is installed (it is, by default).
- **About 4 GB of free disk space.** The voice models are ~1.1 GB; the installer also keeps downloads and the extracted sample bank.
- **Chrome or Edge** for microphone support. Any modern browser works for composing.
- A CPU is fine; 8 GB of RAM is a sensible starting point. No GPU needed.

### The three setup scripts (and which one you want)

All three live in the `tools/cantabile` folder. They do different jobs — pick one:

| Script | Does | Use when |
|---|---|---|
| `setup-windows.bat` | Creates the project environment, installs Python packages, unpacks the recorded vowel bank, **and downloads the two neural voice models (~1.1 GB)** | First install, when you want everything including neural lyrics |
| `setup-bank-only-windows.bat` | Same as above **but skips the 1.1 GB neural download** | First install, when you only want the recorded singers, mic input and pitch correction |
| `setup-voices-windows.bat` | Downloads the neural voice models into an existing setup | You ran the bank-only setup and now want neural lyrics too |

**Normal first install:** double-click `setup-windows.bat`, wait several minutes, done. Then double-click `start-windows.bat` whenever you want to use Cantabile.

What `setup-windows.bat` actually does, step by step:

1. Creates a project-local Python environment in `tools/cantabile/.venv` (so it never touches your system Python).
2. Runs `prepare_bank.py`, which verifies the 20 singer ZIP packs by SHA-256 and unpacks the 1,309 recorded samples. No downloads — everything ships in the folder.
3. Installs the Python packages from `requirements.txt` (NumPy, SciPy, ONNX Runtime, SoundFile, CMUdict, Mido, PyWORLD prebuilt).
4. Runs `setup_assets.py`, which downloads the Hanami (~537 MB) and TIGER (~556 MB) voicebanks directly from their creators, verifies checksums, and installs them under `tools/cantabile/models/`.

If anything fails, the script tells you and stops. The most common failure is Python-related — see below.

### Python version: read this before you run setup

Setup wants **Python 3.12 or 3.13**. If you have multiple Pythons installed (very common on a music-production PC), the launcher picks one with `py -3`, which means *the newest 3.x it can find* — and that might be a 3.14 you didn't mean to use, or a copy buried inside another app's folder.

**To see what the `py` launcher can find**, open a terminal and run:

```bat
py -0
```

You'll get a list like `-V:3.13-64`, `-V:3.12-64`, etc. If 3.12 or 3.13 is listed, you're good. If the setup script created a `.venv` with the *wrong* Python (you can check with the next command), do this:

```bat
cd C:\path\to\tools\cantabile
rmdir /s /q .venv
py -3.13 -m venv .venv
```

That last command is exactly what to run — it forces the 3.13 you installed rather than whatever `py -3` happens to prefer. Then re-run the setup `.bat` of your choice; it will see the existing `.venv` and use it.

> **Why this matters:** the setup scripts only create `.venv` when it doesn't exist (`if not exist .venv\Scripts\python.exe`). A stale or wrong-version `.venv` is never repaired automatically — if setup behaves strangely, delete `.venv` and start over. Nothing you composed lives in `.venv`; it's disposable.

To confirm which Python your environment actually uses:

```bat
.venv\Scripts\python.exe --version
```

### After setup: starting the app

Double-click **`start-windows.bat`**. It runs the local server and opens your browser at:

```
http://127.0.0.1:8765
```

**Leave the terminal window open** while you work — closing it stops Cantabile. The server only listens on your own machine (`127.0.0.1`); nothing is exposed to the network.

The first thing `app.py` does on launch is run the bank preparation again, so the samples are always verified before the UI appears.

### Verifying your install

1. `start-windows.bat` opens the browser with no Python traceback in the terminal.
2. The top bar shows the engine status: with neural voices installed it reads *"English neural voices ready · male + female · local rendering"*; with the bank-only setup it reads *"20 recorded voices ready · neural lyrics need setup-voices-windows.bat"*.
3. Open **Recorded voice bank**, pick any singer, press **▶ Baseline** — you should hear a preview.
4. Run the test suite if you like (needs the venv active):

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expect the Python tests to pass; the one neural test is explicitly skipped when models aren't installed. See `VERIFICATION.md` in the project folder for what was and wasn't exercised.

### Mac / Linux / terminal

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python prepare_bank.py
python setup_assets.py      # skip this for a bank-only install
python app.py
```

Useful flags: `python app.py --no-browser --port 8765` (don't auto-open the browser; choose the port). Never expose this development server to the internet — it listens on 127.0.0.1 and rejects foreign browser origins by design.

### Optional: browser/UI tests (developers)

The JavaScript UI tests need Node. From `tools/cantabile`:

```bat
npm install
npm run test:dom        :: fast DOM checks with simulated browser objects
npm run test:hardware   :: MIDI/hardware control checks (simulated Web MIDI)
```

`npm run test:browser` runs a real Chromium via Playwright (`npx playwright install chromium` first; set `CANTABILE_CHROME` to a Chrome executable if needed). Note it uses a *synthetic* microphone — it doesn't replace testing with a real mic.

---

## 3. Quick start — first sound in five minutes

**Goal:** hear a voice, no setup beyond the steps above.

1. **Start it.** Double-click `start-windows.bat`. Browser opens at `http://127.0.0.1:8765`.
2. **Listen before you build.** In the project folder, open `examples/audio/hold-the-light-choir.wav` in any media player. That's a finished render — now you'll make your own.
3. **Open an example.** In the Cantabile header, click **Load example** (or open `examples/recorded-choir.json` via **Open project**). Six recorded singers appear.
4. **Render.** Click **▶ Render ensemble**. Draft quality renders faster; Standard uses more acoustic detail. First renders take a while — a 21-second four-part choir took about 75 seconds on the developer's CPU. Watch the progress bar; the status line narrates what it's doing.
5. **Listen.** When it finishes, the player appears with your mix, plus download links for the **full mix** and **per-section stems** (44.1 kHz, 24-bit WAV).

**Next:** click a section in the left column, change its voice in the **Voice source** dropdown, and render again. Or type your own words — see [Section 6](#6-web-ui-reference).

**Fastest live thrill:** skip the web app entirely — see [The live player](#5-the-live-player) and [Volta Choir link](#8-volta-choir-link) to *play* a singer from a keyboard.

---

## 4. Concepts

### The vowel bank (recorded singers)

Twenty singers, labelled **vs-f1 … vs-f9** (female) and **vs-m1 … vs-m11** (male). They come from the VocalSet research dataset — real recorded performances, edited into 1,309 looped multisamples. Each singer was captured singing sustained vowels in different **techniques**: *straight*, *vibrato*, *breathy*, and *belt* (a couple of singers have fewer; the bank panel shows exactly what's available per singer).

They sing five vowels: **a, e, i, o, u** (written *ah, eh, ee, oh, oo* in places — same thing). That's the whole vocabulary. No consonants, no words. For anything with lyrics you need a neural voice or your own recording.

Each singer also has a measured **sampled range** (the pitches actually recorded) shown in the bank panel. Notes outside it still sound — they're resampled from the nearest recorded pitch — but the timbre changes, like slowing down or speeding up tape.

The bank ships as 20 compressed ZIP packs and is unpacked locally by `prepare_bank.py`, which checks every file's SHA-256. The originals stay in `vocal-bank/packs/` so you can always re-verify.

### Neural voices

- **Hanami** — female voice by Lotte V. The default for soprano/mezzo/alto parts.
- **TIGER** — male voice by tigermeat, with two performance modes: **Fresh** and **Vinyl** (two flavors of the same singer, not two singers). The default for tenor/baritone/bass parts.

These sing any English words you type, using a pronunciation dictionary (CMUdict) plus per-note phoneme overrides. They're render-only: they need seconds of computation per phrase, so they can't play live. Dependencies include noncommercial terms — fine for personal prototyping, not cleared for commercial release (details in [FAQ](#13-faq)).

### Baselines

Every voice — recorded or neural — can have a **baseline**: a saved neutral performance (notes + voice settings) that acts as your starting point and safety net.

- **Create baseline** generates a neutral phrase for the selected part and *replaces* its notes (it asks first).
- **Hear baseline** renders the saved baseline without touching your edits — a quick A/B.
- **Reset to baseline** restores the saved notes and settings.

Baselines are saved inside your project file. Recorded inputs keep their original untuned playback separately in the correction panel.

### Polyphony (live vs. rendered)

- In the **web app**, polyphony means stacked sections: up to **16 tracks** and **32 enabled singers** total. Each part is monophonic (one note at a time per singer), but you can have many parts.
- In the **live player**, polyphony means chords: one singer instance plays as many simultaneous MIDI notes as you hold. Want a two-part live choir? Run two `live.py` instances with different voices and MIDI channels.

### MIDI routing (the big picture)

```
Volta keyboard ──Web MIDI out──▶ virtual MIDI cable ──▶ live.py ──▶ your speakers
Akai MPK mini ──Web MIDI in───▶ browser (Cantabile web app) ──▶ edits the score
```

Two separate paths: the **live player** turns MIDI into *sound right now*; the **web app** turns MIDI into *notes in your score* (or knob tweaks to the next render). They don't talk to each other — pick the one that fits what you're doing.

---

## 5. The live player

The live player is `live.py` in `tools/cantabile`. It takes one recorded singer, listens on a MIDI input port, and sings every note it receives — same samples and pitch-shifting math as the offline renderer, with a short 18 ms attack and a 90 ms release fade.

**Prerequisites** (in your Cantabile `.venv`):

```bat
.venv\Scripts\python.exe -m pip install sounddevice python-rtmidi
```

`sounddevice` drives your speakers; `python-rtmidi` (via `mido`) is the MIDI backend. Neither ships in `requirements.txt` — they're only needed for live playing. The bank must be unpacked (`prepare_bank.py` — the normal setup already did this).

**Basic launch:**

```bat
cd C:\path\to\tools\cantabile
.venv\Scripts\python.exe live.py --voice vs-f1 --vowel ah --midi-port "Volta Choir"
```

You'll see: `Live choir: F1 · soprano singing "a" from MIDI port "Volta Choir". Ctrl+C to stop.` Then play. Latency is roughly 10–20 ms.

### Every option

| Flag | What it does | Default |
|---|---|---|
| `--voice ID` | Which recorded singer sings. See `--list-voices`. Neural voices (`hanami`, `tiger`) are rejected with an error — they can't sing live. | `vs-f1` |
| `--vowel V` | The vowel the singer holds: `a`, `e`, `i`, `o`, `u` (`ah`, `eh`, `ee`, `oh`, `oo` also accepted). | `ah` |
| `--technique T` | Bank technique: `straight`, `vibrato`, `breathy`, or `belt`. | `straight` if the voice has it, else the voice's first technique |
| `--midi-port NAME` | MIDI input port. Exact name first, then case-insensitive substring match. | First available input port |
| `--channel N` | Only respond to MIDI channel **0–15**. | All channels (omni) |
| `--list-voices` | Print the 20 singers (id, name, role, gender) and exit. | — |
| `--list-ports` | Print available MIDI input ports and exit. | — |

Notes on behavior, from the code:

- **Note selection:** for each note-on, the player picks the sample whose recorded root pitch is nearest your MIDI note, then pitch-shifts it to the exact pitch. Velocity scales loudness (peak 0.7 at full velocity).
- **Retriggering:** hitting the same pitch again releases the old note and starts a fresh one.
- **Note-off** (or note-on with velocity 0) releases with the 90 ms fade.
- **All-notes-off** (MIDI CC 123) releases everything — this is the panic path Volta uses.
- **Channel filter:** with `--channel`, messages on other channels are ignored entirely.

### The 20 live voices

Run `python live.py --list-voices`. The roster (roles describe the source singer):

| ID | Singer | ID | Singer |
|---|---|---|---|
| `vs-f1` | F1 · soprano | `vs-m1` | M1 · baritone |
| `vs-f2` | F2 · soprano | `vs-m2` | M2 · tenor |
| `vs-f3` | F3 · soprano | `vs-m3` | M3 · tenor |
| `vs-f4` | F4 · soprano | `vs-m4` | M4 · bass (?) |
| `vs-f5` | F5 · mezzo-soprano | `vs-m5` | M5 · baritone |
| `vs-f6` | F6 · soprano | `vs-m6` | M6 · baritone |
| `vs-f7` | F7 · soprano | `vs-m7` | M7 · tenor (?) |
| `vs-f8` | F8 · mezzo-soprano | `vs-m8` | M8 · bass |
| `vs-f9` | F9 · soprano | `vs-m9` | M9 · countertenor |
| | | `vs-m10` | M10 · bass-baritone |
| | | `vs-m11` | M11 · tenor |

(The `(?)` marks are the dataset's own tentative classifications, preserved as-is.)

### What it can't do

- **No lyrics or consonants live** — one vowel, held. Words are render-only.
- **No neural voices live** — `hanami`/`tiger` stay in the web app.
- **No pitch bend** — gliding notes sing as stepped pitches.
- **One voice per instance.** For a live duet, open two terminals: one `--voice vs-f1 --channel 0`, another `--voice vs-m2 --channel 1`, and send each its own channel.

---

## 6. Web UI reference

The web app is one page. Top to bottom:

### Header

- **Title field** — your composition's name (used for download filenames).
- **Open project** — loads a `.json` project file (max 2 MB; validated before it replaces your score, asks for confirmation).
- **Save project** — downloads the project as JSON. **Important:** the JSON holds *references* to imported voice WAVs, not the audio — keep the originals, and copy the app's `imports/` folder if you move computers.
- **Load example** — replaces your score with the built-in demo (asks first).
- **Tempo** — 40–200 BPM. **Quality** — *Draft · faster* (fewer acoustic iterations) or *Standard · finer*.
- **▶ Render ensemble** — renders everything enabled. **Cancel** appears while rendering; it waits for the current voice operation to finish and never alters your score.

### Engine status line

Shows what's installed: *"English neural voices ready · male + female · local rendering"* or *"N recorded voices ready · neural lyrics need setup-voices-windows.bat"*. **Voices & setup** opens a dialog summarizing the voice sources, their terms, and the setup steps.

### 01 / Build your choir (left column)

- **+ Add section** with a range dropdown: soprano, mezzo-soprano, alto, tenor, baritone, bass. (Up to 16 tracks; the app stops you at 16.)
- Each section row: an **enable checkbox**, the name, singer count and range. Click the name to select it. Untracked instrument sections (violin, cello, flute, horn — recorded VSCO samples) live under **Orchestra**.
- **Concert hall** slider: 0–60% hall reverb on the mix.

### Selected section controls

- **Section name** — free text.
- **Vocal range** — soprano … bass (composition guide; suggested pitch ranges are shown under the score, e.g. soprano C4–C6).
- **Performance** — *Soloist* (1 singer) or *Ensemble* (defaults to 4; **Singers** accepts 1–8).
- **Delivery** — *Singing* or *Rhythmic / rap sketch* (rhythmic suppresses vibrato; it's a sketch, not a rap model).
- **Voice source** — Hanami · female, TIGER · male / Fresh, TIGER · male / Vinyl, any of the 20 recorded singers, or *Import a male or female voice…*.
- **Recorded technique** — straight / vibrato / breathy / belt (only for recorded singers; whatever the singer actually has).
- **Level** (0–1.5), **Pan** (left–right), **Spread** (ensemble stereo width, 0–1).
- **Remove** — deletes the section (asks first).

### 02 / Compose

- **Piano roll** — a visual of the selected section's notes (pitch vs. beats).
- **Solo this part** — renders only the selected section, leaving your enable-checkboxes alone.
- **Import MIDI** — pick a track from a `.mid`/`.midi` file (under 2 MB). Existing lyric events are kept; otherwise notes start as `ah`. Parts must be monophonic; **variable-tempo files are rejected** rather than silently retimed. Optional checkbox: *use the MIDI file's tempo for this project*.
- **Export vocal score** — writes MusicXML with all enabled vocal parts, words, rests and ties, for external singing editors.
- **Lyrics field** — one word per note, then **Apply lyrics**. Counts must match exactly, or nothing changes and it tells you why. Put `+` on a note to continue the previous word's vowel across a second pitch (melisma).
- **Edit notes & pronunciation** — the note table: start (beats), length, MIDI pitch (C4 = 60), word, optional **phonemes** (lowercase ARPAbet like `l ay t` for "light" — unknown words error out naming the word; they're never silently replaced), accent checkbox, delete. **+ Add note** appends at the end.

### Recorded voice bank panel

- Filter: All / Female / Male. Each singer card shows name, gender, sample count, and sampled pitch range.
- **▶ Baseline** — plays that singer's neutral preview recording.
- **Use voice** — assigns the singer to the selected vocal section (then **Create baseline** in the Voice Lab to generate its fitted phrase).

### Play from hardware panel

See [Section 7](#7-midi-setup) — full reference there.

### 03 / Voice Lab

Nine per-part shaping controls (disabled ones simply don't apply to the current voice — e.g. formant does nothing on recorded singers, and synthesis controls don't retune imported recordings):

| Control | Range |
|---|---|
| Transpose | ±12 semitones |
| Formant / vocal color | −5 … +5 |
| Vibrato depth | 0 … 0.7 st |
| Vibrato rate | 3 … 9 Hz |
| Note glide | 0 … 0.2 s (between adjacent notes) |
| Accent strength | 1 … 2.5× |
| Dark ↔ bright tone | −1 … +1 |
| Grit | 0 … 1 (distortion effect, not a recorded growl) |
| Eighth-note delay | 0 … 0.5 (tempo-synced) |

**Presets:** *Natural choir* (defaults), *Tight rhythmic vocal* (no vibrato, slight glide, brighter, a touch of grit and delay), *Wide hook · 4 singers* (4 singers, wide spread, gentle glide and delay), *Rough chant* (no vibrato, dark formant, heavy grit). Every preset stays fully editable afterward.

**Baselines** (see [Concepts](#4-concepts)): **Create baseline** (replaces notes — asks first; disabled for imported voices), **Hear baseline** (renders the saved reference; your edits are untouched), **Reset to baseline** (restores it).

### 04 / Vocal Groove (syllable sequencer)

A 16-step, 303-style sequencer for rhythmic vocal chops. Each step: **active** on/off, **accent**, **hold previous vowel** (tie), **consonant onset** (e.g. `b r`), **vowel** (15 ARPAbet choices like `aa` *father*, `iy` *beat*, `uw` *boom* — or none for consonants-only), **consonant ending**, **pitch** (MIDI 24–96), **gate** (vowel length, 0.4–1), **retrigger** (1–4 hits per step), **display word**.

Global: step division (1/16 or 1/8 notes), **swing** (0–60%), **pattern repeats** (1–4). Presets: *"Bring that beat back"* (the hook), *"Boom / tss / kah"* (percussive), *"One syllable"* (blank).

**Send pattern to this part** compiles the pattern into notes (asks before replacing). Editing the grid afterwards doesn't change the score until you send it again.

Consonant inventory (lowercase ARPAbet): `b ch d dh f g hh jh k l m n ng p r s sh t th v w y z zh`. Try `b`+`uw`+`m` for "boom", `b`+`iy`+`t` for "beat". Very short notes with heavy consonants may need a slower tempo or longer gate.

### 05 / Microphone input

1. **Refresh audio inputs** — briefly asks for mic permission to reveal device names (then releases it). Pick your interface (e.g. the SP-404MKII) from the dropdown; the selector locks while recording.
2. **● Record mic** — sing or hum one line. Auto-stops at 60 seconds. Click again to stop early.
3. Then either:
   - **Recording → notes** — detects the monophonic guide melody, quantizes to quarter beats, shows you the notes; you type the lyrics and it becomes a *synthesized* performance in the selected neural voice.
   - **Use recording as voice** — your actual recording becomes that section's audio.
   - Or **Import voice WAV** — any mono/stereo WAV under 30 MB and 62 seconds. **It must start at project time zero** (include leading silence). It's resampled to 44.1 kHz automatically.

Recordings live in the browser until imported, then they're stored in the app's `imports/` folder — nothing is uploaded anywhere. If you change the score or tempo after importing, rendering refuses the stale stem until you re-render or re-import it.

### Input / Pitch correction

For the selected recorded/imported voice: **Enable correction**, pick the **key** (C through B♭) and **scale** (chromatic, major, natural minor, major/minor pentatonic), then set **strength**, **retune speed** (0–250 ms), and **wet/dry** mix.

- **Gentle correction** preset: 65% strength, 100 ms. **Hard-tuned effect**: 100%, 0 ms.
- **Solo this part** to hear it. The **Original recording** player stays available for A/B.
- Offline, monophonic, processed with the WORLD vocoder — not live monitoring. Your source WAV is never altered; the corrected version is cached separately. Noise, breathiness and screams can cause artifacts — listen before trusting it.

### 06 / Your rendered performance

Status line, progress bar, and on completion: an audio player, **download links for the full mix and every section stem**, and render info (duration, render time). Outputs are 44.1 kHz / 24-bit stereo WAVs, peak-limited with a common gain so nothing clips.

**Autosave:** your project is saved to the browser's local storage as you work — a convenience, not a backup. **Save project** downloads the real file. If the score changed *during* a render, the info line tells you the playback used the earlier score.

---

## 7. MIDI setup

### The live path (sound right now)

You need a **virtual MIDI cable** — software that pretends to be a MIDI port so two apps can talk:

- **Windows:** install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) (free) and create a port named `Volta Choir`.
- **macOS:** use the built-in IAC Driver (Audio MIDI Setup → MIDI Studio → IAC Driver → enable).

Then:

```bat
.venv\Scripts\python.exe -m pip install sounddevice python-rtmidi
.venv\Scripts\python.exe live.py --list-ports
```

`--list-ports` should show your cable's port. If it prints *"No MIDI input ports found"*, the cable app isn't running or the port wasn't created — create the port first, then start `live.py`.

### The web-app path (notes into the score)

Open the **Play from hardware** panel:

1. **Connect MIDI**, grant the browser permission, and choose your controller's input (e.g. the Akai MPK mini's performance MIDI port). Web MIDI needs Chrome/Edge and a secure context — `localhost` counts.
2. **Learn controls before anything else.** Under **Assign to**, pick an action, click **Learn control**, then press the pad or turn the knob. Learning consumes the message without touching your score. There are no factory presets — everything is learned explicitly, so a custom hardware program can't trigger the wrong thing.
3. Choose the **knob message mode** to match your hardware: *Absolute 0–127*, *Relative · two's complement*, or *Relative · binary offset*.
4. For note entry: select a generated vocal part, pick a **vowel** and **note length**, enable **Arm note entry**. Each keypress appends one note (MIDI 24–96); velocity 100–127 adds an accent. Keys are *not* learned — any unassigned note-on enters a note.

**Assignable actions:**

| Pads (note messages) | Knobs (CC messages) |
|---|---|
| Vowel a / e / i / o / u select | Part level, pan |
| Next sequencer step | Vibrato depth, formant, glide |
| Play latest render / stop playback | Accent strength, tone, grit, delay |
| | Input tuning strength |

Knob edits affect the *next* render — hardware never synthesizes live lyrics; it edits the score. Disabled controls stay unavailable (formant won't touch sampled voices; tuning strength only applies to imported recordings and doesn't auto-enable correction).

**Housekeeping:** mappings are stored per device and MIDI channel in the browser. If a device reconnects with a changed ID, it's relinked only when name + manufacturer match exactly one live port — otherwise you pick manually. **Stop / reset controls**, disconnecting, changing channel/part/project, or unplugging all disarm note entry. **Stop / reset controls** also stops audio playback.

**Test it:** `npm run test:hardware` and `npm run test:dom` from `tools/cantabile` (after `npm install`) — they use simulated MIDI/devices and verify routing and UI state, not your actual USB hardware.

### Channels — watch the numbering

- `live.py --channel` uses **0–15** (raw MIDI).
- The web panel's channel dropdown shows **All channels, 1–16** (musician numbering).

Channel 1 in the panel = `--channel 0` on the command line. When in doubt, leave both on omni/all.

### Panic / stuck notes

- The live player honors MIDI **CC 123 (all-notes-off)** — Volta sends it on panic and note-off.
- If a note hangs after a crash, **restart `live.py`**.

---

## 8. Volta Choir link

Volta and Cantabile are separate apps; the live link joins them with a MIDI cable:

```
Volta keyboard → Web MIDI out → virtual MIDI cable → live.py → your speakers
```

**Setup:**

1. Create the virtual port (`Volta Choir` on loopMIDI; IAC Driver on macOS).
2. In `tools/cantabile`:
   ```bat
   .venv\Scripts\python.exe live.py --voice vs-f1 --vowel ah --midi-port "Volta Choir"
   ```
3. In Volta, click **Choir link** in the header, tick **Send notes to choir**, choose the `Volta Choir` port.
4. Play. The recorded singer follows with ~10–20 ms latency.

**Two-part choir:** run a second `live.py` with a different voice and `--channel`, and have the second source send on that channel.

**Limits:** recorded vowels only (no Hanami/TIGER, no lyrics), one vowel held per instance, no pitch bend — Volta's glide arrives as stepped pitches.

**If it's silent:** check the port exists *before* starting `live.py`; if you created the port after opening Volta, close and reopen the Volta tab; confirm the bank is unpacked (`prepare_bank.py`); check your system audio output.

---

## 9. Building the vowel bank

You don't need this to *use* Cantabile — the bank ships prebuilt in `vocal-bank/packs/`. This section is for the curious and for rebuilding from the original research recordings.

**Pipeline** (in order, from `bank_tools/`):

1. **`download_sources.py`** — fetches the selected original VocalSet ZIP members by HTTP range and verifies their CRCs. The selection is pinned in `source-selection.json`.
2. **`build_bank.py`** — cuts sustained-note excerpts, estimates and refines pitch, removes DC offset, adjusts level, adds fades, bakes sustain-loop crossfades, and writes the 1,309 samples plus metadata. Flags: `--source DIR` (default `.bank_sources/vocalset-raw`), `--output DIR` (default `vocal-bank`).
3. **`quality_gate.py`** — independent YIN-vs-WORLD pitch comparison; rejected 72 of 1,381 candidates, leaving 1,309. (Checks: YIN and WORLD pitch agree within 0.6 semitone; ≥55% voiced frames.)
4. **`render_examples.py`** — renders the example audio and previews.
5. **`sfz.py`** — writes the 78 SFZ patches (library function `write(voices, dest)`; no CLI flags).

**Recording your own vowels instead:** you don't need the pipeline. Record yourself (see [Microphone input](#6-web-ui-reference)), import the WAV, and it becomes a voice in your project. The bank pipeline is only for rebuilding the shipped 20-singer bank from VocalSet.

**Using the bank in a DAW:** load any `vocal-bank/sfz/*.sfz` in a compatible sampler. Each patch is one singer + one technique; press a vowel keyswitch first:

| MIDI note | Vowel |
|---|---|
| 24 (C1) | a |
| 25 (C♯1) | e |
| 26 (D1) | i |
| 27 (E♭1) | o |
| 28 (E1) | u |

(MIDI numbers are authoritative — sampler octave names vary.) A standalone audition page, `vocal-bank/index.html`, plays every voice's preview with no Python needed, and `Voice_Tour.wav` plays excerpts of all 20 (`Voice_Tour_Timing.json` marks the positions). SFZ playback in third-party samplers is structurally checked but wasn't auditioned here — listen before committing.

---

## 10. CLI reference

All commands run from `tools/cantabile`. On Windows use `.venv\Scripts\python.exe`; on Mac/Linux activate the venv first.

### `app.py` — the web app server

```
python app.py [--port 8765] [--no-browser]
```

| Flag | Default | Notes |
|---|---|---|
| `--port N` | `8765` | Server port. Use if 8765 is taken. |
| `--no-browser` | off | Don't auto-open the browser on launch. |

On startup it runs the bank preparation automatically, binds `127.0.0.1`, and opens the browser unless `--no-browser`.

### `live.py` — the live player

```
python live.py [--voice vs-f1] [--vowel ah] [--technique T]
               [--midi-port NAME] [--channel 0-15]
               [--list-voices] [--list-ports]
```

Full flag table in [Section 5](#5-the-live-player). Missing `sounddevice`/`mido`/`python-rtmidi` produce plain-language install instructions instead of tracebacks.

### `prepare_bank.py` — verify & unpack the bank

```
python prepare_bank.py
```

No flags. Verifies all 20 pack SHA-256 hashes, extracts missing samples into `vocal-bank/samples/`, leaves matching files untouched, and **refuses to overwrite** a sample that changed (it reports the path instead). Prints e.g. `Recorded vocal bank ready: 0 extracted, 1309 verified across 20 packs.`

### `setup_assets.py` — download the neural voice models

```
python setup_assets.py [--voice {all,hanami,tiger}]
```

Downloads the pinned originals from their creators (~537 MB Hanami + ~556 MB TIGER), verifies SHA-256, installs under `models/`. Skips anything already installed. Voice terms: see [FAQ](#13-faq) / THIRD_PARTY.md.

### `bank_tools/build_bank.py` — rebuild the bank from sources

```
python bank_tools/build_bank.py [--source DIR] [--output DIR]
```

Defaults: source `.bank_sources/vocalset-raw`, output `vocal-bank`. The other `bank_tools` scripts are pipeline/library modules without their own CLI flags.

### Windows launchers

| Launcher | Runs |
|---|---|
| `setup-windows.bat` | venv → `prepare_bank.py` → `pip install -r requirements.txt` → `setup_assets.py` |
| `setup-bank-only-windows.bat` | venv → `prepare_bank.py` → `pip install -r requirements.txt` (no voice download) |
| `setup-voices-windows.bat` | `setup_assets.py` (requires an existing `.venv`) |
| `start-windows.bat` | `.venv\Scripts\python.exe app.py` (requires setup first) |

---

## 11. Configuration files reference

| File | Purpose |
|---|---|
| `vocal-bank/manifest.json` | The bank catalog: 20 voices, techniques, sampled ranges, per-sample metadata (source path, time interval, hashes, root pitch, loop bounds, pitch-check data). |
| `vocal-bank/packs/manifest.json` | Pack integrity: per-ZIP filename, size, file count, unpacked size, SHA-256. This is what `prepare_bank.py` verifies. |
| `vocal-bank/BUILD_REPORT.json` | How the bank was built: candidate counts, rejections, coverage. |
| `vocal-bank/PITCH_AUDIT.json` | Per-sample pitch analysis results. |
| `vocal-bank/baselines/*.json` | One saved neutral baseline project per singer (`vs-f1.json` … `vs-m11.json`). |
| `vocal-bank/Voice_Tour_Timing.json` | Timestamps identifying each voice inside `Voice_Tour.wav`. |
| `vocal-bank/ATTRIBUTION.md` | CC BY 4.0 credit text and modification notes for the VocalSet material (includes a suggested credit line). |
| `bank_tools/source-selection.json` | Pinned list of source recordings the bank was built from. |
| `requirements.txt` / `requirements-tested.txt` | Python dependencies (loose ranges / exact versions validated under Python 3.12). |
| `MANIFEST.json` | SHA-256 of every tracked project file — tamper-evidence for the source tree. |
| Your saved project `.json` | Your score: tracks, notes, lyrics, voice settings, baselines, groove patterns. References (not copies of) imported WAVs. |

**Generated folders** (safe to delete; recreated by setup): `.venv/`, `models/`, `vocal-bank/samples/`, `renders/`, `imports/`, `.downloads/`, `cache/`.

---

## 12. Troubleshooting

**Setup picked the wrong Python (e.g. 3.14 instead of 3.13).**
→ The launcher only creates `.venv` when it's missing, and `py -3` means "newest 3.x". Run `py -0` to list installed versions, then:
```bat
cd C:\path\to\tools\cantabile
rmdir /s /q .venv
py -3.13 -m venv .venv
```
Then re-run your setup `.bat`. Verify with `.venv\Scripts\python.exe --version`.

**"Setup did not finish."**
→ Read the error above that line — it's usually a download hiccup (retry) or a missing Python. The script is idempotent: just run it again.

**Browser opens but the page says "Cannot open the local engine".**
→ The Python server crashed on startup. Look at the terminal window for the traceback — the usual cause is a failed `prepare_bank.py` (see next item).

**`prepare_bank.py`: "Existing sample differs; preserving your file".**
→ Something changed a file under `vocal-bank/samples/`. If you didn't mean to edit it, delete that file (or the whole `vocal-bank/samples/` folder — the ZIPs are kept) and run `prepare_bank.py` again.

**Port 8765 is already in use.**
→ `python app.py --port 8770` (or kill whatever's on 8765). `start-windows.bat` doesn't take flags — run `app.py` directly from the venv for this.

**`live.py`: "No MIDI input ports found".**
→ Start loopMIDI (or enable the IAC Driver) and create the port *before* launching `live.py`.

**`live.py`: "the recorded vocal bank is not unpacked".**
→ Run `python prepare_bank.py` in `tools/cantabile`.

**Volta shows "No MIDI" / the port isn't in Volta's list.**
→ Web MIDI needs a secure context (`localhost` is fine; plain HTTP from another machine is not). If you created the port after opening Volta, close and reopen the tab.

**No sound from the live player.**
→ Check `--list-voices` for the voice id, `--list-ports` for the port, confirm the bank is unpacked, and check your *system* audio output device — `live.py` plays through the default output.

**A live note hangs.**
→ Volta sends all-notes-off (CC 123) on panic; if a note survives a crash, restart `live.py`.

**Microphone: "permission was denied".**
→ Allow it in the browser's site settings and try again. Recording needs Chrome/Edge on localhost or HTTPS.

**Microphone: "Selected audio input is unavailable."**
→ Reconnect the device, click **Refresh audio inputs**, and select it again. The selector never silently substitutes another mic.

**"Use a WAV shorter than 62 seconds" / import rejected.**
→ The stem endpoint requires uncompressed mono/stereo WAV under 62 s. Also: imported stems must start at project time zero.

**"Stale stem" — rendering refuses your imported voice after a tempo/score change.**
→ By design. Re-render the voice from the project start (or re-import the WAV) so timing lines up again.

**Render is stuck / you want out.**
→ **Cancel** waits for the current voice operation to finish; your score is never modified by cancelling.

**My `pip install` needs a C++ compiler.**
→ It shouldn't: the requirements use `pyworld-prebuilt` specifically to avoid that. If pip tries to build PyWORLD from source, your Python version likely has no prebuilt wheel — stick to 3.12/3.13.

**The page looks broken / buttons do nothing.**
→ Hard-refresh (Ctrl+Shift+R). The server sends `no-store` cache headers, but a stale JS bundle from an older checkout can linger.

---

## 13. FAQ

**Does it work offline?**
Yes — after setup. Rendering, the bank, correction, and the live player are all local. Telemetry is explicitly disabled (`ORT_DISABLE_TELEMETRY=1` is set before ONNX Runtime initializes).

**Can I use this commercially?**
Not as-is. The neural voices carry noncommercial terms: Hanami's bundled vocoder is CC BY-NC-SA 4.0, and TIGER's license is CC BY-NC-ND 4.0 with a Commons Clause — both restrict commercial use without a separate license from the creators. The *recorded* VocalSet bank is CC BY 4.0, which does permit commercial reuse with attribution (see `vocal-bank/ATTRIBUTION.md` for the credit line). The VSCO orchestral samples are CC0. When in doubt, read `THIRD_PARTY.md` and the `notices/` folder.

**Can the live player sing words?**
No — one held vowel per instance. Words, consonants and the neural voices are render-only.

**Why does my recorded singer sound different two octaves up?**
Notes outside a singer's sampled range are resampled from the nearest recorded pitch — like varispeed on tape. The bank panel shows each singer's real sampled range.

**How long can a piece be?**
60 seconds, up to 16 tracks, 32 enabled singers. (Prototype limits.)

**Where do my recordings go?**
Nowhere but your machine: browser storage until imported, then the app's `imports/` folder. There is no upload.

**What's the difference between the three setup scripts?**
`setup-windows.bat` = everything including the 1.1 GB neural download. `setup-bank-only-windows.bat` = everything *except* that download. `setup-voices-windows.bat` = just the download, for later.

**Do I need the neural voices at all?**
No. The recorded bank, mic input, pitch correction, live player and SFZ patches all work without them. The engine status line tells you what's installed.

**Can I use the singers in my DAW?**
Yes — load `vocal-bank/sfz/*.sfz` in any SFZ-capable sampler (see the keyswitch table in [Section 9](#9-building-the-vowel-bank)).

**It rendered but something sounds wrong. Now what?**
Solo the part, check the note pitches against the range hints, and try the **Hear baseline** A/B. For rhythmic patterns, try a slower tempo or longer gates. Note the exact part/word/time of any defect — that's the currency of the next development pass.

---

## 14. Glossary

- **Baseline** — a saved neutral performance per voice: notes plus voice settings, used as a starting point and safety net (create / hear / reset).
- **Vowel bank** — the 20 recorded singers and their 1,309 multisamples. Vowels only, no words.
- **Technique** — how a vowel was sung in the recording session: *straight*, *vibrato*, *breathy*, *belt*.
- **Sampled range** — the pitches actually recorded for a singer; shown per voice in the bank panel.
- **SFZ** — an open sampler patch format; Cantabile ships 78 patches (one per singer × technique).
- **Keyswitch** — a low MIDI note (here 24–28) that selects the vowel in an SFZ patch instead of sounding.
- **Stem** — an individual rendered track (one WAV per section) alongside the full mix.
- **Voice Lab** — the nine per-part shaping controls (transpose, formant, vibrato, glide, accent, tone, grit, delay).
- **Vocal Groove** — the 16-step syllable sequencer for rhythmic vocal chops.
- **Retrigger (ratchet)** — multiple hits of one step within its time slot (1–4).
- **Swing** — rhythmic offset that loosens straight timing (0–60%).
- **Gate** — how long the vowel lasts within its step (0.4–1).
- **ARPAbet** — the phonetic spelling Cantabile uses for consonants and vowel overrides (`b`, `sh`, `iy`, …).
- **CMUdict** — the pronunciation dictionary that turns your words into phonemes.
- **WORLD** — the vocoder used for offline pitch correction of recordings.
- **ONNX** — the model format the neural voices run in (via ONNX Runtime).
- **DiffSinger** — the neural singing-synthesis architecture behind Hanami and TIGER.
- **Formant** — the resonant character of a voice, independent of its pitch.
- **MIDI CC 123** — the "all notes off" message; the live player's panic button.
- **loopMIDI / IAC Driver** — virtual MIDI cables (Windows / macOS) that let apps send MIDI to each other.
- **Monophonic** — one note at a time (every vocal part; also the mic guide detector).

---

*Manual for Cantabile prototype 0.2. Written from the project source in `tools/cantabile` — when in doubt, the code and the docs there (`README.md`, `LIVE_LINK.md`, `HARDWARE.md`, `VERIFICATION.md`, `THIRD_PARTY.md`) are authoritative.*
