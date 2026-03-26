# Atmo Audio Toolbox - Web Interface

The Atmo Audio Toolbox project includes a modern web interface that allows users to upload and analyze MIDI and audio files directly through a web browser.

## Features

- 🎼 **Easy File Upload**: Drag-and-drop or click to browse for MIDI files
- 📊 **Comprehensive Analysis**: Key detection, tempo analysis, dynamics, structure analysis, and more
- 🔒 **Privacy-Focused**: Files are analyzed entirely in memory and never stored on disk
- 🎨 **Modern UI**: Clean, responsive design with real-time analysis feedback
- 📋 **Detailed Results**: Full analysis breakdown with JSON export capability

## Installation

First, ensure Flask is installed:

```bash
pip install -r requirements.txt
```

Or install Flask directly:

```bash
pip install Flask
```

## Running the Web Server

Start the web interface using the CLI:

```bash
# Start on default host and port (127.0.0.1:8010)
atmo-audio-toolbox web

# Start on a specific host and port
atmo-audio-toolbox web --host 0.0.0.0 --port 8080

# Enable debug mode for development
atmo-audio-toolbox web --debug
```

Then open your browser and navigate to `http://127.0.0.1:8010` (or your specified host and port).

## Web Interface Usage

1. **Upload a File**: Drag and drop a MIDI file onto the upload box, or click "Choose File" to browse
2. **Analyze**: Click the "Analyze" button to start the analysis
3. **View Results**: The interface displays:
   - **File Information**: Duration, track count, format details
   - **Structure**: Total notes, polyphony, note range, time signatures, instruments
   - **Key & Mode**: Detected key, mode, modal flavor, correlation score, and any key changes
   - **Tempo**: Initial BPM, tempo type, BPM range, and tempo changes if variable
   - **Dynamics**: Overall dynamic level, velocity statistics, and dynamic patterns
   - **Raw JSON**: Complete analysis data for further processing

4. **Export Data**: Copy the raw JSON data to clipboard for use in other applications

## Technical Details

### File Handling

- Files are uploaded via multipart form data
- Files are read into memory as `BytesIO` objects
- No files are written to disk at any point
- Files are automatically garbage collected after analysis completes
- Maximum file size: 16MB

### API Endpoint

**POST** `/api/analyze`

**Request:**
- **Content-Type**: `multipart/form-data`
- **Field name**: `midi_file`
- **File type**: `.mid` or `.midi`

**Response:**
```json
{
  "file": "example.mid",
  "metadata": {
    "format": 1,
    "track_count": 4,
    "ticks_per_beat": 480,
    "duration_seconds": 123.45
  },
  "key": {
    "tonic": "C",
    "mode": "major",
    "correlation": 0.789,
    "modal_flavor": "Major"
  },
  "key_changes": [...],
  "tempo": {...},
  "dynamics": {...},
  "structure": {...}
}
```

**Error Response:**
```json
{
  "error": "Description of the error"
}
```

### Architecture

The web interface is built with:

- **Backend**: Python Flask
- **Frontend**: Vanilla JavaScript (no dependencies)
- **Styling**: CSS with modern design
- **Analysis Engine**: Existing MIDI analysis modules

### Memory Management

The application uses Python's `io.BytesIO` for in-memory file handling:

```python
# Files are read directly into memory
file_data = file.read()
midi_bytes = io.BytesIO(file_data)

# Passed to analyzer
analyzer = MIDIAnalyzer(midi_bytes)
results = analyzer.analyze()

# BytesIO object is automatically garbage collected after analysis
```

## Command-Line Usage (Backward Compatible)

The CLI now supports both analyze and web commands:

```bash
# Analyze a file from the command line
atmo-audio-toolbox analyze file.mid
atmo-audio-toolbox analyze file.mid --json
atmo-audio-toolbox analyze file.mid --window 16

# Start the web server
atmo-audio-toolbox web
atmo-audio-toolbox web --host 0.0.0.0 --port 8080
```

## Troubleshooting

### "Flask is not installed"

Install Flask:
```bash
pip install Flask
```

### File upload fails

- Ensure the file is a valid MIDI file (.mid or .midi extension)
- Check file size is under 16MB
- Verify server is properly running

### Analysis results are incomplete

Some MIDI files may not have all analysis types available (e.g., dynamics may error if no velocity data exists). The interface handles this gracefully and displays N/A for unavailable analyses.

## Browser Compatibility

The web interface works on all modern browsers:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Privacy & Security

- **No data logging**: The application does not log uploaded files or analysis results
- **In-memory only**: Files are only kept in RAM during analysis
- **No persistent storage**: No files are written to the server's disk
- **No external connections**: All analysis is performed locally on the server

## Development

The web interface is organized as follows:

```
midi_analysis/
├── web.py                    # Flask application
├── templates/
│   └── index.html           # HTML interface
└── static/
    ├── style.css            # Styling
    └── app.js               # Client-side logic
```

To contribute or modify:

1. Edit `templates/index.html` for HTML structure changes
2. Edit `static/style.css` for styling changes
3. Edit `static/app.js` for client-side logic changes
4. Edit `web.py` for backend/API changes

## Future Enhancements

Potential future improvements:
- Batch file analysis
- Comparative analysis of multiple files
- MIDI file visualization
- Audio playback preview
- Export analysis as PDF report
- User accounts and analysis history
- REST API for programmatic access
