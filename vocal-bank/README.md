# Cantabile Vocal Bank 01

**20 actual recorded singers · 1,309 multisamples · 78 SFZ patches · 20 editable baselines**

The source is VocalSet, not a newly recorded session or newly trained neural model. This is a curated and processed instrument bank. It provides real vocal timbres for vowel choirs, solo vowel lines, vocal pads and rhythmic chops. **It cannot sing arbitrary words.** Use Cantabile's separate neural voices for supplied lyrics and consonants, or import/record a vocal performance.

## Try it

Open **index.html** for a local audition page. Every voice has a neutral five-vowel preview. Voice_Tour.wav plays a short excerpt from all 20 voices; Voice_Tour_Timing.json identifies the positions.

In Cantabile, open the Recorded voice bank, choose Use voice, then Create baseline. The engine creates a neutral phrase in useful recorded pitches, stores a baseline copy and renders it. Edit pitches, timing, vowels, technique, accent strength, ensemble spread, tone, grit or delay. Hear baseline auditions the saved version without overwriting the adjusted score; Reset to baseline restores it. Save project retains the baseline. Baseline JSON projects are also provided in baselines/.

## In a DAW sampler

For a fresh Git checkout, first run `python prepare_bank.py` from the parent
Cantabile directory, or use its Windows setup launcher. This verifies the 20
local singer ZIP bundles and expands `samples/`. The audition previews above
work before extraction. Keep the ZIP packs and their manifest for verification.

Load an SFZ from sfz/ in a compatible sampler. Keep this whole folder together. Each patch selects one singer and one recorded technique. Press a vowel keyswitch before playing:

| MIDI note | Vowel |
|---|---|
| 24 / C1 | a |
| 25 / C♯1 | e |
| 26 / D1 | i |
| 27 / E♭1 | o |
| 28 / E1 | u |

Sampler octave names vary; MIDI numbers are authoritative. Players that support sw_default begin on a; others need the keyswitch. Notes outside mapped ranges do not sound. The files use ordinary SFZ sample/pitch, key-range, loop, envelope and keyswitch opcodes. Actual third-party SFZ-player playback has not been exercised here.

## Voices and techniques

F1–F9 are the dataset's female singers; M1–M11 are its male singers. Source voice types include soprano, mezzo-soprano, countertenor, tenor, baritone, bass and bass-baritone. Classification describes the source performer, not guaranteed realism at every transposed pitch.

Techniques: **straight, vibrato, breathy and belt**. Some singer/technique combinations have fewer than five usable vowels. manifest.json and BUILD_REPORT.json show exact coverage. Unavailable vowels are not replaced with a different singer. In Cantabile, a clear error requests another vowel or technique.

Each SFZ pitch zone uses a nearby recorded root and tuning adjustment. Away from recorded roots, resampling changes vocal color. Sustain loops and repeated samples can sound mechanical. Ensembles within one part are variations of one source; use different singer IDs on separate parts for independent people. Grit is processing, not a recorded scream or growl. These are not dedicated operatic or harsh-metal voice models.

## Quality and provenance

401 source recordings were inspected. Initial note segmentation produced 1,381 candidate samples; 14 recordings produced no usable candidate. A second pitch analysis rejected 72 candidates, leaving 1,309. Retained samples have YIN and WORLD pitch estimates agreeing within 0.6 semitone and at least 55% voiced frames in the WORLD check. WORLD refined the mapped root pitch. Technical checks do not establish perceptual realism; listen to the previews and combinations before relying on them in a production.

Samples are mono 44.1 kHz, 24-bit PCM WAVs. Previews are stereo WAVs. Raw recordings were excerpted, level-adjusted and looped; no new model was trained. See ATTRIBUTION.md for CC BY 4.0 credits and reuse terms.

Rebuild from the original sources using the application's bank_tools/download_sources.py, build_bank.py, quality_gate.py, then render_examples.py. The download script retrieves selected original ZIP members and verifies their CRCs. Keep the pinned source-selection manifest for provenance.
