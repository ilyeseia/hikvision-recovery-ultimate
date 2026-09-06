"""
High-level Hikvision SDK Client.
Wraps the low-level ctypes bindings with Pythonic API.
"""

import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Iterator, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

from .loader import SDKLibraryLoader, create_loader
from .bindings import (
    HCNetSDKBindings,
    NET_DVR_DEVICEINFO_V30,
    NET_DVR_DEVICEINFO_V40,
    NET_DVR_USER_LOGIN_INFO,
    NET_DVR_PREVIEWINFO,
    NET_DVR_FILECOND_V40,
    NET_DVR_FIND_DATA,
    NET_DVR_TIME,
    NET_DVR_TIME_V30,
    NET_DVR_PLAYBACK_POS,
    NET_DVR_PLAYBACKSTATUS,
    NET_DVR_PTZCTRL,
    DeviceInfo,
    TimeInfo,
    FileInfo,
    NET_DVR_STREAM_TYPE,
    NET_DVR_RECORD_TYPE,
    NET_DVR_PLAYBACK_CTRL,
    NET_DVR_PTZ_CMD,
)
from .exceptions import (
    HikvisionSDKError,
    LoginError,
    ConnectionError,
    TimeoutError,
    PlaybackError,
    SearchError,
    DownloadError,
    PTZError,
    raise_for_error,
)

logger = logging.getLogger(__name__)


@dataclass
class LoginConfig:
    """Login configuration."""
    host: str
    port: int = 8000
    username: str = "admin"
    password: str = ""
    use_https: bool = False
    timeout: int = 10
    reconnect: bool = True


@dataclass
class PlaybackConfig:
    """Playback configuration."""
    channel: int
    start_time: datetime
    end_time: datetime
    stream_type: int = NET_DVR_STREAM_TYPE.MAIN
    hWnd: int = 0


@dataclass
class SearchConfig:
    """File search configuration."""
    channel: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    record_types: List[int] = field(default_factory=lambda: [NET_DVR_RECORD_TYPE.ALL])
    file_type: int = 0xFF


