# Cantabile — Vocal Bank & Choir Prototype 0.2

A local, render-first composition app for Scott: build a choir, select individual male/female voices, create an adjustable baseline, sequence lyrics or vowels, record an input, correct its pitch, render, and listen.

New in 0.2: **20 recorded singers, 1,309 processed vowel samples, 78 SFZ patches, individual voice baselines, and offline pitch correction for input vocals.**

Cantabile is a separate local companion to Volta, with WAV files as the handoff to a
DAW or sampler. For real-time playing, the **live link** connects the two apps:
enable **Choir link** in Volta's header, choose a MIDI output port, and run
`python live.py` here — the recorded singers then sing Volta's notes as you play
them. See [LIVE_LINK.md](LIVE_LINK.md) for the full setup. Open **Play from hardware** for live MIDI step entry, pad/knob learning and
saved mappings. The microphone panel includes an audio-input selector for the
SP-404MKII or another available interface. See [HARDWARE.md](HARDWARE.md) for setup
and the remaining physical validation steps.

This is a working first prototype, not a finished orchestral workstation. It uses real neural singing synthesis and recorded orchestral samples. It does not substitute prerecorded phrases or pitch-shift text-to-speech.

## Start on Windows

1. Clone this repo (or open `tools/cantabile` in a Volta checkout, where Cantabile is included as a submodule) to a normal folder.
2. Install **Python 3.12 or 3.13, 64-bit** from https://www.python.org/downloads/windows/ if you do not already have it.
3. Double-click **setup-windows.bat** once. It installs Python dependencies into a project-local environment and downloads two original voicebanks, about **1.1 GB total**. Allow several minutes and at least 4 GB of free disk space. See the voice terms in THIRD_PARTY.md.
   For the recorded bank and microphone correction without the 1.1 GB neural download, use **setup-bank-only-windows.bat** instead. You can add neural lyrics later with **setup-voices-windows.bat**.
4. Double-click **start-windows.bat**. Your browser opens at **http://127.0.0.1:8765**. Leave the terminal window open while using the app.
5. Open **Recorded voice bank**, choose a singer, and click **Create baseline**. Or open `examples/recorded-choir.json` for six independent recorded singers and `examples/barbershop-start.json` for a four-part starting arrangement.
6. Click **Render ensemble** to hear “Hold the Light.” Open `examples/mixed-choir.json` to try the four-part choir. Open `examples/vocal-groove.json` for the syllable sequencer demo. Finished examples are also in `examples/audio/`, so you can listen before installing anything.

The standalone `vocal-bank/index.html` auditions its supplied previews without Python. The repository stores samples in 20 compressed singer bundles under `vocal-bank/packs/`. Windows setup/start extracts them automatically. On Linux/macOS, or before loading SFZ files from a fresh checkout, run `python prepare_bank.py` once from this directory; it checks archive hashes and safely expands the local samples. Existing changed samples are reported rather than overwritten. Then load the SFZ files in a compatible sampler. The bank has its own CC BY 4.0 attribution instructions.

No account, API key or paid service is required for this prototype. After setup, rendering works offline. Runtime telemetry is explicitly disabled before ONNX Runtime initializes. Chrome or Edge is recommended for microphone support. A CPU is sufficient; an 8 GB RAM machine is a sensible starting point. Windows launchers are supplied but have not been exercised on Windows in this environment.

## Three vocal sources

| Source | What it can do | Terms / practical limits |
|---|---|---|
| Recorded VocalSet bank | 20 different human singers; recorded vowels; straight, vibrato, breathy and belt options; editable pitch/timing and effects | CC BY 4.0 with attribution. Not arbitrary words; some technique/vowel gaps. Resampling and loops can be audible. |
| Hanami and TIGER neural voices | Sing supplied English words, phonemes and syllable patterns | Two underlying identities, three selectable modes. Dependencies include noncommercial terms; this build does not clear them for commercial use. |
| Your mic / imported vocal | Keep your real performance; apply key/scale pitch correction and effects | Original file is not overwritten. Use isolated vocals; no voice cloning or automatic word replacement. |

## A baseline for every voice

Every recorded singer has a supplied neutral baseline in `vocal-bank/baselines/` and a playable preview. Select a recorded or neural voice and click **Create baseline** to generate a neutral performance in that part, save its settings/notes as a reference, and render it. This replaces the current part's notes after confirmation.

Change the score, vowels, technique, voice controls and effects. **Hear baseline** renders the saved reference without replacing your edits. **Reset to baseline** restores the reference. Project saves include it. Recorded inputs instead retain their original untuned playback in the correction panel.

