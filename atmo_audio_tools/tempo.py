"""Tempo extraction and analysis from MIDI tempo events."""

import mido

_DEFAULT_TEMPO_US = 500_000  # 120 BPM


def _ticks_to_seconds(ticks: int, tempo_us: int, ticks_per_beat: int) -> float:
    return (ticks / ticks_per_beat) * (tempo_us / 1_000_000)


def analyze_tempo(midi_file: mido.MidiFile) -> dict:
    """
    Extract all tempo events and return summary statistics.

    MIDI stores tempo as microseconds-per-beat (set_tempo messages).
    If no tempo message is present, the MIDI default of 120 BPM applies.
    """
    tpb = midi_file.ticks_per_beat
    raw_events: list[dict] = []

    for track in midi_file.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'set_tempo':
                raw_events.append({'tick': abs_tick, 'tempo_us': msg.tempo})

    if not raw_events:
        raw_events = [{'tick': 0, 'tempo_us': _DEFAULT_TEMPO_US}]

    raw_events.sort(key=lambda e: e['tick'])

    # Deduplicate: remove consecutive identical tempos
    deduped: list[dict] = [raw_events[0]]
    for ev in raw_events[1:]:
        if ev['tempo_us'] != deduped[-1]['tempo_us']:
            deduped.append(ev)

    # Compute elapsed wall-clock time for each event
    elapsed = 0.0
    current_tempo = _DEFAULT_TEMPO_US
    prev_tick = 0
    events: list[dict] = []

    for ev in deduped:
        elapsed += _ticks_to_seconds(ev['tick'] - prev_tick, current_tempo, tpb)
        bpm = round(mido.tempo2bpm(ev['tempo_us']), 2)
        events.append({
            'tick': ev['tick'],
            'time_seconds': round(elapsed, 3),
            'tempo_us': ev['tempo_us'],
            'bpm': bpm,
        })
        current_tempo = ev['tempo_us']
        prev_tick = ev['tick']

    bpms = [e['bpm'] for e in events]

    return {
        'initial_bpm': events[0]['bpm'],
        'is_constant': len(events) == 1,
        'min_bpm': round(min(bpms), 2),
        'max_bpm': round(max(bpms), 2),
        'avg_bpm': round(sum(bpms) / len(bpms), 2),
        # Only populated when there are actual changes
        'tempo_changes': events[1:] if len(events) > 1 else [],
    }
