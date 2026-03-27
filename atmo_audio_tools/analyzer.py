"""Main orchestrator: runs all analysis modules and assembles the report."""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import mido

from .dynamics import analyze_dynamics
from .key_detection import detect_key, detect_key_changes
from .quantization import analyze_quantization
from .structure import analyze_structure
from .tempo import analyze_tempo
from .midi_parser import extract_note_events

# Key changes must meet this correlation threshold to be shown as a modulation
_MODULATION_CONFIDENCE = 0.82


def _build_modulation_path(key_changes: list[dict]) -> str | None:
    """
    Return an arrow-joined modulation path (e.g. "C → F#m → Bb") using only
    high-confidence changes.  Lowercase 'm' suffix for minor keys.
    Returns None when no confident modulations are found.
    Up to 5 transitions after the starting key are included.
    """
    if not key_changes:
        return None

    def _fmt(change: dict) -> str:
        suffix = 'm' if change['mode'] == 'minor' else ''
        return f"{change['key']}{suffix}"

    # First entry is always the opening key regardless of confidence
    segments = [_fmt(key_changes[0])]

    for change in key_changes[1:]:
        if change['correlation'] >= _MODULATION_CONFIDENCE:
            label = _fmt(change)
            if label != segments[-1]:   # skip consecutive duplicates
                segments.append(label)
        if len(segments) >= 6:          # 1 start + 5 transitions
            break

    return ' → '.join(segments) if len(segments) > 1 else None


def _build_midi_from_note_events(note_events: list) -> mido.MidiFile:
    """
    Reconstruct a basic mido.MidiFile from extracted note events.
    This creates a minimal MIDI structure that's compatible with analysis functions.
    """
    midi = mido.MidiFile()
    track = mido.MidiTrack()
    midi.tracks.append(track)
    
    # Default division (ticks per beat)
    midi.ticks_per_beat = 480
    
    prev_time = 0
    for note_event in note_events:
        # Calculate delta time
        delta = note_event.time - prev_time
        prev_time = note_event.time
        
        # Create note on or note off message
        if note_event.is_note_on:
            msg = mido.Message('note_on', note=note_event.note, velocity=note_event.velocity, time=delta)
        else:
            msg = mido.Message('note_off', note=note_event.note, velocity=note_event.velocity, time=delta)
        
        track.append(msg)
    
    return midi


class MIDIAnalyzer:
    """
    Load a MIDI file and run the full suite of analyses.

    Usage::

        analyzer = MIDIAnalyzer("song.mid")
        report = analyzer.analyze()

    Can also load from BytesIO (in-memory file)::

        import io
        with open("song.mid", "rb") as f:
            midi_bytes = io.BytesIO(f.read())
        analyzer = MIDIAnalyzer(midi_bytes)
        report = analyzer.analyze()
    """

    def __init__(self, path: str | Path | io.BytesIO) -> None:
        self._temp_path = None
        
        if isinstance(path, io.BytesIO):
            # In-memory file - save to temp location for parsing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
                tmp.write(path.read())
                self._temp_path = tmp.name
            self.path = Path(path.name if hasattr(path, 'name') else 'unknown.mid')
            path = self._temp_path
        else:
            self.path = Path(path)
            if not self.path.exists():
                raise FileNotFoundError(f'MIDI file not found: {self.path}')
        
        # Try to load with custom parser (handles corrupt metadata)
        try:
            note_events = extract_note_events(path)
            self._midi = _build_midi_from_note_events(note_events)
        except Exception as custom_error:
            # Fallback to mido for pristine files
            try:
                self._midi = mido.MidiFile(str(path))
            except Exception as mido_error:
                # If both fail, raise the original custom parser error
                raise ValueError(f"Could not load MIDI file: {custom_error}") from custom_error

    def __del__(self):
        """Clean up temp file if created."""
        if self._temp_path:
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass

    def analyze(self, key_change_window: int = 8) -> dict:
        """
        Run all analyses and return a single report dictionary.

        Parameters
        ----------
        key_change_window:
            Number of measures per window used when scanning for key changes.
        """
        # Try to detect key, but gracefully handle any errors
        try:
            key_result = detect_key(self._midi)
            key_changes_result = detect_key_changes(self._midi, window_measures=key_change_window)
        except Exception as e:
            # Catch any error during key detection
            key_result = {
                'tonic': 'N/A',
                'mode': 'N/A',
                'modal_flavor': 'N/A',
                'correlation': 0.0,
                'error': 'Key detection failed, but analysis continues'
            }
            key_changes_result = []

        tempo_result = analyze_tempo(self._midi)

        modulation_path = _build_modulation_path(key_changes_result)
        if modulation_path:
            key_result['modulation_path'] = modulation_path

        return {
            'file': self.path.name,
            'metadata': self._metadata(tempo_result),
            'key': key_result,
            'key_changes': key_changes_result,
            'tempo': tempo_result,
            'dynamics': analyze_dynamics(self._midi),
            'quantization': analyze_quantization(self._midi),
            'structure': analyze_structure(self._midi),
        }

    def _metadata(self, tempo_info: dict) -> dict:
        tpb = self._midi.ticks_per_beat
        # Total duration in ticks is the length of the longest track
        total_ticks = max(
            (sum(msg.time for msg in track) for track in self._midi.tracks),
            default=0,
        )

        # Estimate wall-clock duration using average tempo
        avg_tempo_us = 60_000_000 / tempo_info['avg_bpm']
        duration_seconds = (total_ticks / tpb) * (avg_tempo_us / 1_000_000)

        return {
            'format': self._midi.type,
            'track_count': len(self._midi.tracks),
            'ticks_per_beat': tpb,
            'duration_seconds': round(duration_seconds, 2),
        }