class SDKClient:
    """
    High-level Hikvision HCNetSDK client.
    
    Provides Pythonic interface for:
    - Device login/session management
    - Live preview
    - Playback control (time-based, file-based)
    - File search and download
    - PTZ control
    - Device configuration
    """
    
    def __init__(
        self,
        sdk_path: Optional[str] = None,
        auto_reconnect: bool = True,
        reconnect_interval: int = 30,
    ):
        """
        Initialize SDK client.
        
        Args:
            sdk_path: Path to Hikvision SDK installation
            auto_reconnect: Automatically reconnect on connection loss
            reconnect_interval: Seconds between reconnection attempts
        """
        self.sdk_path = sdk_path
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        
        self.loader: Optional[SDKLibraryLoader] = None
        self.bindings: Optional[HCNetSDKBindings] = None
        
        self._user_id: int = -1
        self._device_info: Optional[DeviceInfo] = None
        self._login_config: Optional[LoginConfig] = None
        self._connected = False
        self._lock = threading.RLock()
        self._preview_handles: Dict[int, int] = {}
        self._playback_handles: Dict[int, int] = {}
        
        # Callbacks
        self._exception_callback: Optional[Callable] = None
        self._message_callback: Optional[Callable] = None
        self._alarm_callback: Optional[Callable] = None
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    def initialize(self) -> bool:
        """Initialize SDK and load libraries."""
        with self._lock:
            if self.bindings and self.bindings.lib:
                return True
            
            logger.info("Initializing Hikvision SDK...")
            
            self.loader = create_loader(sdk_path=self.sdk_path)
            self.loader.load_all()
            
            self.bindings = HCNetSDKBindings(self.loader)
            
            if not self.bindings.init():
                raise HikvisionSDKError("Failed to initialize SDK")
            
            # Set default connect time and reconnect
            if self.bindings.NET_DVR_SetConnectTime:
                self.bindings.NET_DVR_SetConnectTime(5000, 3)  # 5s timeout, 3 retries
            
            if self.bindings.NET_DVR_SetReconnect:
                self.bindings.NET_DVR_SetReconnect(10000, True)  # 10s interval
            
            logger.info("SDK initialized successfully")
            return True
    
    def cleanup(self):
        """Cleanup SDK resources."""
        with self._lock:
            # Stop all previews
            for handle in list(self._preview_handles.values()):
                self.stop_preview(handle)
            
            # Stop all playback
            for handle in list(self._playback_handles.values()):
                self.stop_playback(handle)
            
            # Logout
            if self._user_id >= 0:
                self.logout()
            
            # Cleanup SDK
            if self.bindings:
                self.bindings.cleanup()
            
            # Unload libraries
            if self.loader:
                self.loader.unload_all()
            
            self._connected = False
            self._user_id = -1
            self._device_info = None
            logger.info("SDK cleaned up")
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    # =========================================================================
    # Login / Logout
    # =========================================================================
    
    def login(self, config: LoginConfig) -> DeviceInfo:
        """
        Login to device.
        
        Args:
            config: Login configuration
            
        Returns:
            DeviceInfo with device details
        """
        with self._lock:
            if not self.bindings:
                self.initialize()
            
            self._login_config = config
            
            # Prepare login info
            login_info = NET_DVR_USER_LOGIN_INFO()
            login_info.dwSize = ctypes.sizeof(NET_DVR_USER_LOGIN_INFO)
            
            # Host
            host_bytes = config.host.encode('utf-8')
            ctypes.memmove(login_info.sDeviceAddress, host_bytes, min(len(host_bytes), 128))
            
            # Port
            login_info.wPort = config.port
            
            # Credentials
            user_bytes = config.username.encode('utf-8')
            ctypes.memmove(login_info.sUserName, user_bytes, min(len(user_bytes), 63))
            
            pass_bytes = config.password.encode('utf-8')
            ctypes.memmove(login_info.sPassword, pass_bytes, min(len(pass_bytes), 63))
            
            # Login mode
            login_info.byLoginMode = 0  # Normal
            login_info.byUseTransport = 1 if config.use_https else 0
            
            # Device info output
            device_info = NET_DVR_DEVICEINFO_V40()
            device_info.dwSize = ctypes.sizeof(NET_DVR_DEVICEINFO_V40)
            
            # Login
            user_id = self.bindings.NET_DVR_Login_V40(
                ctypes.byref(login_info),
                ctypes.byref(device_info)
            )
            
            if user_id < 0:
                self.bindings.check_error("Login")
                raise LoginError("Login failed", self.bindings.get_last_error())
            
            self._user_id = user_id
            self._device_info = DeviceInfo.from_v40(device_info)
            self._connected = True
            
            logger.info(f"Logged in to {config.host} as {config.username} (UserID: {user_id})")
            logger.info(f"Device: {self._device_info}")
            
            return self._device_info
    
    def logout(self) -> bool:
        """Logout from device."""
        with self._lock:
            if self._user_id < 0:
                return True
            
            if self.bindings.NET_DVR_Logout_V30:
                result = self.bindings.NET_DVR_Logout_V30(self._user_id)
            else:
                result = self.bindings.NET_DVR_Logout(self._user_id)
            
            self._user_id = -1
            self._connected = False
            self._device_info = None
            
            if result:
                logger.info("Logged out successfully")
            return bool(result)
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._user_id >= 0
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def device_info(self) -> Optional[DeviceInfo]:
        return self._device_info
    
    # =========================================================================
    # Preview / Live View
    # =========================================================================
    
    def start_preview(
        self,
        channel: int,
        stream_type: int = NET_DVR_STREAM_TYPE.MAIN,
        hWnd: int = 0,
        callback: Optional[Callable] = None,
        user_data: Any = None,
    ) -> int:
        """
        Start live preview.
        
        Args:
            channel: Channel number (1-based)
            stream_type: Stream type (main/sub/trans)
            hWnd: Window handle for rendering (0 = no window)
            callback: Optional data callback
            user_data: User data passed to callback
            
        Returns:
            Preview handle
        """
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            preview_info = NET_DVR_PREVIEWINFO()
            preview_info.lChannel = channel
            preview_info.dwStreamType = stream_type
            preview_info.dwLinkMode = 0  # TCP
            preview_info.hPlayWnd = hWnd
            preview_info.bBlocked = 1 if callback is None else 0
            preview_info.bPassbackRecord = 0
            preview_info.byProtoType = 0
            
            # Define callback if provided
            cb_func = None
            if callback:
                from .bindings import PREVIEW_CALLBACK
                def wrapped_cb(lRealHandle, dwDataType, pBuffer, dwBufSize, pUser):
                    try:
                        # Convert buffer to bytes
                        data = ctypes.string_at(pBuffer, dwBufSize)
                        callback(lRealHandle, dwDataType, data, user_data)
                    except Exception as e:
                        logger.error(f"Preview callback error: {e}")
                
                cb_func = PREVIEW_CALLBACK(wrapped_cb)
                # Keep reference to prevent garbage collection
                self._preview_callbacks = getattr(self, '_preview_callbacks', {})
                self._preview_callbacks[channel] = cb_func
            
            handle = self.bindings.NET_DVR_RealPlay_V40(
                self._user_id,
                ctypes.byref(preview_info),
                cb_func,
                ctypes.c_void_p(id(user_data)) if user_data else None
            )
            
            if handle < 0:
                self.bindings.check_error("RealPlay")
                raise HikvisionSDKError("Failed to start preview", self.bindings.get_last_error())
            
            self._preview_handles[handle] = channel
            logger.info(f"Started preview on channel {channel} (handle: {handle})")
            return handle
    
    def stop_preview(self, handle: int) -> bool:
        """Stop live preview."""
        with self._lock:
            if self.bindings.NET_DVR_StopRealPlay:
                result = self.bindings.NET_DVR_StopRealPlay(handle)
                self._preview_handles.pop(handle, None)
                return bool(result)
            return False
    
    # =========================================================================
    # Playback
    # =========================================================================
    
    def start_playback_by_time(
        self,
        channel: int,
        start_time: datetime,
        end_time: datetime,
        hWnd: int = 0,
        stream_type: int = NET_DVR_STREAM_TYPE.MAIN,
    ) -> int:
        """
        Start playback by time range.
        
        Args:
            channel: Channel number
            start_time: Start time
            end_time: End time
            hWnd: Window handle
            stream_type: Stream type
            
        Returns:
            Playback handle
        """
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            # Convert times
            start = NET_DVR_TIME()
            start.dwYear = start_time.year
            start.dwMonth = start_time.month
            start.dwDay = start_time.day
            start.dwHour = start_time.hour
            start.dwMinute = start_time.minute
            start.dwSecond = start_time.second
            
            end = NET_DVR_TIME()
            end.dwYear = end_time.year
            end.dwMonth = end_time.month
            end.dwDay = end_time.day
            end.dwHour = end_time.hour
            end.dwMinute = end_time.minute
            end.dwSecond = end_time.second
            
            handle = self.bindings.NET_DVR_PlayBackByTime(
                self._user_id,
                channel,
                ctypes.byref(start),
                ctypes.byref(end),
                hWnd
            )
            
            if handle < 0:
                self.bindings.check_error("PlayBackByTime")
                raise PlaybackError("Failed to start playback", self.bindings.get_last_error())
            
            self._playback_handles[handle] = channel
            logger.info(f"Started playback on channel {channel} (handle: {handle})")
            return handle
    
    def start_playback_by_name(self, channel: int, filename: str, hWnd: int = 0) -> int:
        """Start playback by filename."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            filename_bytes = filename.encode('utf-8')
            handle = self.bindings.NET_DVR_PlayBackByName(
                self._user_id,
                channel,
                filename_bytes,
                hWnd
            )
            
            if handle < 0:
                self.bindings.check_error("PlayBackByName")
                raise PlaybackError("Failed to start playback by name", self.bindings.get_last_error())
            
            self._playback_handles[handle] = channel
            return handle
    
    def control_playback(self, handle: int, command: int, param: Any = None) -> bool:
        """Control playback (play, pause, stop, speed, etc.)."""
        with self._lock:
            if self.bindings.NET_DVR_PlayBackControl:
                if param is not None:
                    param_ptr = ctypes.c_void_p(param)
                else:
                    param_ptr = None
                result = self.bindings.NET_DVR_PlayBackControl(handle, command, param_ptr)
                return bool(result)
            return False
    
    def pause_playback(self, handle: int) -> bool:
        return self.control_playback(handle, NET_DVR_PLAYBACK_CTRL.PAUSE)
    
    def resume_playback(self, handle: int) -> bool:
        return self.control_playback(handle, NET_DVR_PLAYBACK_CTRL.RESTART)
    
    def stop_playback(self, handle: int) -> bool:
        with self._lock:
            if self.bindings.NET_DVR_StopPlayBack:
                result = self.bindings.NET_DVR_StopPlayBack(handle)
                self._playback_handles.pop(handle, None)
                return bool(result)
            return False
    
    def set_playback_speed(self, handle: int, speed: int) -> bool:
        """Set playback speed (1=normal, 2=2x, 4=4x, 8=8x, 16=16x, 0.5=half, etc.)."""
        return self.control_playback(handle, NET_DVR_PLAYBACK_CTRL.SET_SPEED, speed)
    
    def set_playback_position(self, handle: int, position: float) -> bool:
        """Set playback position (0.0 to 1.0)."""
        pos = int(position * 100000)  # SDK uses 0-100000
        return self.control_playback(handle, NET_DVR_PLAYBACK_CTRL.SET_POS, pos)
    
    def get_playback_position(self, handle: int) -> Optional[float]:
        """Get playback position (0.0 to 1.0)."""
        with self._lock:
            pos = NET_DVR_PLAYBACK_POS()
            if self.bindings.NET_DVR_PlayBackGetPos(handle, ctypes.byref(pos)):
                return pos.dwFileOffset / 100000.0
            return None
    
    def get_playback_status(self, handle: int) -> Optional[Dict]:
        """Get playback status."""
        with self._lock:
            status = NET_DVR_PLAYBACKSTATUS()
            if self.bindings.NET_DVR_PlayBackGetStatus(handle, ctypes.byref(status)):
                return {
                    "file_index": status.dwFileIndex,
                    "file_offset": status.dwFileOffset,
                    "frame_num": status.dwFrameNum,
                    "relative_time": status.dwRelativeTime,
                    "absolute_time": status.dwAbsoluteTime,
                    "play_status": status.byPlayStatus,
                }
            return None
    
    def capture_playback_frame(self, handle: int, filepath: str) -> bool:
        """Capture current playback frame to file."""
        with self._lock:
            if self.bindings.NET_DVR_PlayBackCaptureFile:
                filepath_bytes = filepath.encode('utf-8')
                result = self.bindings.NET_DVR_PlayBackCaptureFile(handle, filepath_bytes)
                return bool(result)
            return False
    
    # =========================================================================
    # File Search
    # =========================================================================
    
    def search_files(self, config: SearchConfig) -> List[FileInfo]:
        """
        Search for recording files.
        
        Args:
            config: Search configuration
            
        Returns:
            List of FileInfo objects
        """
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            # Set default times
            if config.start_time is None:
                config.start_time = datetime.now() - timedelta(days=1)
            if config.end_time is None:
                config.end_time = datetime.now()
            
            # Prepare search condition
            cond = NET_DVR_FILECOND_V40()
            cond.dwSize = ctypes.sizeof(NET_DVR_FILECOND_V40)
            cond.byChannel = config.channel
            cond.byFileType = config.file_type
            
            # Time range
            start = config.start_time
            end = config.end_time
            
            cond.struStartTime.dwYear = start.year
            cond.struStartTime.dwMonth = start.month
            cond.struStartTime.dwDay = start.day
            cond.struStartTime.dwHour = start.hour
            cond.struStartTime.dwMinute = start.minute
            cond.struStartTime.dwSecond = start.second
            
            cond.struStopTime.dwYear = end.year
            cond.struStopTime.dwMonth = end.month
            cond.struStopTime.dwDay = end.day
            cond.struStopTime.dwHour = end.hour
            cond.struStopTime.dwMinute = end.minute
            cond.struStopTime.dwSecond = end.second
            
            # Start search
            find_handle = self.bindings.NET_DVR_FindFile_V30(self._user_id, ctypes.byref(cond))
            
            if find_handle < 0:
                self.bindings.check_error("FindFile")
                raise SearchError("Failed to start file search", self.bindings.get_last_error())
            
            try:
                files = []
                find_data = NET_DVR_FIND_DATA()
                
                while True:
                    result = self.bindings.NET_DVR_FindNextFile_V30(find_handle, ctypes.byref(find_data))
                    if not result:
                        break
                    
                    file_info = FileInfo.from_find_data(find_data)
                    files.append(file_info)
                
                return files
                
            finally:
                self.bindings.NET_DVR_FindClose_V30(find_handle)
    
    # =========================================================================
    # Download
    # =========================================================================
    
    def download_by_name(
        self,
        filename: str,
        save_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download file by name."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            filename_bytes = filename.encode('utf-8')
            save_path_bytes = save_path.encode('utf-8')
            
            handle = self.bindings.NET_DVR_GetFileByName(
                self._user_id,
                filename_bytes,
                save_path_bytes
            )
            
            if handle < 0:
                self.bindings.check_error("GetFileByName")
                raise DownloadError("Failed to start download", self.bindings.get_last_error())
            
            try:
                if progress_callback:
                    while True:
                        pos = self.bindings.NET_DVR_GetDownloadPos(handle)
                        if pos >= 100:
                            progress_callback(100, 100)
                            break
                        elif pos < 0:
                            break
                        progress_callback(pos, 100)
                        time.sleep(0.5)
                else:
                    # Wait for completion
                    while True:
                        pos = self.bindings.NET_DVR_GetDownloadPos(handle)
                        if pos >= 100:
                            break
                        elif pos < 0:
                            return False
                        time.sleep(1)
                
                return True
            finally:
                self.bindings.NET_DVR_StopGetFile(handle)
    
    def download_by_time(
        self,
        channel: int,
        start_time: datetime,
        end_time: datetime,
        save_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download file by time range."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            start = NET_DVR_TIME()
            start.dwYear = start_time.year
            start.dwMonth = start_time.month
            start.dwDay = start_time.day
            start.dwHour = start_time.hour
            start.dwMinute = start_time.minute
            start.dwSecond = start_time.second
            
            end = NET_DVR_TIME()
            end.dwYear = end_time.year
            end.dwMonth = end_time.month
            end.dwDay = end_time.day
            end.dwHour = end_time.hour
            end.dwMinute = end_time.minute
            end.dwSecond = end_time.second
            
            save_path_bytes = save_path.encode('utf-8')
            
            handle = self.bindings.NET_DVR_GetFileByTime(
                self._user_id,
                channel,
                ctypes.byref(start),
                ctypes.byref(end),
                save_path_bytes
            )
            
            if handle < 0:
                self.bindings.check_error("GetFileByTime")
                raise DownloadError("Failed to start download", self.bindings.get_last_error())
            
            try:
                if progress_callback:
                    while True:
                        pos = self.bindings.NET_DVR_GetDownloadPos(handle)
                        if pos >= 100:
                            progress_callback(100, 100)
                            break
                        elif pos < 0:
                            break
                        progress_callback(pos, 100)
                        time.sleep(0.5)
                else:
                    while True:
                        pos = self.bindings.NET_DVR_GetDownloadPos(handle)
                        if pos >= 100:
                            break
                        elif pos < 0:
                            return False
                        time.sleep(1)
                
                return True
            finally:
                self.bindings.NET_DVR_StopGetFile(handle)
    
    # =========================================================================
    # PTZ Control
    # =========================================================================
    
    def ptz_control(
        self,
        channel: int,
        command: int,
        speed: int = 5,
        stop: bool = False,
    ) -> bool:
        """
        Control PTZ.
        
        Args:
            channel: Channel number
            command: PTZ command (NET_DVR_PTZ_CMD)
            speed: Speed (1-10)
            stop: True to stop movement
        """
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            if self.bindings.NET_DVR_PTZControlWithSpeed:
                result = self.bindings.NET_DVR_PTZControlWithSpeed(
                    self._user_id,
                    channel,
                    command,
                    0 if stop else 1,
                    speed
                )
            else:
                result = self.bindings.NET_DVR_PTZControl_Other(
                    self._user_id,
                    channel,
                    command,
                    0 if stop else 1
                )
            
            if not result:
                self.bindings.check_error("PTZControl")
                raise PTZError("PTZ control failed", self.bindings.get_last_error())
            
            return bool(result)
    
    def ptz_move(self, channel: int, direction: str, speed: int = 5) -> bool:
        """Move PTZ in direction."""
        directions = {
            "up": NET_DVR_PTZ_CMD.UP,
            "down": NET_DVR_PTZ_CMD.DOWN,
            "left": NET_DVR_PTZ_CMD.LEFT,
            "right": NET_DVR_PTZ_CMD.RIGHT,
            "up_left": NET_DVR_PTZ_CMD.UP_LEFT,
            "up_right": NET_DVR_PTZ_CMD.UP_RIGHT,
            "down_left": NET_DVR_PTZ_CMD.DOWN_LEFT,
            "down_right": NET_DVR_PTZ_CMD.DOWN_RIGHT,
            "zoom_in": NET_DVR_PTZ_CMD.ZOOM_IN,
            "zoom_out": NET_DVR_PTZ_CMD.ZOOM_OUT,
            "focus_near": NET_DVR_PTZ_CMD.FOCUS_NEAR,
            "focus_far": NET_DVR_PTZ_CMD.FOCUS_FAR,
            "iris_open": NET_DVR_PTZ_CMD.IRIS_OPEN,
            "iris_close": NET_DVR_PTZ_CMD.IRIS_CLOSE,
        }
        
        if direction not in directions:
            raise ValueError(f"Unknown direction: {direction}")
        
        return self.ptz_control(channel, directions[direction], speed)
    
    def ptz_stop(self, channel: int, direction: str) -> bool:
        """Stop PTZ movement."""
        directions = {
            "up": NET_DVR_PTZ_CMD.UP,
            "down": NET_DVR_PTZ_CMD.DOWN,
            "left": NET_DVR_PTZ_CMD.LEFT,
            "right": NET_DVR_PTZ_CMD.RIGHT,
            "zoom_in": NET_DVR_PTZ_CMD.ZOOM_IN,
            "zoom_out": NET_DVR_PTZ_CMD.ZOOM_OUT,
        }
        
        if direction not in directions:
            raise ValueError(f"Unknown direction: {direction}")
        
        return self.ptz_control(channel, directions[direction], stop=True)
    
    def ptz_preset(self, channel: int, preset_id: int, action: str = "goto") -> bool:
        """Control PTZ preset."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            actions = {"goto": 39, "set": 37, "clear": 38}
            if action not in actions:
                raise ValueError(f"Unknown preset action: {action}")
            
            if self.bindings.NET_DVR_PTZPreset:
                result = self.bindings.NET_DVR_PTZPreset(
                    self._user_id,
                    channel,
                    actions[action],
                    preset_id
                )
                return bool(result)
            return False
    
    # =========================================================================
    # Device Configuration
    # =========================================================================
    
    def get_config(self, config_type: int, channel: int = -1, out_buffer_size: int = 8192) -> bytes:
        """Get device configuration."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            out_buffer = ctypes.create_string_buffer(out_buffer_size)
            bytes_returned = ctypes.c_ulong(0)
            
            if self.bindings.NET_DVR_GetDVRConfig:
                result = self.bindings.NET_DVR_GetDVRConfig(
                    self._user_id,
                    config_type,
                    channel,
                    out_buffer,
                    out_buffer_size,
                    ctypes.byref(bytes_returned)
                )
                
                if result:
                    return out_buffer.raw[:bytes_returned.value]
            
            self.bindings.check_error("GetDVRConfig")
            raise HikvisionSDKError("Failed to get config", self.bindings.get_last_error())
    
    def set_config(self, config_type: int, channel: int, config_data: bytes) -> bool:
        """Set device configuration."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            in_buffer = ctypes.create_string_buffer(config_data)
            
            if self.bindings.NET_DVR_SetDVRConfig:
                result = self.bindings.NET_DVR_SetDVRConfig(
                    self._user_id,
                    config_type,
                    channel,
                    in_buffer,
                    len(config_data)
                )
                return bool(result)
            
            return False
    
    # =========================================================================
    # Capabilities
    # =========================================================================
    
    def get_capabilities(self, capability_type: int = 0) -> bytes:
        """Get device capabilities."""
        with self._lock:
            if not self.is_connected:
                raise ConnectionError("Not connected")
            
            out_buffer = ctypes.create_string_buffer(65536)
            bytes_returned = ctypes.c_ulong(0)
            
            if self.bindings.NET_DVR_GetDeviceAbility:
                result = self.bindings.NET_DVR_GetDeviceAbility(
                    self._user_id,
                    capability_type,
                    out_buffer,
                    65536,
                    ctypes.byref(bytes_returned)
                )
                
                if result:
                    return out_buffer.raw[:bytes_returned.value]
            
            return b""
    
    # =========================================================================
    # Callbacks
    # =========================================================================
    
    def set_exception_callback(self, callback: Callable[[int, int, int], None]):
        """Set exception callback."""
        from .bindings import EXCEPTION_CALLBACK
        
        def wrapped(dwType, lUserID, lHandle, pUser):
            try:
                callback(dwType, lUserID, lHandle)
            except Exception as e:
                logger.error(f"Exception callback error: {e}")
        
        self._exception_callback = EXCEPTION_CALLBACK(wrapped)
        
        if self.bindings.NET_DVR_SetExceptionCallBack:
            self.bindings.NET_DVR_SetExceptionCallBack(self._exception_callback, None)
    
    def set_message_callback(self, callback: Callable[[int, bytes], bool]):
        """Set message callback."""
        from .bindings import MESSAGE_CALLBACK
        
        def wrapped(lCommand, pBuffer, dwBufLen, pUser):
            try:
                data = ctypes.string_at(pBuffer, dwBufLen)
                return callback(lCommand, data)
            except Exception as e:
                logger.error(f"Message callback error: {e}")
                return False
        
        self._message_callback = MESSAGE_CALLBACK(wrapped)
        
        if self.bindings.NET_DVR_SetMessageCallBack:
            self.bindings.NET_DVR_SetMessageCallBack(self._message_callback, None)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_sdk_version(self) -> str:
        """Get SDK version."""
        if self.bindings.NET_DVR_GetSDKVersion:
            version = self.bindings.NET_DVR_GetSDKVersion()
            major = (version >> 24) & 0xFF
            minor = (version >> 16) & 0xFF
            patch = (version >> 8) & 0xFF
            build = version & 0xFF
            return f"{major}.{minor}.{patch}.{build}"
        return "Unknown"
    
    def get_last_error(self) -> int:
        """Get last error code."""
        return self.bindings.get_last_error() if self.bindings else -1
    
    def get_error_message(self, error_code: int = None) -> str:
        """Get error message for code."""
        from .exceptions import get_error_message
        return get_error_message(error_code or self.get_last_error())


