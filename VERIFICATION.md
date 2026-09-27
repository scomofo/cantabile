# Verification — prototype 0.2

## Volta companion import — September 27, 2026

- The companion is under `tools/cantabile`; it is a separate Python app, not a
  hosted Volta route. No Volta synth source files were changed for this import.
- **31 Python tests: 30 passed, one explicitly skipped** without the optional
  neural models. The original full-model 25-test validation is recorded below.
- The DOM suite passes without neural models using a fixed example project;
  startup includes a timeout, Python executable override and process cleanup.
- The 1,309 sample WAVs are stored in **20 local singer ZIP bundles**. A fresh
  pack-only copy extracted all samples; a second preparation verified every
  file and preserved its timestamp. SHA-256, ZIP path/type/duplicate checks,
  declared sizes/counts and edited-file preservation have regression coverage.
- Windows setup and application startup prepare the bank locally. No network
  request is made by bank preparation. Original source/output hashes remain in
  the bank manifest; the packs have a separate size/SHA-256 manifest.
- Volta's `npm test`, `npm run lint`, `npm run typecheck` and `npm run build`
  passed with the companion present. Cantabile has an independent CI workflow.
- No new real-browser, physical-controller, Windows or microphone acceptance is
  claimed. The prior browser sandbox rejection still applies. The Akai/404
  mapping in `HARDWARE.md` is a proposed follow-up, not implemented support.

## Passed in this environment

- **25 Python tests**, including real neural audio rendering, a two-singer section, finite/non-silent stereo output, peak bounds, repeat-render cache identity, and cancellation.
- Validation for all six choir ranges in solo/ensemble modes, maximum singer counts, malformed notes and non-finite values, overlapping vocal notes, and valid/invalid melisma continuations.
- Syllable-pattern compilation retained swing, non-overlapping timing, holds, retriggers and accents. Invalid holds/phones/retriggers and invalid voice-control values were rejected.
- MIDI roundtrip retained melody, word events and tempo. MusicXML retained words, rests, ties and measure durations.
- Synthetic three-note microphone guide recovered C4, E4, G4 with expected quantized timing. Silence correctly returned no melody.
- Local HTTP API returned model state, rejected foreign origins, rejected path traversal, imported/resampled a WAV stem, and refused reuse after a tempo change.
- **DOM interface checks**: all six section types, independent solo/ensemble controls, male/female source selections, lyric mismatch preserving notes, successful lyric assignment, section renaming, local autosave, score SVG/table generation, voice presets/sliders, pattern editing and HTTP score transfer (including swing, holds, repeats and accents), and microphone permission-denied feedback.
- JavaScript syntax and Python compilation passed.
- Actual full audio exports:
  - Solo voice plus orchestra: **21.09 seconds**, ~15.9 seconds to render on the available CPU during the initial test.
  - Soprano, alto, tenor and baritone plus orchestra: **21.09 seconds**, **75.37 seconds** to render. Female parts use Hanami, male parts use TIGER Fresh/Vinyl. Both are 44.1 kHz, 24-bit WAV files.

- Rhythmic TIGER vocal groove: **14.27 seconds**, **11.71 seconds** to render. Includes custom phonemes, accents, vowel holds, retriggers, formant shaping, tone, grit and delay. Stereo 44.1 kHz / 24-bit PCM; finite samples and peak ~0.409.
- A subsequent render-process check was blocked by automatic review for an unsolicited runtime telemetry connection. The package now sets the documented `ORT_DISABLE_TELEMETRY=1` opt-out before importing ONNX Runtime and calls its telemetry-disable API before inference sessions. The Python and DOM checks were rerun with this change. No packet-capture privacy audit is claimed.

## Vocal bank, baselines and correction

- 20 recorded singers; initially 1,381 candidate samples from 401 selected source recordings. Fourteen source recordings produced no usable segment. Independent WORLD/YIN comparison rejected 72 samples, leaving **1,309**. Every retained sample has a source interval, raw/output hash, loop bounds and pitch-check metadata.
- Rendered a neutral baseline for every singer and a six-person recorded choir. The bank rejects arbitrary words instead of silently substituting vowels. Vowel holds, changed pitches and accent rendering passed.
- Tests cover key/scale mapping, unvoiced frames, bypass, finite output, original-input preservation and output length. A harmonic signal deliberately detuned +35 cents was corrected to within 12 cents of the target in the hard setting.
- DOM checks include the 20-singer catalog, female filter, recorded-technique controls, baseline creation/render/reset, baseline preservation through edits, input WAV import, correction settings and original-recording playback URL.
- A recorded vocal demonstration was also rendered in original/gentle/hard variants. It has not undergone expert listening acceptance.

- Final integrity check passed for all 1,309 sample hashes, finite audio, peak bounds, sustain-loop positions, 78 SFZ patch sample references, and 20 baseline previews. The recorded choir and input-correction comparison both contain finite, nonclipping audio.

## Explicitly not passed or claimed

- **Real-browser acceptance is blocked.** Chrome's local IPC socket creation was denied in the sandbox. An explicit escalation request was automatically rejected because this environment disables sandbox approvals. No browser screenshot or successful browser microphone session is claimed.
- `tests/browser.cjs` is provided for execution on a normal machine. It has not completed here. DOM tests do not establish layout, browser audio playback, hardware permissions or download behavior.
- SFZ mappings are checked structurally; no third-party SFZ sampler playback is claimed.
- No physical microphone, audio interface, Windows launcher, user-specific Python installation or Windows download workflow was available for acceptance.
- Audio output was checked technically; no expert listening panel has established realism, intelligibility on arbitrary lyrics, natural bass registers or choir blend. The demo is the listening checkpoint.

## Smallest local acceptance check

1. Run setup and start on Windows. Render the supplied solo example; play and download it.
2. Add a baritone, select TIGER, switch between Soloist and Ensemble, and use Solo this part. Repeat with a soprano and Hanami.
3. Record three slowly sung/hummed notes. Stop; play the recording; choose Recording → notes; inspect the three pitches. Assign three words and render.
4. Use a recording as a voice. Render it, then change tempo and confirm that the stale-stem message appears.
5. Save/reopen the project and check notes, section counts, voice assignments and words.
6. Open vocal-groove.json; render it, change a vowel, send the pattern again and render. Try each Voice Lab preset, then save/reopen and check those controls.
7. Listen to the mixed-choir example for clear consonants, believable range, correct syllable timing, balanced blend and artifacts. Record the exact word/part/time of any defect for the next pass.

For rebuilding the sample bank, run bank_tools/download_sources.py, build_bank.py, quality_gate.py, then render_examples.py in that order. Runtime requirements include the prebuilt PyWORLD package to avoid requiring a local C++ compiler.
