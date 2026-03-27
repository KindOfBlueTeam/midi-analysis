"""Key and mode detection using the Krumhansl-Schmuckler algorithm."""
from __future__ import annotations

import numpy as np
import mido

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Krumhansl-Kessler pitch class profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Scale intervals (semitones from root) for all 7 diatonic modes
_MODE_INTERVALS: dict[str, list[int]] = {
    'ionian':     [0, 2, 4, 5, 7, 9, 11],  # major
    'dorian':     [0, 2, 3, 5, 7, 9, 10],
    'phrygian':   [0, 1, 3, 5, 7, 8, 10],
    'lydian':     [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'aeolian':    [0, 2, 3, 5, 7, 8, 10],  # natural minor
    'locrian':    [0, 1, 3, 5, 6, 8, 10],
}


def _collect_pitch_classes(midi_file: mido.MidiFile) -> np.ndarray:
    """Build a normalized pitch class distribution weighted by note count."""
    distribution = np.zeros(12)
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                distribution[msg.note % 12] += 1
    total = distribution.sum()
    if total > 0:
        distribution /= total
    return distribution


def _ks_correlate(distribution: np.ndarray) -> tuple[str, str, float]:
    """
    Krumhansl-Schmuckler key-finding: correlate pitch class distribution
    against all 24 major/minor key profiles and return the best match.
    """
    best_r = -np.inf
    best_tonic = 'C'
    best_mode = 'major'

    for i in range(12):
        for profile, mode_name in [(_MAJOR_PROFILE, 'major'), (_MINOR_PROFILE, 'minor')]:
            rotated = np.roll(profile, i)
            r = float(np.corrcoef(distribution, rotated)[0, 1])
            if r > best_r:
                best_r = r
                best_tonic = NOTE_NAMES[i]
                best_mode = mode_name

    return best_tonic, best_mode, best_r


def _detect_modal_flavor(distribution: np.ndarray, tonic_pc: int) -> str:
    """
    Given a tonic pitch class, determine which of the 7 diatonic modes
    best matches the pitch class usage by dot-product scoring.
    """
    rotated = np.roll(distribution, -tonic_pc)
    best_mode = 'ionian'
    best_score = -np.inf

    for mode_name, intervals in _MODE_INTERVALS.items():
        profile = np.zeros(12)
        for i in intervals:
            profile[i] = 1.0
        score = float(np.dot(rotated, profile))
        if score > best_score:
            best_score = score
            best_mode = mode_name

    return best_mode


def detect_key(midi_file: mido.MidiFile) -> dict:
    """Detect the overall musical key, major/minor mode, and modal flavor."""
    dist = _collect_pitch_classes(midi_file)
    tonic, mode, correlation = _ks_correlate(dist)
    tonic_pc = NOTE_NAMES.index(tonic)
    modal_flavor = _detect_modal_flavor(dist, tonic_pc)

    return {
        'tonic': tonic,
        'mode': mode,
        'modal_flavor': modal_flavor,
        'correlation': round(correlation, 4),
    }


def detect_key_changes(
    midi_file: mido.MidiFile,
    window_measures: int = 8,
    beats_per_measure: int = 4,
) -> list[dict]:
    """
    Detect key changes by applying the KS algorithm over sliding, non-overlapping
    windows of ``window_measures`` measures.

    Returns a list of key-change events, each containing the estimated measure
    number, tonic, mode, and correlation coefficient.  Only entries where the
    detected key differs from the previous window are included, so the first
    entry always reflects the opening key.
    """
    tpb = midi_file.ticks_per_beat
    window_ticks = window_measures * beats_per_measure * tpb

    # Collect (absolute_tick, pitch_class) for every note-on event
    notes: list[tuple[int, int]] = []
    for track in midi_file.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                notes.append((abs_tick, msg.note % 12))

    if not notes:
        return []

    notes.sort()
    max_tick = notes[-1][0]

    if max_tick < window_ticks * 2:
        return []

    changes: list[dict] = []
    prev_key_str: str | None = None
    window_num = 0
    tick = 0

    while tick + window_ticks <= max_tick:
        window_pcs = [pc for (t, pc) in notes if tick <= t < tick + window_ticks]
        tick += window_ticks
        window_num += 1

        if not window_pcs:
            continue

        dist = np.zeros(12)
        for pc in window_pcs:
            dist[pc] += 1
        dist /= dist.sum()

        tonic, mode, correlation = _ks_correlate(dist)
        key_str = f'{tonic} {mode}'

        if key_str != prev_key_str:
            measure_num = (window_num - 1) * window_measures + 1
            changes.append({
                'measure': measure_num,
                'key': tonic,
                'mode': mode,
                'correlation': round(correlation, 4),
            })
            prev_key_str = key_str

    return changes
