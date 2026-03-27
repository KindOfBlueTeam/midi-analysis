"""Unit tests for key_detection — no MIDI files required."""

import numpy as np
import pytest

from atmo_audio_tools.key_detection import (
    NOTE_NAMES,
    _detect_modal_flavor,
    _ks_correlate,
)


def _dist(*pitch_classes: int) -> np.ndarray:
    """Build a normalized pitch class distribution from a list of PCs."""
    d = np.zeros(12)
    for pc in pitch_classes:
        d[pc % 12] += 1
    d /= d.sum()
    return d


def _dist_weighted(weights: dict) -> np.ndarray:
    """
    Build a distribution from {pitch_class: count} weights.
    This lets tests mimic real music where the tonic is struck more often,
    which is required for the KS algorithm to distinguish relative keys
    (e.g. C major vs A minor share identical pitch classes).
    """
    d = np.zeros(12)
    for pc, count in weights.items():
        d[pc % 12] += count
    d /= d.sum()
    return d


# ---------------------------------------------------------------------------
# Key detection (KS correlation)
# ---------------------------------------------------------------------------

class TestKsCorrelate:
    def test_c_major(self):
        # Weight C (tonic) and G (dominant) more heavily — as in real music
        dist = _dist_weighted({0: 4, 2: 1, 4: 2, 5: 1, 7: 3, 9: 1, 11: 1})
        tonic, mode, r = _ks_correlate(dist)
        assert tonic == 'C'
        assert mode == 'major'
        assert r > 0.7

    def test_g_major(self):
        # G A B C D E F#  — weight G and D
        dist = _dist_weighted({7: 4, 9: 1, 11: 2, 0: 1, 2: 3, 4: 1, 6: 1})
        tonic, mode, r = _ks_correlate(dist)
        assert tonic == 'G'
        assert mode == 'major'

    def test_a_minor(self):
        # A natural minor: weight A (tonic) and E (dominant) more
        # Without weighting, A minor and C major are indistinguishable by
        # pitch class alone — the KS profiles break the tie via tonic emphasis.
        dist = _dist_weighted({9: 4, 11: 1, 0: 2, 2: 1, 4: 3, 5: 1, 7: 1})
        tonic, mode, r = _ks_correlate(dist)
        assert tonic == 'A'
        assert mode == 'minor'

    def test_d_minor(self):
        # D E F G A Bb C — weight D and A
        dist = _dist_weighted({2: 4, 4: 1, 5: 2, 7: 1, 9: 3, 10: 1, 0: 1})
        tonic, mode, r = _ks_correlate(dist)
        assert tonic == 'D'
        assert mode == 'minor'

    def test_returns_float_correlation(self):
        dist = _dist(0, 2, 4, 5, 7, 9, 11)
        _, _, r = _ks_correlate(dist)
        assert isinstance(r, float)
        assert -1.0 <= r <= 1.0


# ---------------------------------------------------------------------------
# Modal flavor detection
# ---------------------------------------------------------------------------

class TestDetectModalFlavor:
    def test_c_ionian(self):
        dist = _dist(0, 2, 4, 5, 7, 9, 11)
        assert _detect_modal_flavor(dist, 0) == 'ionian'

    def test_d_dorian(self):
        # D E F G A B C  (raised 6th vs natural minor)
        dist = _dist(2, 4, 5, 7, 9, 11, 0)
        assert _detect_modal_flavor(dist, 2) == 'dorian'

    def test_e_phrygian(self):
        # E F G A B C D
        dist = _dist(4, 5, 7, 9, 11, 0, 2)
        assert _detect_modal_flavor(dist, 4) == 'phrygian'

    def test_f_lydian(self):
        # F G A B C D E  (raised 4th)
        dist = _dist(5, 7, 9, 11, 0, 2, 4)
        assert _detect_modal_flavor(dist, 5) == 'lydian'

    def test_g_mixolydian(self):
        # G A B C D E F  (lowered 7th)
        dist = _dist(7, 9, 11, 0, 2, 4, 5)
        assert _detect_modal_flavor(dist, 7) == 'mixolydian'

    def test_a_aeolian(self):
        dist = _dist(9, 11, 0, 2, 4, 5, 7)
        assert _detect_modal_flavor(dist, 9) == 'aeolian'

    def test_b_locrian(self):
        # B C D E F G A
        dist = _dist(11, 0, 2, 4, 5, 7, 9)
        assert _detect_modal_flavor(dist, 11) == 'locrian'
