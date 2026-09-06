# Hikvision Recovery

Professional ISAPI client for Hikvision DVR/NVR management and recording recovery.

## Features

- **ISAPI Client**: Full-featured client with Digest/Basic auth, automatic retry, session management
- **Recording Search**: Search recordings by time range, camera, type with pagination
- **Download Manager**: Streaming downloads with progress tracking, resume support, concurrent downloads
- **RTSP URLs**: Generate live streaming and playback RTSP URLs
- **PTZ Control**: Pan/tilt/zoom and preset management
- **Device Info**: Fetch device information and capabilities
- **CLI**: Rich command-line interface with progress bars
- **Config**: YAML-based configuration with environment variable support

## Installation

```bash
# From source
git clone https://github.com/your-org/hikvision-recovery
cd hikvision-recovery
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### Configuration

Create a config file:

```bash
hikvision init-config -o config.yaml
# Edit config.yaml with your device credentials
```

Or use environment variables:

```bash
export HIKVISION_HOST="192.168.1.100"
export HIKVISION_USER="admin"
export HIKVISION_PASS="your_password"
```

### CLI Usage

```bash
# Show device info
hikvision info

# Search recordings from last 7 days
hikvision search --days 7

# Search specific camera, motion recordings only
hikvision search --channels 1,2 --type motion --days 3

# Download recordings by ID
hikvision download rec_id_1 rec_id_2 --output ./downloads

# Generate RTSP URL for live streaming
hikvision rtsp --channel 1 --stream main

# Generate playback RTSP URL
hikvision playback --channel 1 --start "2024-01-15 10:00:00" --end "2024-01-15 11:00:00"

# PTZ control
hikvision ptz --channel 1 --command left --speed 5

# Show device capabilities
hikvision capabilities
```

### Python API

```python
from hikvision_recovery import ISAPIClient, ISAPIConfig, SearchCriteria, RecordingType

# Configure
config = ISAPIConfig(
    host="192.168.1.100",
    username="admin",
    password="your_password",
    port=80,
    use_https=False,
)

# Use client
with ISAPIClient(config) as client:
    # Get device info
    device = client.get_device_info()
    print(f"Device: {device.device_name} ({device.model})")
    
    # Search recordings
    criteria = SearchCriteria(
        start_time=datetime(2024, 1, 15, 10, 0, 0),
        end_time=datetime(2024, 1, 15, 12, 0, 0),
        camera_ids=[1, 2],
        recording_types=[RecordingType.MOTION, RecordingType.ALARM],
    )
    
    recordings = list(client.search_all_recordings(criteria))
    for rec in recordings:
        print(f"{rec.start_time} - {rec.end_time}: {rec.duration_human} ({rec.file_size/1024/1024:.1f} MB)")
    
    # Download with progress
    def progress_cb(prog):
        print(f"\r{prog.file_name}: {prog.progress_percent:.1f}% @ {prog.speed_mbps:.1f} MB/s", end="")
    
    client.download_recording(recordings[0], "./downloads/video.mp4", progress_callback=progress_cb)
```

## Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `host` | Device IP/hostname | Required |
| `username` | Username | `admin` |
| `password` | Password | Required |
| `port` | HTTP port | `80` |
| `use_https` | Use HTTPS | `false` |
| `verify_ssl` | Verify SSL cert | `false` |
| `timeout` | Request timeout (s) | `30` |
| `max_retries` | Max retries | `3` |
| `backoff_factor` | Retry backoff | `0.5` |
| `digest_auth` | Use Digest auth | `true` |

## Recording Types

| Type | Description |
|------|-------------|
| `continuous` | 24/7 continuous recording |
| `motion` | Motion detection triggered |
| `alarm` | Alarm input triggered |
| `alarmMotion` | Alarm + motion |
| `smart` | Smart events (line crossing, intrusion, etc.) |
| `pos` | POS/ATM overlay |
| `heatMap` | Heat map data |
| `anr` | Automatic Network Replenishment |
| `all` | All types |

## Stream Types

| Type | Description |
|------|-------------|
| `main` | High quality main stream |
| `sub` | Lower quality sub stream |
| `trans` | Mobile/transcoded stream |

## Project Structure

```
hikvision_recovery/
├── hikvision_recovery/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic data models
│   │   └── isapi_client.py    # Main ISAPI client
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py            # CLI commands
│   ├── utils/
│   │   └── __init__.py        # Helper functions
│   └── config/
│       └── default.yaml       # Default configuration
├── tests/
├── docs/
├── pyproject.toml
├── config.yaml.example
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .

# Type check
mypy .
```

## Roadmap

### Phase 1: ISAPI Client (Current)
- [x] Device info & capabilities
- [x] Recording search with pagination
- [x] Download with progress/resume
- [x] RTSP URL generation
- [x] PTZ control
- [x] CLI interface

### Phase 2: SDK Wrapper
- [ ] HCNetSDK ctypes bindings
- [ ] Advanced playback control
- [ ] Smart search (face, license plate, etc.)
- [ ] Video clipping/export

### Phase 3: Disk Forensics (Deleted Recovery)
- [ ] Raw disk image analysis
- [ ] Hikvision filesystem parser
- [ ] File carving for deleted recordings
- [ ] Timeline reconstruction
- [ ] Export to standard formats

## Legal Notice

⚠️ **Important**: This tool is for authorized use only. Accessing surveillance systems without explicit permission may violate privacy laws and regulations. Always ensure you have proper authorization before using this software on any device.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For issues and feature requests, please open a GitHub issue.