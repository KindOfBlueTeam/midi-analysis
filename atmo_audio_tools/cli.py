"""Command-line interface for atmo-audio-tools."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .analyzer import MIDIAnalyzer


# ---------------------------------------------------------------------------
# Human-readable report formatting
# ---------------------------------------------------------------------------

def _fmt(results: dict) -> str:
    lines: list[str] = []
    sep = '─' * 50

    lines.append(f'\n  MIDI Analysis: {results["file"]}')
    lines.append(sep)

    # Metadata
    meta = results['metadata']
    m, s = divmod(int(meta['duration_seconds']), 60)
    lines.append(f'  Duration      {m}m {s}s  ({meta["duration_seconds"]}s)')
    lines.append(f'  Tracks        {meta["track_count"]}')
    lines.append(f'  Format        Type {meta["format"]}')
    lines.append(f'  Ticks/beat    {meta["ticks_per_beat"]}')

    # Structure
    struct = results['structure']
    lines.append('')
    lines.append(f'  Total notes   {struct["total_notes"]}')
    lines.append(f'  Max polyphony {struct["max_polyphony"]} simultaneous notes')

    if struct.get('note_range'):
        nr = struct['note_range']
        lines.append(f'  Note range    {nr["lowest"]} – {nr["highest"]}  ({nr["span_semitones"]} semitones)')

    ts_list = struct.get('time_signatures', [])
    if ts_list:
        if len(ts_list) == 1:
            lines.append(f'  Time sig      {ts_list[0]["display"]}')
        else:
            lines.append(f'  Time sigs     ' + ', '.join(
                f'{e["display"]} @ m.{_tick_label(e["tick"])}' for e in ts_list
            ))

    if struct.get('instruments'):
        lines.append('')
        lines.append('  Instruments:')
        for inst in struct['instruments']:
            lines.append(f'    ch {inst["channel"]:2d}  {inst["name"]:30s}  ({inst["note_count"]} notes)')

    # Key
    key = results['key']
    lines.append('')
    lines.append(sep)
    lines.append(f'  Key           {key["tonic"]} {key["mode"]}  (r = {key["correlation"]})')
    lines.append(f'  Modal flavor  {key["modal_flavor"]}')

    key_changes = results['key_changes']
    if len(key_changes) > 1:
        lines.append(f'  Key changes   {len(key_changes) - 1} detected:')
        for ch in key_changes[1:]:
            lines.append(f'    m.{ch["measure"]:>4}  →  {ch["key"]} {ch["mode"]}  (r = {ch["correlation"]})')
    else:
        lines.append('  Key changes   None detected')

    # Tempo
    tempo = results['tempo']
    lines.append('')
    lines.append(sep)
    if tempo['is_constant']:
        lines.append(f'  Tempo         {tempo["initial_bpm"]} BPM  (constant)')
    else:
        lines.append(f'  Tempo         {tempo["initial_bpm"]} BPM  (initial)')
        lines.append(f'  Range         {tempo["min_bpm"]} – {tempo["max_bpm"]} BPM')
        lines.append(f'  Changes       {len(tempo["tempo_changes"])}:')
        for tc in tempo['tempo_changes']:
            lines.append(f'    {tc["time_seconds"]:>8.2f}s  →  {tc["bpm"]} BPM')

    # Dynamics
    dyn = results['dynamics']
    lines.append('')
    lines.append(sep)
    if 'error' in dyn:
        lines.append(f'  Dynamics      {dyn["error"]}')
    else:
        lines.append(f'  Dynamics      {dyn["overall_dynamic"]}  (avg velocity {dyn["average_velocity"]})')
        lines.append(f'  Vel. range    {dyn["min_velocity"]} – {dyn["max_velocity"]}  (σ = {dyn["std_deviation"]})')
        if dyn['level_distribution']:
            dist_str = '  '.join(f'{k}:{v}' for k, v in dyn['level_distribution'].items())
            lines.append(f'  Distribution  {dist_str}')
        if dyn['patterns']:
            lines.append(f'  Patterns      {", ".join(dyn["patterns"])}')

    lines.append(sep)
    lines.append('')
    return '\n'.join(lines)


def _tick_label(tick: int) -> str:
    return str(tick) if tick else '0'


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

@click.group()
def main():
    """Analyze MIDI files for key, mode, tempo, dynamics, and more."""
    pass


@main.command('analyze')
@click.argument('midi_file', type=click.Path(exists=True, path_type=Path))
@click.option('--json', 'output_json', is_flag=True, help='Output raw JSON instead of formatted report.')
@click.option(
    '--window', default=8, show_default=True,
    help='Window size in measures for key-change detection.',
)
def analyze_cmd(midi_file: Path, output_json: bool, window: int) -> None:
    """Analyze MIDI_FILE for key, mode, tempo, dynamics, and more."""
    try:
        analyzer = MIDIAnalyzer(midi_file)
        results = analyzer.analyze(key_change_window=window)
    except Exception as exc:
        click.echo(f'Error: {exc}', err=True)
        sys.exit(1)

    if output_json:
        click.echo(json.dumps(results, indent=2))
    else:
        click.echo(_fmt(results))


@main.command('web')
@click.option('--host', default='127.0.0.1', show_default=True, help='Host to bind to.')
@click.option('--port', default=8010, show_default=True, type=int, help='Port to listen on.')
@click.option('--debug', is_flag=True, help='Enable debug mode.')
def web_cmd(host: str, port: int, debug: bool) -> None:
    """Start the web interface for MIDI analysis."""
    try:
        from .web import run
        click.echo(f'Starting MIDI Analysis Studio at http://{host}:{port}')
        run(host=host, port=port, debug=debug)
    except ImportError:
        click.echo('Error: Flask is required for the web interface. Install it with: pip install Flask', err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
