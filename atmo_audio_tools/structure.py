"""Structural analysis: instruments, note range, time signatures, polyphony."""
from __future__ import annotations

import mido

# General MIDI program → instrument name (programs 0–127)
GM_INSTRUMENTS: list[str] = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano",
    "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord",
    "Clavi", "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba",
    "Xylophone", "Tubular Bells", "Dulcimer", "Drawbar Organ", "Percussive Organ",
    "Rock Organ", "Church Organ", "Reed Organ", "Accordion", "Harmonica",
    "Tango Accordion", "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)", "Electric Guitar (clean)", "Electric Guitar (muted)",
    "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics",
    "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)",
    "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2",
    "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings",
    "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "Synth Strings 1", "Synth Strings 2",
    "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn",
    "Brass Section", "Synth Brass 1", "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax",
    "Oboe", "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown Bottle",
    "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)", "Lead 4 (chiff)",
    "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass+lead)",
    "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)",
    "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)",
    "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)",
    "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bag pipe",
    "Fiddle", "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum",
    "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet",
    "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]

_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# MIDI standard: channel 9 (0-indexed) is reserved for percussion
PERCUSSION_CHANNEL = 9


def midi_note_name(note: int) -> str:
    """Convert a MIDI note number (0–127) to scientific pitch notation."""
    octave = (note // 12) - 1
    return f'{_NOTE_NAMES[note % 12]}{octave}'


def analyze_structure(midi_file: mido.MidiFile) -> dict:
    """
    Extract structural metadata from MIDI events:

    - instruments: channel → program number and GM name
    - note_range: lowest and highest pitch seen across all tracks
    - time_signatures: all time-signature change events
    - total_notes: total note-on event count
    - max_polyphony: maximum simultaneous notes observed
    """
    # channel → {'program': int, 'note_count': int}
    channels: dict[int, dict] = {}
    all_pitches: list[int] = []
    time_sig_events: list[dict] = []

    # For polyphony: track active notes per tick
    # We'll use a simpler approach: count simultaneous note-ons
    active_notes: dict[tuple[int, int], int] = {}  # (channel, note) → start_tick
    polyphony_samples: list[int] = []

    for track in midi_file.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time

            if msg.type == 'program_change':
                ch = msg.channel
                if ch not in channels:
                    channels[ch] = {'program': msg.program, 'note_count': 0}
                else:
                    channels[ch]['program'] = msg.program

            elif msg.type == 'note_on' and msg.velocity > 0:
                ch = msg.channel
                if ch not in channels:
                    channels[ch] = {'program': 0, 'note_count': 0}
                channels[ch]['note_count'] += 1
                all_pitches.append(msg.note)
                active_notes[(ch, msg.note)] = abs_tick
                polyphony_samples.append(len(active_notes))

            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                active_notes.pop((msg.channel, msg.note), None)

            elif msg.type == 'time_signature':
                time_sig_events.append({
                    'tick': abs_tick,
                    'numerator': msg.numerator,
                    'denominator': msg.denominator,
                    'display': f'{msg.numerator}/{msg.denominator}',
                })

    # Build instrument list
    instruments: list[dict] = []
    for ch, data in sorted(channels.items()):
        if ch == PERCUSSION_CHANNEL:
            name = 'Percussion (GM channel 10)'
        else:
            prog = data.get('program', 0)
            name = GM_INSTRUMENTS[prog] if prog < len(GM_INSTRUMENTS) else f'Program {prog}'
        instruments.append({
            'channel': ch,
            'program': data.get('program', 0),
            'name': name,
            'note_count': data.get('note_count', 0),
        })

    note_range: dict = {}
    if all_pitches:
        lo, hi = min(all_pitches), max(all_pitches)
        note_range = {
            'lowest': midi_note_name(lo),
            'highest': midi_note_name(hi),
            'lowest_midi': lo,
            'highest_midi': hi,
            'span_semitones': hi - lo,
        }

    if not time_sig_events:
        time_sig_events = [{'tick': 0, 'numerator': 4, 'denominator': 4, 'display': '4/4'}]

    return {
        'instruments': instruments,
        'note_range': note_range,
        'time_signatures': time_sig_events,
        'total_notes': len(all_pitches),
        'max_polyphony': max(polyphony_samples) if polyphony_samples else 0,
    }
