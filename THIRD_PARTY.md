# Sources, credits and usage boundaries

This package contains application source, a small CC0 orchestral sample selection, notices, and rendered examples. **It does not redistribute the voicebank archives or model weights.** The setup script retrieves exact pinned originals directly from their creators. The models are used unmodified for inference.

## Hoshino Hanami —LoveSong— NoTension beta

- Creator/voice: **Lotte V**.
- Pinned original release: https://github.com/lottev1991/LotteV-Voicebank-Update-Repo/releases/tag/v0.0.1b
- Creator's current voicebank terms: https://lottev.moe/utau/voicebank-license/
- SHA-256: `41bad5281f90d375a282513395c953ceae6a5903a5395bfef3e6974a16deec15`
- Bundled voicebank notice says CC BY 4.0; bundled custom vocoder notice says **CC BY-NC-SA 4.0**. The original readme also contains usage and redistribution terms. Copies of the bundled notices and readme are in `notices/`; preserve the original model's full notices on installation.
- This prototype therefore does not present Hanami plus that vocoder as an unrestricted commercial dependency. The creator has newer releases; the older one is deliberately pinned because its exact ONNX interface was implemented and exercised here.

## TIGER DiffSinger v103

- Creator/voice: **tigermeat / neutrogic**.
- Pinned original release: https://github.com/spicytigermeat/tiger_diffsinger/releases/tag/v103
- Current repository license: https://github.com/spicytigermeat/tiger_diffsinger/blob/master/LICENSE.md
- SHA-256: `dc1e2e7efd2960c5f672cb5719fbd5af602a2fc21d1742716c8ac4399b6e243a`
- The release's bundled custom license and the repository's current **CC BY-NC-ND 4.0 & Commons Clause** wording both restrict commercial use without a separate license. Copies are supplied in `notices/`.
- Fresh and Vinyl are two provided performance modes of one voice identity, not two independently recorded singers. This app selects their original speaker embeddings; it does not modify or train the model.
- The creator credits Millefeuille corpora: https://utaufrance.com/millefeuille-diffsinger/

## Orchestral samples

- **VS Chamber Orchestra: Community Edition**, recorded by Sam Gossner and Simon Dalzell; sample cutting by Elan Hickler/Soundemote.
- Original repository: https://github.com/sgossner/VSCO-2-CE
- License: **CC0 1.0**, included in `assets/VSCO-LICENSE.txt`.
- A small selection of violin section, cello section, flute and French horn sustain samples is included, unchanged. The renderer adjusts pitch, duration, gain and pan during playback. Sample filenames use an octave convention in which C3 corresponds to MIDI 60.

## Engine and dictionary foundations

- DiffSinger / OpenVPI model architecture and ONNX interfaces: https://github.com/openvpi/DiffSinger
- Original research: https://arxiv.org/abs/2105.02446
- OpenVPI's reference inference API informed interface selection: https://github.com/openvpi/DiffSingerMiniEngine
- CMU pronunciation dictionary: https://github.com/cmusphinx/cmudict ; installed through the `cmudict` package with its own notices.
- Runtime packages are installed separately under their respective licenses: NumPy, SciPy, ONNX Runtime, SoundFile and Mido. This prototype's inference and application code was written for this project; it does not bundle OpenUtau binaries, commercial plugins or cloned celebrity voices.

## Audio examples

“Hold the Light” is an original short test phrase and arrangement created for this prototype. Solo vocal: Hoshino Hanami by Lotte V. Mixed choir: Hoshino Hanami by Lotte V and TIGER by tigermeat, with recorded VSCO 2 CE instruments. “Bring That Beat Back” is an original rhythmic test arrangement using TIGER by tigermeat, with formant, accent and effect settings. Examples are supplied for personal prototype evaluation. Do not assume these prototype voice dependencies are cleared for commercial distribution or a paid service.

Runtime privacy reference: https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md . The app sets `ORT_DISABLE_TELEMETRY=1` before importing ONNX Runtime and calls `disable_telemetry_events()` before creating inference sessions.

## VocalSet recorded bank

VocalSet: A Singing Voice Dataset, Julia Wilkins, Prem Seetharaman, Alison Wahl and Bryan Pardo (2018), https://doi.org/10.5281/zenodo.1442513 . The original record identifies the audio dataset as CC BY 4.0. The sampled bank contains edited, looped, level-adjusted excerpts with per-file source paths, time intervals and hashes. Full credit and modifications are in vocal-bank/ATTRIBUTION.md. This source permits commercial reuse under its attribution terms; that does not change the separate Hanami/TIGER model terms.

## Input pitch correction

PyWORLD prebuilt distribution: https://github.com/tsukumijima/pyworld-prebuilt ; original wrapper: https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder (MIT). WORLD: https://github.com/mmorise/World (modified BSD). These packages are installed separately. The app uses DIO, StoneMask, CheapTrick, D4C and synthesis to correct an isolated input's estimated pitch while retaining its analyzed spectral envelope. No pretrained conversion model is used.