The bank's original samples remain unchanged by these controls. It was built from attributed VocalSet recordings, not a newly trained 20-singer lyric model. See `vocal-bank/README.md`, `ATTRIBUTION.md`, the source/processing manifest and pitch-audit report.

## Build your choir

- Add **soprano, mezzo-soprano, alto, tenor, baritone or bass** sections. You can add more than one of a range, such as Tenor I and Tenor II.
- Every range offers **Soloist** (one singer) and **Ensemble** (2–8 singers). Up to 16 tracks and 32 enabled singers are supported in this prototype.
- Select **Hanami / female**, **TIGER / male / Fresh**, or **TIGER / male / Vinyl**, independently of the section range. You can also select one of the 20 recorded VocalSet singers or record/import your own voice.
- Use section checkboxes to include/exclude parts. **Solo this part** renders only the selected part without changing the ensemble checkboxes.
- Adjust each part's level, stereo position and ensemble spread. Multiple singers are separately synthesized with small performance variations. They still share the chosen underlying voice identity; they are not a collection of independently trained singers.
- The note-range hints are composition guides. They do not prove that the installed voice sounds natural on every note. The two neural voices are a starting palette, not specialist classical lyric voicebanks for every fach or register. The recorded bank adds real source voice types, with measured sampled coverage. Convincing operatic tenor, baritone and deep bass timbres need further listening work and appropriate models.

## Words and music

The selected section has its own notes and lyrics. Expand **Edit notes & pronunciation** to change note starts, lengths and MIDI pitches. C4 is MIDI 60. Times are in quarter-note beats, starting from zero.

Enter one word per note in the lyric field and click **Apply lyrics**. The word count must match the note count. Use **+** on a directly adjacent note to continue the preceding word across a second pitch. A whole multisyllabic word can occupy one note; independent syllable placement can be specified through the per-note phoneme field.

English pronunciations come from CMUdict. For names or unknown words, enter space-separated, lowercase ARPAbet sounds in the note's **Phonemes** field. For example, `light` → `l ay t`, `night` → `n ay t`. Unknown words produce an error with the word identified; they are not silently replaced.

**Import MIDI** lets you choose a track. Existing lyric events are preserved; otherwise notes start with `ah`. Vocal parts must be monophonic. The first version rejects variable-tempo files and overlapping vocal notes rather than silently changing their timing. The prototype supports constant-tempo compositions up to 60 seconds.

**Export vocal score** writes MusicXML containing all enabled vocal parts, their words, rests and ties. You can open it in a compatible external singing editor, use another voice, render a WAV from the beginning of the project, and import the result back into its section.

## Vocal groove and voice shaping

The **Voice Lab** exposes nine per-part controls: transpose (±12 semitones), formant color, vibrato depth/rate, glide, accent strength, dark/bright tone, grit and tempo-synced eighth-note delay. Start with Natural choir, Tight rhythmic vocal, Wide hook or Rough chant, then edit any control. Wide hook sets four singers and stereo spread; the other presets preserve the singer count. Glide applies between adjacent notes; rhythmic delivery suppresses vibrato. These are synthesis/effect settings, not newly trained vocal identities. Tone, grit and delay also work on recorded voices; synthesis controls do not retune imported recordings.

The **Vocal Groove** panel has 16 steps. Select a step and set its consonant onset, vowel and ending, MIDI pitch, gate, accent and 1–4 retriggers. A vowel hold joins the previous enabled step; the pitch can change during a hold. Choose eighth/sixteenth notes, swing and 1–4 pattern repeats. Click **Send pattern to this part**, then **Solo this part** to render. Editing the pattern does not change the score until you send it again. The note table also lets you accent individual notes.

Try `b` + `uw` + `m` for “boom,” `b` + `iy` + `t` for “beat,” or `k` + `ah` for “kah.” Use lowercase ARPAbet consonants: `b ch d dh f g hh jh k l m n ng p r s sh t th v w y z zh`. There are 15 vowel choices with word examples. You can alter pronunciations manually; regional accent models are not included. Very short notes with many consonants or retriggers may need a slower tempo, longer gate or simpler syllable.

The included “Bring That Beat Back” example is a **rhythmic neural vocal sketch**, not a claim of natural spoken rap. Grit is a distortion effect, not trained growling or screaming. See STYLE_ROADMAP.md for barbershop, opera and metal expansion.

## Microphone

