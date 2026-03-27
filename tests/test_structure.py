"""Unit tests for structure helpers."""

import pytest

from atmo_audio_tools.structure import midi_note_name, GM_INSTRUMENTS


class TestMidiNoteName:
    @pytest.mark.parametrize('midi,expected', [
        (0,   'C-1'),
        (12,  'C0'),
        (21,  'A0'),   # lowest piano key
        (60,  'C4'),   # middle C
        (69,  'A4'),   # concert A
        (127, 'G9'),
    ])
    def test_known_notes(self, midi, expected):
        assert midi_note_name(midi) == expected


class TestGmInstruments:
    def test_length(self):
        assert len(GM_INSTRUMENTS) == 128

    def test_first(self):
        assert GM_INSTRUMENTS[0] == 'Acoustic Grand Piano'

    def test_last(self):
        assert GM_INSTRUMENTS[127] == 'Gunshot'
