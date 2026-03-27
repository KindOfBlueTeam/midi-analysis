"""Dynamics analysis derived from MIDI note velocity values."""
from __future__ import annotations

import numpy as np
import mido

# Standard dynamic markings with their MIDI velocity ranges
DYNAMIC_LEVELS: list[tuple[str, int, int]] = [
    ('ppp', 1,   15),
    ('pp',  16,  31),
    ('p',   32,  47),
    ('mp',  48,  63),
    ('mf',  64,  79),
    ('f',   80,  95),
    ('ff',  96,  111),
    ('fff', 112, 127),
]


def velocity_to_dynamic(velocity: int) -> str:
    for name, low, high in DYNAMIC_LEVELS:
        if low <= velocity <= high:
            return name
    return 'mf'


def _calculate_humanness_score(velocities: list[int]) -> int:
    """
    Calculate a score from 0-100 indicating how 'human' the velocities appear.
    
    0% = Clearly Human (high velocity variation, natural inconsistency)
    100% = Clearly Software (all notes same velocity or negligible variation)
    
    Uses multiple indicators:
    - Standard deviation of velocities
    - Unique velocity values
    - Coefficient of variation
    """
    if len(velocities) < 2:
        return 100  # Single note could be anything, assume software
    
    v = np.array(velocities, dtype=float)
    std_dev = float(np.std(v))
    mean_vel = float(np.mean(v))
    
    # Indicator 1: Standard deviation (0 = all same = software)
    # Perfect max std dev for values 0-127 is about 36.8
    # We'll use a more realistic max of 30 for practical MIDI
    max_realistic_std = 30.0
    std_score = min(std_dev / max_realistic_std, 1.0)
    
    # Indicator 2: Unique velocities (1 unique = software, many = human)
    unique_velocities = len(set(velocities))
    unique_score = min(unique_velocities / 32.0, 1.0)  # 32+ unique values = likely human
    
    # Indicator 3: Coefficient of variation (how much variance relative to mean)
    cv = std_dev / mean_vel if mean_vel > 0 else 0
    max_cv = 0.5  # Realistic max for human playing
    cv_score = min(cv / max_cv, 1.0)
    
    # Combine indicators (higher = more human)
    human_score = (std_score * 0.4 + unique_score * 0.3 + cv_score * 0.3)
    
    # Convert to percentage: 0% = human, 100% = software
    software_likelihood = (1.0 - human_score) * 100
    return round(software_likelihood)


def analyze_dynamics(midi_file: mido.MidiFile) -> dict:
    """
    Analyse note velocities across all tracks and return:
    - overall dynamic marking and average velocity
    - velocity range and standard deviation
    - per-level distribution (how many notes fall in each dynamic band)
    - detected crescendo / decrescendo patterns
    - humanness score (0% = human, 100% = software)
    """
    velocities: list[int] = []
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                velocities.append(msg.velocity)

    if not velocities:
        return {'error': 'No note events found'}

    v = np.array(velocities, dtype=float)
    avg_vel = float(np.mean(v))

    level_distribution: dict[str, int] = {}
    for name, low, high in DYNAMIC_LEVELS:
        count = int(np.sum((v >= low) & (v <= high)))
        if count > 0:
            level_distribution[name] = count

    humanness = _calculate_humanness_score(velocities)

    return {
        'overall_dynamic': velocity_to_dynamic(round(avg_vel)),
        'average_velocity': round(avg_vel, 1),
        'min_velocity': int(v.min()),
        'max_velocity': int(v.max()),
        'dynamic_range': int(v.max()) - int(v.min()),
        'std_deviation': round(float(np.std(v)), 2),
        'humanness_score': humanness,
        'level_distribution': level_distribution,
        'patterns': _detect_dynamic_patterns(velocities),
    }


def _detect_dynamic_patterns(velocities: list[int], window: int = 20) -> list[str]:
    """
    Identify broad crescendo and decrescendo gestures by computing the linear
    regression slope over rolling windows of note velocities.
    """
    if len(velocities) < window * 2:
        return []

    v = np.array(velocities, dtype=float)
    step = max(window // 2, 1)
    x = np.arange(window, dtype=float)

    patterns: list[str] = []
    in_cresc = False
    in_decresc = False
    threshold = 0.5  # velocity units per note

    for i in range(0, len(v) - window, step):
        chunk = v[i:i + window]
        slope = float(np.polyfit(x, chunk, 1)[0])

        if slope > threshold and not in_cresc:
            patterns.append('crescendo')
            in_cresc = True
            in_decresc = False
        elif slope < -threshold and not in_decresc:
            patterns.append('decrescendo')
            in_decresc = True
            in_cresc = False
        elif abs(slope) <= threshold:
            in_cresc = False
            in_decresc = False

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for p in patterns:
        if p not in seen:
            result.append(p)
            seen.add(p)
    return result
