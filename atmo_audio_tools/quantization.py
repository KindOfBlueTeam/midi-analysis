"""Timing quantization analysis — how tightly notes align to the beat grid."""
from __future__ import annotations

import numpy as np
import mido

# Analyse against a 16th-note grid (4 subdivisions per beat)
_GRID_SUBDIVISIONS = 4


def analyze_quantization(midi_file: mido.MidiFile) -> dict:
    """
    Measure how closely note onsets align to the 16th-note grid.

    Returns
    -------
    quantization_score : int
        0% = clearly human (notes freely placed)
        100% = clearly software (all notes snapped to grid)
    mean_offset_fraction : float
        Average distance from nearest grid line, as a fraction of one
        grid unit (0.0 = on the grid, 0.5 = halfway between grid lines).
    std_offset_fraction : float
        Standard deviation of the same offset measure.
    on_grid_percentage : float
        Percentage of notes within 5 % of a grid line.
    grid_size_ticks : float
        Size of one 16th-note grid unit in ticks.
    note_count : int
        Number of note-on events analysed.
    """
    ticks_per_beat = midi_file.ticks_per_beat or 480
    grid_size = ticks_per_beat / _GRID_SUBDIVISIONS  # ticks per 16th note

    offsets: list[float] = []

    for track in midi_file.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                raw = abs_tick % grid_size
                # Fold to [0, 0.5]: distance to the *nearest* grid line
                normalized = min(raw, grid_size - raw) / grid_size
                offsets.append(normalized)

    if not offsets:
        return {'error': 'No note events found'}

    arr = np.array(offsets)
    mean_offset = float(np.mean(arr))
    std_offset = float(np.std(arr))

    # Notes within 5 % of a grid line are considered "on the grid"
    on_grid_pct = float(np.mean(arr < 0.05)) * 100

    # Scale: mean_offset 0.0 → score 100 (perfect grid / software)
    #        mean_offset 0.5 → score 0   (random / human)
    score = round((1.0 - mean_offset * 2) * 100)
    score = max(0, min(100, score))

    return {
        'quantization_score': score,
        'mean_offset_fraction': round(mean_offset, 4),
        'std_offset_fraction': round(std_offset, 4),
        'on_grid_percentage': round(on_grid_pct, 1),
        'grid_size_ticks': round(grid_size, 1),
        'note_count': len(offsets),
    }
