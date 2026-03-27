"""
Lightweight MIDI parser that extracts only note events, ignoring all metadata.
Designed to handle corrupt MIDI files (e.g., from Suno) by skipping problematic meta events.
"""

import io
from pathlib import Path
from typing import NamedTuple, Union, List, Tuple


class NoteEvent(NamedTuple):
    """Represents a MIDI note event."""
    time: int  # Absolute time in ticks
    note: int  # MIDI note number (0-127)
    velocity: int  # Note velocity (0-127)
    is_note_on: bool  # True for note on, False for note off


def read_variable_length(data: bytes, pos: int) -> Tuple[int, int]:
    """
    Read a variable-length quantity from MIDI data.
    Returns (value, new_position).
    """
    value = 0
    while True:
        if pos >= len(data):
            raise ValueError("Unexpected end of MIDI data while reading variable-length quantity")
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            break
    return value, pos


def extract_note_events(midi_file_path: Union[str, Path]) -> List[NoteEvent]:
    """
    Extract only note on/off events from a MIDI file, ignoring all metadata.
    Works with corrupt MIDI files by skipping unparseable meta events.
    
    Parameters
    ----------
    midi_file_path : str | Path
        Path to the MIDI file.
    
    Returns
    -------
    list[NoteEvent]
        List of note events sorted by time.
    """
    with open(midi_file_path, 'rb') as f:
        data = f.read()
    
    pos = 0
    
    if len(data) < 14:
        raise ValueError("MIDI file too short (missing header)")
    
    # Parse header
    if data[pos:pos+4] != b'MThd':
        raise ValueError("Not a valid MIDI file (missing MThd header)")
    pos += 4
    
    # Header size
    if pos + 4 > len(data):
        raise ValueError("MIDI file truncated (header size not readable)")
    header_size = int.from_bytes(data[pos:pos+4], 'big')
    pos += 4
    
    if pos + header_size > len(data):
        raise ValueError("MIDI file truncated (header data not readable)")
    
    # Read format, tracks, and division from within the header chunk
    header_pos = 8  # After MThd (4 bytes) and size (4 bytes)
    if len(data) < header_pos + 6:
        raise ValueError("MIDI file truncated (missing format/tracks/division)")
    num_tracks = int.from_bytes(data[header_pos+2:header_pos+4], 'big')

    # Move past the header chunk to the first track
    pos = 8 + header_size
    
    all_events: List[NoteEvent] = []
    
    # Parse each track
    for _ in range(num_tracks):
        if pos + 8 > len(data):
            # Not enough data for track header
            break
        
        if data[pos:pos+4] != b'MTrk':
            # Corrupted track header, try to skip
            pos += 4
        else:
            pos += 4
        
        if pos + 4 > len(data):
            break
        
        # Track size
        track_size = int.from_bytes(data[pos:pos+4], 'big')
        pos += 4
        track_end = min(pos + track_size, len(data))
        
        current_time = 0
        running_status = 0
        
        # Parse track events
        while pos < track_end:
            if pos >= len(data):
                break
            
            # Read delta time
            try:
                delta_time, pos = read_variable_length(data, pos)
            except (IndexError, ValueError):
                break
            current_time += delta_time
            
            if pos >= track_end or pos >= len(data):
                break
            
            status = data[pos]
            
            # Handle meta events (0xFF) - skip them entirely
            if status == 0xFF:
                pos += 1
                if pos >= track_end or pos >= len(data):
                    break
                meta_type = data[pos]
                pos += 1
                # Read meta event length
                try:
                    meta_length, pos = read_variable_length(data, pos)
                except (IndexError, ValueError):
                    break
                # Skip the meta event data
                pos = min(pos + meta_length, len(data))
                continue
            
            # Handle sysex events (0xF0, 0xF7) - skip them
            if status in (0xF0, 0xF7):
                pos += 1
                if pos >= track_end or pos >= len(data):
                    break
                try:
                    sysex_length, pos = read_variable_length(data, pos)
                except (IndexError, ValueError):
                    break
                pos = min(pos + sysex_length, len(data))
                continue
            
            # Handle system events (0xF1-0xF6, 0xF8-0xFF)
            if status >= 0xF0:
                pos += 1
                continue
            
            # Handle channel messages
            if status & 0x80:
                running_status = status
                pos += 1
            else:
                status = running_status
            
            if pos >= track_end or pos >= len(data):
                break
            
            status_nibble = status & 0xF0
            
            # Note Off (0x80)
            if status_nibble == 0x80:
                if pos + 1 < len(data):
                    note = data[pos]
                    velocity = data[pos + 1]
                    pos += 2
                    all_events.append(NoteEvent(current_time, note, velocity, False))
            
            # Note On (0x90)
            elif status_nibble == 0x90:
                if pos + 1 < len(data):
                    note = data[pos]
                    velocity = data[pos + 1]
                    pos += 2
                    # Note on with velocity 0 is treated as note off
                    all_events.append(NoteEvent(current_time, note, velocity, velocity > 0))
            
            # Control Change (0xB0) - skip
            elif status_nibble == 0xB0:
                if pos + 1 < len(data):
                    pos += 2
            
            # Program Change (0xC0) - skip
            elif status_nibble == 0xC0:
                if pos < len(data):
                    pos += 1
            
            # Channel Pressure (0xD0) - skip
            elif status_nibble == 0xD0:
                if pos < len(data):
                    pos += 1
            
            # Pitch Bend (0xE0) - skip
            elif status_nibble == 0xE0:
                if pos + 1 < len(data):
                    pos += 2
            
            # Unknown - try to skip safely
            else:
                if pos < len(data):
                    pos += 1
    
    # Sort by time and return
    return sorted(all_events, key=lambda e: (e.time, not e.is_note_on, e.note))
