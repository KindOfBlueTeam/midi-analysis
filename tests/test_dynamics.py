"""Unit tests for dynamics analysis helpers."""

import pytest

from atmo_audio_tools.dynamics import velocity_to_dynamic, _detect_dynamic_patterns


class TestVelocityToDynamic:
    @pytest.mark.parametrize('velocity,expected', [
        (1,   'ppp'),
        (15,  'ppp'),
        (16,  'pp'),
        (32,  'p'),
        (48,  'mp'),
        (64,  'mf'),
        (80,  'f'),
        (96,  'ff'),
        (112, 'fff'),
        (127, 'fff'),
    ])
    def test_boundaries(self, velocity, expected):
        assert velocity_to_dynamic(velocity) == expected


class TestDetectDynamicPatterns:
    def test_crescendo_detected(self):
        # Rising velocities
        velocities = list(range(20, 100, 2)) * 2
        patterns = _detect_dynamic_patterns(velocities, window=10)
        assert 'crescendo' in patterns

    def test_decrescendo_detected(self):
        velocities = list(range(100, 20, -2)) * 2
        patterns = _detect_dynamic_patterns(velocities, window=10)
        assert 'decrescendo' in patterns

    def test_flat_no_patterns(self):
        velocities = [64] * 100
        patterns = _detect_dynamic_patterns(velocities, window=10)
        assert patterns == []

    def test_short_input_returns_empty(self):
        velocities = [64, 70, 60]
        patterns = _detect_dynamic_patterns(velocities, window=10)
        assert patterns == []
