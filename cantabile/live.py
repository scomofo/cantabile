"""Live choir link: sing the recorded vocal bank in real time from MIDI notes.

This is the Cantabile half of the Volta live link. A small player opens a MIDI
input port (a virtual cable fed by Volta's MIDI output), and for every note-on
it streams the nearest recorded vowel sample of the chosen singer, pitch-shifted
to the exact MIDI pitch with the same loop/interpolation math as the offline
renderer in bank.py. Note-off releases with a short fade.

Only the recorded vowel bank can sing live; the neural voices are render-first
and stay in the offline path. One voice per player instance; run a second
instance with --channel to build a two-part choir.

Audio output needs the `sounddevice` package and MIDI input needs a working
mido backend (`python-rtmidi`). Both are optional: this module imports without
them so the mapping/DSP logic stays unit-testable, and the CLI reports exactly
what to install when they are missing.

MIDI control map (matches what Volta transmits on the choir link): notes sing
the recorded samples; pitch wheel bends ±2 semitones; CC1 morphs the vowel
toward the adjacent sample; CC11 scales expression (gain); CC5 sets the
inter-note portamento time; CC123 is all-notes-off.
"""
import math
import threading

import numpy as np

from .bank import read_sample, voices, VOWELS

SR = 44100
ATTACK_SEC = 0.018
RELEASE_SEC = 0.090
CANONICAL_VOWELS = ('a', 'e', 'i', 'o', 'u')
PORTAMENTO_MAX_SEC = 1.5  # glide time at CC5 = 127
BEND_RANGE_SEMITONES = 2.0  # matches the pitch-bend range Volta transmits


def resolve_vowel(vowel):
    """Accept any bank lyric spelling, return the canonical vowel."""
    key = (vowel or '').strip().lower()
    if key not in VOWELS:
        raise ValueError(
            f'Vowel {vowel!r} is not sung by the recorded bank. '
            'Choose one of a/ah, e/eh, i/ee, o/oh, u/oo.'
        )
    return VOWELS[key]


def resolve_voice(voice_id):
    """Return (voice_id, technique) for a recorded bank voice."""
    bank = voices()
    if voice_id not in bank:
        sampled = sorted(bank)
        raise ValueError(
            f'Unknown voice {voice_id!r}. Recorded voices: {", ".join(sampled)}. '
            'Neural voices (hanami, tiger) cannot sing live; pick a recorded singer.'
        )
    voice = bank[voice_id]
    technique = 'straight' if 'straight' in voice['techniques'] else voice['techniques'][0]
    return voice, technique


def select_sample(voice, vowel, technique, pitch):
    """Nearest recorded sample for vowel/technique to the target MIDI pitch."""
    pool = [s for s in voice['samples']
            if s['technique'] == technique and s['vowel'] == vowel]
    if not pool:
        have = sorted({(s['technique'], s['vowel']) for s in voice['samples']})
        raise ValueError(
            f'{voice["name"]}: vowel {vowel!r} is unavailable in technique {technique!r}. '
            f'Available: {have}.'
        )
    return min(pool, key=lambda s: abs(s['root_midi'] - pitch))


def pitch_increment(pitch, root_midi, source_sr=SR, out_sr=SR):
    """Source-sample advance per output frame, mirroring bank.synthesize."""
    return 2 ** ((pitch - root_midi) / 12) * (source_sr / out_sr)


def resolve_port(wanted, available):
    """Match a MIDI port name: exact first, then case-insensitive substring."""
    if wanted in available:
        return wanted
    lowered = wanted.lower()
    for name in available:
        if lowered in name.lower():
            return name
    raise ValueError(
        f'MIDI port {wanted!r} not found. Available: {", ".join(available) or "none"}.'
    )


def _adjacent_vowel(vowel):
    """Next vowel in the canonical order, wrapping around; the CC1 morph target."""
    i = CANONICAL_VOWELS.index(vowel)
    return CANONICAL_VOWELS[(i + 1) % len(CANONICAL_VOWELS)]


