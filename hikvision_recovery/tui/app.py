"""
Hikvision Recovery TUI - Main Application
Professional Terminal User Interface for Hikvision DVR/NVR Management
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, Select, 
    DataTable, Log, ProgressBar, TabbedContent, TabPane,
    Label, Checkbox, RadioSet, RadioButton, RichLog
)
from textual.screen import Screen
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual.events import Mount
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from hikvision_recovery.core.isapi_client import ISAPIClient, ISAPIConfig, ISAPIError
from hikvision_recovery.core.models import (
    DeviceInfo, RecordingInfo, SearchCriteria, RecordingType, StreamType
)
from hikvision_recovery.core.sdk import SDKClient, LoginConfig, SearchConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeviceConnection:
    """Manages device connection state"""
    def __init__(self):
        self.isapi_client: Optional[ISAPIClient] = None
        self.sdk_client: Optional[object] = None
        self.device_info: Optional[DeviceInfo] = None
        self.connected = False
        self.config: Optional[ISAPIConfig] = None


class DevicePanel(Static):
    """Device connection and info panel"""
    
    def compose(self) -> ComposeResult:
        yield Label("Device Connection", classes="panel-title")
        with Vertical(classes="panel-content"):
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Host/IP (e.g., 192.168.1.100)", id="host-input", classes="input-field")
                yield Input(placeholder="Port (default: 80)", id="port-input", classes="input-field-small")
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Username (default: admin)", id="user-input", classes="input-field")
                yield Input(placeholder="Password", id="pass-input", password=True, classes="input-field")
            with Horizontal(classes="button-row"):
                yield Button("Connect ISAPI", id="connect-isapi", variant="primary", classes="connect-btn")
                yield Button("Connect SDK", id="connect-sdk", variant="primary", classes="connect-btn")
                yield Button("Disconnect", id="disconnect-btn", variant="error", classes="connect-btn")
            yield Static("", id="connection-status", classes="status-text")
            yield Static("", id="device-info", classes="info-text")


class SearchPanel(Static):
    """Recording search panel"""
    
    def compose(self) -> ComposeResult:
        yield Label("Recording Search", classes="panel-title")
        with Vertical(classes="panel-content"):
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Channel (0=all)", id="search-channel", classes="input-field-small")
                yield Select(
                    [(t.value, t.value) for t in RecordingType],
                    value=RecordingType.ALL.value,
                    id="search-type",
                    classes="select-field"
                )
                yield Select(
                    [(s.value, s.value) for s in StreamType],
                    value=StreamType.MAIN.value,
                    id="search-stream",
                    classes="select-field"
                )
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Days back (default: 7)", id="search-days", classes="input-field-small")
                yield Input(placeholder="Hours back", id="search-hours", classes="input-field-small")
            with Horizontal(classes="button-row"):
                yield Button("Search", id="search-btn", variant="primary", classes="action-btn")
                yield Button("Search All Pages", id="search-all-btn", variant="primary", classes="action-btn")
            yield DataTable(id="results-table", classes="results-table")


class DownloadPanel(Static):
    """Download management panel"""
    
    def compose(self) -> ComposeResult:
        yield Label("Download Manager", classes="panel-title")
        with Vertical(classes="panel-content"):
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Recording ID", id="download-id", classes="input-field")
                yield Input(placeholder="Save path", id="download-path", value="./downloads", classes="input-field")
            with Horizontal(classes="button-row"):
                yield Button("Download by ID", id="download-id-btn", variant="primary", classes="action-btn")
                yield Button("Download by Time", id="download-time-btn", variant="primary", classes="action-btn")
            yield Static("", id="download-progress", classes="progress-text")
            yield ProgressBar(id="download-bar", total=100, show_eta=True, classes="progress-bar")
            yield RichLog(id="download-log", classes="download-log")


class PTZPanel(Static):
    """PTZ Control panel"""
    
    def compose(self) -> ComposeResult:
        yield Label("PTZ Control", classes="panel-title")
        with Vertical(classes="panel-content"):
            with Horizontal(classes="input-row"):
                yield Input(placeholder="Channel", id="ptz-channel", value="1", classes="input-field-small")
                yield Select(
                    [("5", "Slow"), ("7", "Normal"), ("10", "Fast")],
                    value="7",
                    id="ptz-speed",
                    classes="select-field-small"
                )
            with Horizontal(classes="ptz-controls"):
                yield Button("\u2191", id="ptz-up", variant="default", classes="ptz-btn")
                yield Button("\u2193", id="ptz-down", variant="default", classes="ptz-btn")
            with Horizontal(classes="ptz-controls"):
                yield Button("\u2190", id="ptz-left", variant="default", classes="ptz-btn")
                yield Button("\u2192", id="ptz-right", variant="default", classes="ptz-btn")
            with Horizontal(classes="ptz-controls"):
                yield Button("Zoom +", id="ptz-zoom-in", variant="default", classes="ptz-btn")
                yield Button("Zoom -", id="ptz-zoom-out", variant="default", classes="ptz-btn")
            with Horizontal(classes="button-row"):
                yield Button("Stop", id="ptz-stop", variant="error", classes="action-btn")
            yield Static("", id="ptz-status", classes="status-text")


class LogPanel(Static):
    """Application log panel"""
    
    def compose(self) -> ComposeResult:
        yield Label("Activity Log", classes="panel-title")
        yield RichLog(id="app-log", classes="app-log", highlight=True, markup=True)