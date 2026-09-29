import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cantabile.live import (
    LiveNote, LivePlayer, _adjacent_vowel, pitch_increment, resolve_port,
    resolve_voice, resolve_vowel, select_sample, SR,
)
from cantabile.bank import read_sample, voices


def sine_note(freq=440.0, seconds=1.0, sr=SR):
    t = np.arange(round(seconds * sr)) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


class VowelTests(unittest.TestCase):
    def test_canonical_spellings(self):
        self.assertEqual(resolve_vowel('ah'), 'a')
        self.assertEqual(resolve_vowel('EE'), 'i')
        self.assertEqual(resolve_vowel('oh'), 'o')
        self.assertEqual(resolve_vowel('u'), 'u')

    def test_invalid_vowel(self):
        with self.assertRaises(ValueError):
            resolve_vowel('xyz')


class VoiceResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not voices():
            raise unittest.SkipTest('Recorded vocal bank manifest not unpacked.')

    def test_known_recorded_voice(self):
        vid = sorted(voices())[0]
        voice, technique = resolve_voice(vid)
        self.assertEqual(voice['id'], vid)
        self.assertIn(technique, voice['techniques'])

    def test_unknown_voice_lists_recorded(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_voice('hanami')
        self.assertIn('Recorded voices', str(ctx.exception))

    def test_select_sample_nearest_root(self):
        vid = sorted(voices())[0]
        voice, technique = resolve_voice(vid)
        item = select_sample(voice, 'a', technique, 60.0)
        pool = [s for s in voice['samples']
                if s['technique'] == technique and s['vowel'] == 'a']
        best = min(pool, key=lambda s: abs(s['root_midi'] - 60.0))
        self.assertEqual(item['file'], best['file'])

    def test_select_sample_missing_vowel(self):
        vid = sorted(voices())[0]
        voice, technique = resolve_voice(vid)
        with self.assertRaises(ValueError):
            select_sample(voice, 'zzz-nope', technique, 60.0)


class PitchMathTests(unittest.TestCase):
    def test_octave_doubles_rate(self):
        self.assertAlmostEqual(pitch_increment(72, 60), 2.0)

    def test_unison_is_one(self):
        self.assertAlmostEqual(pitch_increment(60, 60.0), 1.0)

    def test_fractional_root(self):
        # Same formula as bank.synthesize: 2**((pitch-root)/12) * src/out.
        self.assertAlmostEqual(pitch_increment(69, 68.5), 2 ** (0.5 / 12))


class PortResolutionTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(resolve_port('Volta Choir', ['Volta Choir', 'Other']), 'Volta Choir')

    def test_substring_match(self):
        self.assertEqual(resolve_port('volta', ['loopMIDI Volta Choir Port']), 'loopMIDI Volta Choir Port')

    def test_missing_raises_with_available(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_port('nope', ['A', 'B'])
        self.assertIn('A', str(ctx.exception))


class LiveNoteTests(unittest.TestCase):
    def make_note(self, freq=440.0, peak=0.7):
        data = sine_note(freq, seconds=0.5)
        a, b = 1000, 9000
        return LiveNote(data, a, b, increment=1.0, peak=peak), data, a, b

    def test_attack_ramps_from_zero(self):
        note, _, _, _ = self.make_note()
        out = note.render(64)
        # First frame is silence (attack starts at 0), envelope rises after.
        self.assertEqual(out[0], 0.0)
        self.assertGreater(np.max(np.abs(out)), 0.0)

    def test_sustain_reaches_peak(self):
        note, data, _, _ = self.make_note(peak=0.5)
        note.render(SR)  # past the attack
        out = note.render(256)
        self.assertLessEqual(np.max(np.abs(out)), 0.5 + 1e-6)
        self.assertGreater(np.max(np.abs(out)), 0.4)

    def test_release_fades_and_finishes(self):
        note, _, _, _ = self.make_note()
        note.render(SR // 2)
        note.release()
        tail = note.render(SR)  # well past the 90ms release
        self.assertTrue(note.finished)
        self.assertAlmostEqual(tail[-1], 0.0, places=5)

    def test_positions_stay_in_loop(self):
        note, _, a, b = self.make_note()
        # Render enough frames to lap the loop several times at 1x.
        note.render(SR * 2)
        self.assertGreaterEqual(note.pos, a)
        self.assertLess(note.pos, b + note.increment)

    def test_pitch_shift_changes_period(self):
        # 2x increment halves the sine period in the output.
        data = sine_note(220.0, seconds=0.25)
        fast = LiveNote(data, 100, 5000, increment=2.0, peak=1.0)
        fast.render(SR)  # skip attack
        out = fast.render(441)
        # Zero crossings over 10ms at 440Hz effective -> ~8-9 crossings.
        crossings = np.sum(np.diff(np.sign(out)) != 0)
        self.assertGreater(crossings, 5)


class LivePlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not voices():
            raise unittest.SkipTest('Recorded vocal bank manifest not unpacked.')
        # The manifest can exist without the sample WAVs (as in this sandbox);
        # these tests need real audio data, not just the manifest.
        vid = sorted(voices())[0]
        voice, technique = resolve_voice(vid)
        try:
            read_sample(voice['samples'][0]['file'])
        except Exception:
            raise unittest.SkipTest('Recorded vocal bank samples not unpacked.')

    def setUp(self):
        vid = sorted(voices())[0]
        self.player = LivePlayer(vid, vowel='ah')

    def msg(self, type, note=60, velocity=100, channel=0, control=0):
        return SimpleNamespace(type=type, note=note, velocity=velocity,
                               channel=channel, control=control)

    def test_note_on_off_tracking(self):
        self.player.handle_midi(self.msg('note_on', note=60, velocity=100))
        self.assertEqual(self.player.active_pitches(), [60])
        self.player.handle_midi(self.msg('note_off', note=60))
        # Note lingers through its release, then drops out of the mix.
        self.player.mix_block(SR)
        self.assertEqual(self.player.active_pitches(), [])

    def test_velocity_zero_note_on_is_note_off(self):
        self.player.handle_midi(self.msg('note_on', note=62, velocity=0))
        self.assertEqual(self.player.active_pitches(), [])

    def test_polyphony(self):
        for n in (60, 64, 67):
            self.player.handle_midi(self.msg('note_on', note=n))
        self.assertEqual(self.player.active_pitches(), [60, 64, 67])
        out = self.player.mix_block(512)
        self.assertGreater(np.max(np.abs(out)), 0.01)

    def test_silence_when_idle(self):
        out = self.player.mix_block(512)
        np.testing.assert_array_equal(out, np.zeros(512, dtype=np.float32))

    def test_output_clips_not_wraps(self):
        for n in range(60, 72):
            self.player.handle_midi(self.msg('note_on', note=n, velocity=127))
        self.player.mix_block(SR)  # settle envelopes
        out = self.player.mix_block(512)
        self.assertLessEqual(np.max(np.abs(out)), 1.0)

    def test_channel_filter(self):
        p = LivePlayer(sorted(voices())[0], channel=5)
        p.handle_midi(self.msg('note_on', note=60, channel=0))
        self.assertEqual(p.active_pitches(), [])
        p.handle_midi(self.msg('note_on', note=60, channel=5))
        self.assertEqual(p.active_pitches(), [60])

    def test_all_notes_off_cc(self):
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.handle_midi(self.msg('control_change', control=123))
        self.player.mix_block(SR)
        self.assertEqual(self.player.active_pitches(), [])

    def test_all_notes_off_releases_chord(self):
        # Regression: mix_block used to drop only the last finished note,
        # leaving the rest of a released chord droning.
        for n in (60, 64, 67):
            self.player.handle_midi(self.msg('note_on', note=n))
        self.player.handle_midi(self.msg('control_change', control=123))
        self.player.mix_block(SR)
        self.assertEqual(self.player.active_pitches(), [])

    def test_retrigger_releases_old_voice(self):
        self.player.handle_midi(self.msg('note_on', note=60))
        first = self.player._notes[60]
        self.player.handle_midi(self.msg('note_on', note=60))
        self.assertIsNot(self.player._notes[60], first)
        self.assertIsNotNone(first.rel_at)


class ExpressiveControlTests(unittest.TestCase):
    """Pitch bend, vowel morph (CC1), expression (CC11), portamento (CC5)."""

    @classmethod
    def setUpClass(cls):
        if not voices():
            raise unittest.SkipTest('Recorded vocal bank manifest not unpacked.')
        # The manifest can exist without the sample WAVs (as in this sandbox);
        # these tests need real audio data, not just the manifest.
        vid = sorted(voices())[0]
        voice, technique = resolve_voice(vid)
        try:
            read_sample(voice['samples'][0]['file'])
        except Exception:
            raise unittest.SkipTest('Recorded vocal bank samples not unpacked.')

    def setUp(self):
        vid = sorted(voices())[0]
        self.player = LivePlayer(vid, vowel='ah')

    def msg(self, type, **kw):
        d = dict(note=60, velocity=100, channel=0, control=0, value=0, pitch=0)
        d.update(kw)
        return SimpleNamespace(type=type, **d)

    def two_vowel_voice(self):
        for vid in sorted(voices()):
            voice, technique = resolve_voice(vid)
            have = {s['vowel'] for s in voice['samples']
                    if s['technique'] == technique}
            if 'a' in have and 'e' in have:
                return vid
        raise unittest.SkipTest('No recorded voice sings both a and e.')

    def test_adjacent_vowel_order(self):
        self.assertEqual(_adjacent_vowel('a'), 'e')
        self.assertEqual(_adjacent_vowel('u'), 'a')  # wraps around

    def test_pitch_bend_up_factor(self):
        self.player.handle_midi(self.msg('note_on'))
        self.player.handle_midi(self.msg('pitchwheel', pitch=8191))
        self.player.mix_block(64)  # audio thread propagates bend to notes
        note = self.player._notes[60]
        self.assertAlmostEqual(note.bend_factor, 2 ** (2 / 12), places=3)

    def test_pitch_bend_down_factor(self):
        self.player.handle_midi(self.msg('pitchwheel', pitch=-8192))
        self.assertAlmostEqual(self.player._bend_factor, 2 ** (-2 / 12), places=4)

    def test_pitch_bend_center_is_unity(self):
        self.player.handle_midi(self.msg('pitchwheel', pitch=0))
        self.assertAlmostEqual(self.player._bend_factor, 1.0, places=6)

    def test_bend_sharpens_synthetic_note(self):
        data = sine_note(220.0, seconds=0.25)
        plain = LiveNote(data, 100, 5000, increment=1.0, peak=1.0)
        bent = LiveNote(data, 100, 5000, increment=1.0, peak=1.0)
        bent.bend_factor = 2.0
        plain.render(SR)
        bent.render(SR)  # skip attack
        crossings = lambda o: np.sum(np.diff(np.sign(o)) != 0)
        out_plain = plain.render(4410)
        out_bent = bent.render(4410)
        self.assertGreater(crossings(out_bent), crossings(out_plain) * 1.8)

    def test_cc1_attaches_morph_partner(self):
        player = LivePlayer(self.two_vowel_voice(), vowel='ah')
        player.handle_midi(self.msg('note_on', note=60))
        player.handle_midi(self.msg('control_change', control=1, value=127))
        note = player._notes[60]
        self.assertIsNotNone(note.morph_note)
        self.assertAlmostEqual(note.morph_amount, 1.0)
        self.assertEqual(note.morph_note.age, note.age)  # envelope-synced
        out = player.mix_block(512)
        self.assertGreater(np.max(np.abs(out)), 0.01)

    def test_cc1_zero_drops_partner(self):
        player = LivePlayer(self.two_vowel_voice(), vowel='ah')
        player.handle_midi(self.msg('note_on', note=60))
        player.handle_midi(self.msg('control_change', control=1, value=127))
        player.handle_midi(self.msg('control_change', control=1, value=0))
        note = player._notes[60]
        self.assertIsNone(note.morph_note)
        self.assertEqual(note.morph_amount, 0.0)

    def test_morph_blends_two_timbres(self):
        d1 = sine_note(220.0, seconds=0.5)
        d2 = sine_note(330.0, seconds=0.5)
        note = LiveNote(d1, 100, 9000, increment=1.0, peak=1.0)
        note.morph_note = LiveNote(d2, 100, 9000, increment=1.0, peak=1.0)
        note.morph_amount = 0.5
        note.render(SR)  # settle the primary envelope
        out = note.render(4410)
        solo = LiveNote(d1, 100, 9000, increment=1.0, peak=1.0)
        solo.render(SR)
        out_solo = solo.render(4410)
        self.assertFalse(np.allclose(out, out_solo))
        self.assertGreater(np.max(np.abs(out)), 0.1)

    def test_release_propagates_to_partner(self):
        player = LivePlayer(self.two_vowel_voice(), vowel='ah')
        player.handle_midi(self.msg('note_on', note=60))
        player.handle_midi(self.msg('control_change', control=1, value=127))
        note = player._notes[60]
        player.handle_midi(self.msg('note_off', note=60))
        self.assertIsNotNone(note.morph_note.rel_at)

    def test_cc11_zero_silences_output(self):
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.mix_block(SR)  # settle
        self.player.handle_midi(self.msg('control_change', control=11, value=0))
        out = self.player.mix_block(512)
        np.testing.assert_array_equal(out, np.zeros(512, dtype=np.float32))

    def test_cc11_full_restores_output(self):
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.mix_block(SR)
        self.player.handle_midi(self.msg('control_change', control=11, value=0))
        self.player.handle_midi(self.msg('control_change', control=11, value=127))
        out = self.player.mix_block(512)
        self.assertGreater(np.max(np.abs(out)), 0.01)

    def test_cc5_sets_glide_time(self):
        self.player.handle_midi(self.msg('control_change', control=5, value=127))
        self.assertAlmostEqual(self.player._portamento_sec, 1.5)

    def test_portamento_glides_from_last_pitch(self):
        self.player.handle_midi(self.msg('control_change', control=5, value=127))
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.handle_midi(self.msg('note_on', note=64))
        note = self.player._notes[64]
        self.assertGreater(note.glide_left, 0)
        self.assertAlmostEqual(note.glide_start_ratio, 2 ** ((60 - 64) / 12))
        for _ in range(400):  # render past the 1.5 s glide
            self.player.mix_block(256)
        self.assertEqual(note.glide_left, 0)
        out = self.player.mix_block(256)
        self.assertGreater(np.max(np.abs(out)), 0.001)

    def test_no_portamento_by_default(self):
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.handle_midi(self.msg('note_on', note=64))
        self.assertEqual(self.player._notes[64].glide_left, 0)

    def test_same_pitch_retrigger_does_not_glide(self):
        self.player.handle_midi(self.msg('control_change', control=5, value=127))
        self.player.handle_midi(self.msg('note_on', note=60))
        self.player.handle_midi(self.msg('note_on', note=60))
        self.assertEqual(self.player._notes[60].glide_left, 0)

    def test_expressive_controls_respect_channel(self):
        player = LivePlayer(sorted(voices())[0], channel=5)
        player.handle_midi(self.msg('pitchwheel', pitch=8191, channel=0))
        self.assertAlmostEqual(player._bend_factor, 1.0)
        player.handle_midi(self.msg('pitchwheel', pitch=8191, channel=5))
        self.assertGreater(player._bend_factor, 1.0)


if __name__ == '__main__':
    unittest.main()