class LiveNote:
    """One sounding note: looped sample playback with attack/release envelope."""

    def __init__(self, data, loop_start, loop_end, increment, peak, sr=SR, pitch=None):
        data = np.asarray(data, dtype=np.float32).reshape(-1)
        self.base_increment = float(increment)
        self.increment = float(increment)  # effective increment of the last block
        self.pitch = pitch
        self.peak = float(peak)
        self.bend_factor = 1.0
        self.morph_note = None
        self.morph_amount = 0.0
        self.glide_start_ratio = 1.0
        self.glide_total = 0
        self.glide_left = 0
        self.sr = sr
        self.a = int(loop_start)
        self.b = int(loop_end) + 1
        self.period = self.b - self.a
        self.pos = 0.0
        # Cyclic interpolation table, same construction as bank.synthesize.
        self.idx = np.arange(self.b + 1)
        self.cyclic = np.concatenate((data[:self.b], data[self.a:self.a + 1]))
        self.attack_n = max(1, round(ATTACK_SEC * sr))
        self.release_n = max(1, round(RELEASE_SEC * sr))
        self.age = 0
        self.rel_at = None
        self.finished = False

    def release(self):
        if self.rel_at is None:
            self.rel_at = self.age
            self.rel_gain = min(self.rel_at / self.attack_n, 1.0)
        if self.morph_note is not None:
            self.morph_note.release()

    def _render_raw(self, n):
        """Interpolated sample frames with bend/glide applied; no envelope."""
        inc = self.base_increment * self.bend_factor
        if self.glide_left > 0 and self.glide_total > 0:
            prog = 1.0 - self.glide_left / self.glide_total
            inc *= self.glide_start_ratio + (1.0 - self.glide_start_ratio) * prog
            self.glide_left = max(0, self.glide_left - n)
        self.increment = inc
        frames = np.arange(n)
        positions = self.pos + inc * frames
        positions = np.where(positions >= self.b,
                             self.a + (positions - self.b) % self.period,
                             positions)
        out = np.interp(positions, self.idx, self.cyclic)
        self.pos = float(positions[-1] + inc)
        return out

    def render(self, n):
        out = self._render_raw(n)
        partner = self.morph_note
        if partner is not None and self.morph_amount > 0.0:
            partner.bend_factor = self.bend_factor
            m = self.morph_amount
            out = out * (1.0 - m) + partner._render_raw(n) * m

        frames = np.arange(n)
        ages = self.age + frames
        if self.rel_at is None:
            env = np.minimum(ages / self.attack_n, 1.0)
        else:
            env = self.rel_gain * np.clip(1.0 - (ages - self.rel_at) / self.release_n, 0.0, 1.0)
            if ages[-1] - self.rel_at >= self.release_n:
                self.finished = True
        self.age += n
        return (out * env * self.peak).astype(np.float32)


