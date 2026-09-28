"""Live choir link CLI. Run `python live.py --help` for usage.

Wires a MIDI input port to LivePlayer and streams the mixed audio to the
default output device. Missing optional dependencies produce a plain-language
error telling you exactly what to install.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cantabile.live import (  # noqa: E402
    LivePlayer, resolve_port, resolve_voice, resolve_vowel, voices, SR,
)


def list_ports():
    try:
        import mido
    except ImportError:
        return None, 'mido is not installed. Run: pip install mido python-rtmidi'
    try:
        return mido.get_input_names(), None
    except Exception as e:
        return None, (
            f'Could not list MIDI ports ({e}). '
            'Install a working MIDI backend: pip install python-rtmidi'
        )


def list_voices():
    rows = []
    for vid, v in sorted(voices().items()):
        rows.append(f'  {vid:10s} {v["name"]} ({v["role"]}, {v["gender"]})')
    return '\n'.join(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Sing the Cantabile recorded vocal bank live from a MIDI port '
                    '(the Volta end of the live link).')
    ap.add_argument('--voice', default='vs-f1',
                    help='Recorded singer id (see --list-voices). Default: vs-f1')
    ap.add_argument('--vowel', default='ah',
                    help='Vowel to sing: a, e, i, o, u (ah/eh/ee/oh/oo also work). Default: ah')
    ap.add_argument('--technique', default=None,
                    help='Bank technique; defaults to straight when available.')
    ap.add_argument('--midi-port', default=None,
                    help='MIDI input port name (exact or substring). Default: first available.')
    ap.add_argument('--channel', type=int, default=None,
                    help='Only respond to this MIDI channel (0-15). Default: all channels.')
    ap.add_argument('--list-ports', action='store_true', help='List MIDI input ports and exit.')
    ap.add_argument('--list-voices', action='store_true', help='List recorded voices and exit.')
    args = ap.parse_args(argv)

    if args.list_voices:
        print(list_voices())
        return 0
    if args.list_ports:
        names, err = list_ports()
        if err:
            print(err, file=sys.stderr)
            return 1
        print('\n'.join(names) if names else 'No MIDI input ports found.')
        return 0

    try:
        player = LivePlayer(args.voice, vowel=args.vowel,
                            technique=args.technique, channel=args.channel)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1
    except FileNotFoundError:
        print('Error: the recorded vocal bank is not unpacked. '
              'Run python prepare_bank.py in tools/cantabile first.', file=sys.stderr)
        return 1

    names, err = list_ports()
    if err:
        print(f'Error: {err}', file=sys.stderr)
        return 1
    if not names:
        print('Error: no MIDI input ports found. On Windows, create a virtual port '
              '(for example with loopMIDI) and select it as Volta\'s MIDI output.',
              file=sys.stderr)
        return 1
    try:
        port_name = resolve_port(args.midi_port, names) if args.midi_port else names[0]
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1

    try:
        import sounddevice as sd
    except ImportError:
        print('Error: the sounddevice package is not installed. '
              'Run: pip install sounddevice', file=sys.stderr)
        return 1
    import mido

    print(f'Live choir: {player.voice["name"]} singing "{player.vowel}" '
          f'from MIDI port "{port_name}". Ctrl+C to stop.')

    def callback(outdata, frames, time_info, status):
        outdata[:, 0] = player.mix_block(frames)

    try:
        port = mido.open_input(port_name)
    except Exception as e:
        print(f'Error: could not open MIDI port {port_name!r} ({e}). '
              'If the port disappeared, run python live.py --list-ports.', file=sys.stderr)
        return 1

    try:
        with sd.OutputStream(samplerate=SR, channels=1, dtype='float32',
                             blocksize=256, callback=callback):
            with port:
                while True:
                    for msg in port.iter_pending():
                        player.handle_midi(msg)
                    time.sleep(0.002)
    except KeyboardInterrupt:
        print('\nStopped.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