@contextmanager
def sdk_session(
    host: str,
    username: str = "admin",
    password: str = "",
    port: int = 8000,
    sdk_path: Optional[str] = None,
) -> Iterator[SDKClient]:
    """Context manager for SDK session."""
    client = SDKClient(sdk_path=sdk_path)
    try:
        client.initialize()
        client.login(LoginConfig(
            host=host,
            username=username,
            password=password,
            port=port,
        ))
        yield client
    finally:
        client.cleanup()


# =========================================================================
# Async Support (optional)
# =========================================================================

try:
    import asyncio
    
    class AsyncSDKClient:
        """Async wrapper for SDKClient."""
        
        def __init__(self, *args, **kwargs):
            self._client = SDKClient(*args, **kwargs)
            self._executor = None
        
        async def __aenter__(self):
            loop = asyncio.get_event_loop()
            self._executor = loop.run_in_executor(None, self._client.initialize)
            await self._executor
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await asyncio.get_event_loop().run_in_executor(None, self._client.cleanup)
        
        async def login(self, config: LoginConfig) -> DeviceInfo:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._client.login, config)
        
        async def search_files(self, config: SearchConfig) -> List[FileInfo]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._client.search_files, config)
        
        async def download_by_time(
            self,
            channel: int,
            start_time: datetime,
            end_time: datetime,
            save_path: str,
            progress_callback: Optional[Callable] = None,
        ) -> bool:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._client.download_by_time, channel, start_time, end_time, save_path, progress_callback
            )
        
        def __getattr__(self, name):
            return getattr(self._client, name)

except ImportError:
    AsyncSDKClient = None


# =========================================================================
# Factory Functions
# =========================================================================

def create_client(
    sdk_path: Optional[str] = None,
    auto_reconnect: bool = True,
) -> SDKClient:
    """Create SDK client."""
    return SDKClient(sdk_path=sdk_path, auto_reconnect=auto_reconnect)


def create_async_client(
    sdk_path: Optional[str] = None,
    auto_reconnect: bool = True,
) -> Optional["AsyncSDKClient"]:
    """Create async SDK client."""
    if AsyncSDKClient:
        return AsyncSDKClient(sdk_path=sdk_path, auto_reconnect=auto_reconnect)
    return None