1. Select the destination section.
2. Click **Record mic**, allow the browser's microphone request, and sing or hum one line. Click **Stop recording** when done. Recording stops automatically at 60 seconds.
3. Choose either:
   - **Recording → notes:** detect a monophonic guide melody, quantize it to quarter beats, review/correct the notes, and type your lyrics. This produces a new synthesized performance in the selected neural voice.
   - **Use recording as voice:** use your actual recording as that section's audio.

You can also use **Import voice WAV**. WAV stems should start at project time zero, including any leading silence. Imported audio initially plays as supplied. You can explicitly enable pitch correction below; automatic time stretching, word transcription and voice cloning are not included. If the score or tempo changes after import, rendering refuses that stale stem until you re-render/re-import it.

Mic recordings remain in this browser until you import them as a voice, at which point they are stored in the app's local `imports/` folder. There is no upload to an external service. Keep original WAVs: project JSON files contain references, not embedded audio. Changing computers requires copying `imports/` or importing the source WAVs again.

**Real-browser microphone capture and listening quality still need a check on your computer.** This environment blocked Chrome execution through its sandbox policy. The pitch detector passed synthetic-note tests and the interface's permission-denied path was checked, but that is not a physical microphone acceptance test.

## Pitch correction for recordings

Select a part using a recorded/imported WAV. The **Tune your recorded voice** panel lets you enable correction, choose a key and chromatic/major/natural-minor/pentatonic scale, set strength, retune speed (0–250 ms) and wet/dry mix. Gentle sets 65% strength and 100 ms; Hard sets 100% and 0 ms. Click **Solo this part** to render the corrected result.

The Original recording player remains available for comparison. Source audio is stored separately; corrected audio is cached separately and processed with WORLD's spectral-envelope/aperiodicity analysis. Unvoiced consonants/breaths are blended from the original near detected boundaries. This is offline monophonic correction, not live monitoring, polyphonic repair, an Antares product, or a guarantee of transparent results. Noise, breathiness, screams and rapid pitch changes can cause tracking artifacts. Listen before using the result.

The demo order in Cantabile_Pitch_Correction_Demo.wav is deliberately detuned sampled vocal → gentle → hard, separated by 0.6 seconds. Individual files are in examples/audio/.

## Render and save

Draft uses fewer acoustic iterations; Standard uses more. First renders take longer, especially for large ensembles. Unchanged voice performances are cached, so changing levels, pan, tone, grit, delay or hall amount can reuse them. A 21-second four-part choir example rendered in approximately 75 seconds on the available CPU; your machine and settings will differ.

Each completed render provides a 44.1 kHz, 24-bit stereo WAV mix and separate section/instrument stems. Output is peak-limited by a common gain reduction when necessary, preserving stem balance. Section stems include their voice effects; the full mix also includes the hall effect. A common gain protects both the mix and individual stems from clipping.

**Save project** downloads a JSON score. **Open project** validates before replacing the current score. Local browser autosave is a convenience, not a replacement for downloaded project files. Cancel waits for the current neural operation to finish; it does not change your composition.

## Mac / Linux / terminal

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python prepare_bank.py
python setup_assets.py
python app.py
```

Use `python app.py --no-browser --port 8765` to control launch behavior. The server listens only on 127.0.0.1 and rejects foreign browser origins. Do not expose this development server publicly.

## Verification

```sh
python -m unittest discover -s tests -v
```

Actual neural tests run when models are installed; otherwise the audio test is explicitly skipped. See VERIFICATION.md for what was exercised and what remains unverified.

Optional UI tests require Node and `npm install`. Run `npm run test:dom`. For browser acceptance, run `npx playwright install chromium`, then `npm run test:browser`. Set `CANTABILE_CHROME` to a Chrome executable if needed. The browser test uses a synthetic mic; it is not a substitute for checking a physical input device.

## Next development gate

1. Listen to the recorded and neural choir examples, compare each voice baseline, and test mic input plus correction on the target Windows PC.
2. Audition the rhythmic phrase for intelligibility and groove. Improve phrase transitions and consonant placement; add an expressive pitch-curve editor and undo.
3. Audition specialist classical voices, especially genuine baritone/bass and alto timbres. Establish commercially usable voice/vocoder dependencies before a commercial product.
4. Expand orchestral samples, articulations and room control after vocal intelligibility and ensemble blend pass listening acceptance.

Core files: `cantabile/voice.py` (neural inference), `render.py` (samples/mix/cache), `score.py` (project rules), `pattern.py` (syllable sequencer), `bank.py` (recorded bank/baselines), `tuning.py` (input pitch correction), `microphone.py` (guide pitch extraction), `exchange.py` (MIDI/MusicXML), `app.py` (local API), and `web/` (choir editor).