class LivePlayer:
    """Polyphonic live singer. Thread-safe: MIDI thread mutates, audio thread mixes."""

    def __init__(self, voice_id, vowel='ah', technique=None, channel=None):
        self.vowel = resolve_vowel(vowel)
        self.voice, default_technique = resolve_voice(voice_id)
        self.technique = technique or default_technique
        self.channel = channel  # None = omni
        self.voice_id = voice_id
        self._notes = {}
        self._lock = threading.Lock()
        self._bend_semitones = 0.0
        self._bend_factor = 1.0
        self._expression = 1.0
        self._morph = 0.0
        self._portamento_sec = 0.0
        self._last_pitch = None

    def note_on(self, pitch, velocity=100):
        if not 0 <= pitch <= 127:
            raise ValueError(f'MIDI pitch {pitch} out of range.')
        item = select_sample(self.voice, self.vowel, self.technique, float(pitch))
        data, source_sr = read_sample(item['file'])
        inc = pitch_increment(float(pitch), float(item['root_midi']), source_sr, SR)
        peak = 0.7 * max(1, min(127, velocity)) / 127
        note = LiveNote(data, item['loop_start'], item['loop_end'], inc, peak,
                        pitch=pitch)
        note.bend_factor = self._bend_factor
        if self._portamento_sec > 0.0 and self._last_pitch is not None \
                and self._last_pitch != pitch:
            note.glide_start_ratio = 2 ** ((self._last_pitch - pitch) / 12)
            note.glide_total = max(1, round(self._portamento_sec * SR))
            note.glide_left = note.glide_total
        if self._morph > 0.0:
            self._attach_morph_partner(note)
            note.morph_amount = self._morph
        with self._lock:
            old = self._notes.get(pitch)
            self._notes[pitch] = note
        if old is not None:
            old.release()
        self._last_pitch = pitch

    def note_off(self, pitch):
        with self._lock:
            note = self._notes.get(pitch)
        if note is not None:
            note.release()

    def all_off(self):
        with self._lock:
            notes = list(self._notes.values())
        for note in notes:
            note.release()

    def set_pitch_bend(self, pitch):
        """MIDI pitch-wheel value (-8192..8191); ±2 semitones, like Volta sends."""
        clamped = max(-8192, min(8191, pitch))
        self._bend_semitones = clamped / 8192 * BEND_RANGE_SEMITONES
        self._bend_factor = 2 ** (self._bend_semitones / 12)

    def set_vowel_morph(self, value):
        """CC1: crossfade each active note toward the adjacent vowel's sample."""
        value = max(0, min(127, int(value)))
        self._morph = value / 127
        with self._lock:
            notes = list(self._notes.values())
        for note in notes:
            if self._morph > 0.0:
                self._attach_morph_partner(note)
            else:
                note.morph_note = None
            note.morph_amount = self._morph

    def set_expression(self, value):
        """CC11: master gain scaler, 0..1."""
        self._expression = max(0, min(127, int(value))) / 127

    def set_portamento(self, value):
        """CC5: inter-note glide time, 0..1.5 s."""
        self._portamento_sec = max(0, min(127, int(value))) / 127 * PORTAMENTO_MAX_SEC

    def _attach_morph_partner(self, note):
        """Give a note its adjacent-vowel sample, envelope-synced to the note."""
        if note.pitch is None or note.morph_note is not None:
            return
        vowel = _adjacent_vowel(self.vowel)
        try:
            item = select_sample(self.voice, vowel, self.technique, float(note.pitch))
        except ValueError:
            return  # voice has no adjacent-vowel sample; stay on the main vowel
        data, source_sr = read_sample(item['file'])
        inc = pitch_increment(float(note.pitch), float(item['root_midi']), source_sr, SR)
        partner = LiveNote(data, item['loop_start'], item['loop_end'], inc,
                           note.peak, pitch=note.pitch)
        partner.age = note.age
        partner.bend_factor = note.bend_factor
        partner.glide_start_ratio = note.glide_start_ratio
        partner.glide_total = note.glide_total
        partner.glide_left = note.glide_left
        if note.rel_at is not None:
            partner.rel_at = note.rel_at
            partner.rel_gain = note.rel_gain
        note.morph_note = partner

    def active_pitches(self):
        with self._lock:
            return sorted(self._notes)

    def mix_block(self, n):
        """Render n frames of all active notes. Pure DSP; no audio device needed."""
        with self._lock:
            items = list(self._notes.items())
        if not items:
            return np.zeros(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        done = []
        bend = self._bend_factor
        for pitch, note in items:
            note.bend_factor = bend
            out += note.render(n)
            if note.finished:
                done.append((pitch, note))
        if done:
            with self._lock:
                for pitch, note in done:
                    if self._notes.get(pitch) is note:
                        del self._notes[pitch]
        return np.clip(out * self._expression, -1.0, 1.0)

    def handle_midi(self, msg):
        """Route a mido message to the player.

        MIDI control map (matches what Volta transmits on the choir link):
        notes -> sung samples; pitchwheel -> ±2 semitones bend; CC1 -> vowel
        morph toward the adjacent vowel; CC11 -> expression (gain); CC5 ->
        portamento (inter-note glide time); CC123 -> all notes off.
        """
        if self.channel is not None and getattr(msg, 'channel', 0) != self.channel:
            return
        if msg.type == 'note_on' and msg.velocity > 0:
            self.note_on(msg.note, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            self.note_off(msg.note)
        elif msg.type == 'pitchwheel':
            self.set_pitch_bend(msg.pitch)
        elif msg.type == 'control_change':
            if msg.control == 123:
                self.all_off()
            elif msg.control == 1:
                self.set_vowel_morph(msg.value)
            elif msg.control == 11:
                self.set_expression(msg.value)
            elif msg.control == 5:
                self.set_portamento(msg.value)
