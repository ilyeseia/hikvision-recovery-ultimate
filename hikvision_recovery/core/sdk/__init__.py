"""
Hikvision HCNetSDK Python Wrapper.

High-level Python bindings for Hikvision HCNetSDK (HCNetSDK.dll/.so).
Provides device management, live preview, playback, file search, download, PTZ control, and more.

Usage:
    from hikvision_recovery.core.sdk import SDKClient, LoginConfig
    
    with SDKClient() as client:
        client.login(LoginConfig(host="192.168.1.100", username="admin", password="***"))
        files = client.search_files(SearchConfig(channel=1, start_time=..., end_time=...))
        client.download_by_time(1, start_time, end_time, "/path/to/save.mp4")
"""

from .loader import (
    SDKLibraryLoader,
    LibraryInfo,
    create_loader,
)

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
    NET_DVR_LOGIN_MODE,
    NET_DVR_DEVICE_TYPE,
    NET_DVR_FILE_TYPE,
    NET_DVR_SEARCH_MODE,
    PREVIEW_CALLBACK,
    PLAYBACK_CALLBACK,
    ALARM_CALLBACK,
    MESSAGE_CALLBACK,
    EXCEPTION_CALLBACK,
)

from .client import (
    SDKClient,
    LoginConfig,
    PlaybackConfig,
    SearchConfig,
    create_client,
    create_async_client,
    sdk_session,
)

from .exceptions import (
    HikvisionSDKError,
    SDKLoadError,
    SDKInitializationError,
    LoginError,
    ConnectionError,
    TimeoutError,
    InvalidParameterError,
    UnsupportedOperationError,
    PlaybackError,
    SearchError,
    DownloadError,
    PTZError,
    CallbackError,
    get_error_message,
    raise_for_error,
    ERROR_CODES,
)

__all__ = [
    # Loader
    "SDKLibraryLoader",
    "LibraryInfo",
    "create_loader",
    
    # Bindings
    "HCNetSDKBindings",
    "NET_DVR_DEVICEINFO_V30",
    "NET_DVR_DEVICEINFO_V40",
    "NET_DVR_USER_LOGIN_INFO",
    "NET_DVR_PREVIEWINFO",
    "NET_DVR_FILECOND_V40",
    "NET_DVR_FIND_DATA",
    "NET_DVR_TIME",
    "NET_DVR_TIME_V30",
    "NET_DVR_PLAYBACK_POS",
    "NET_DVR_PLAYBACKSTATUS",
    "NET_DVR_PTZCTRL",
    "DeviceInfo",
    "TimeInfo",
    "FileInfo",
    "NET_DVR_STREAM_TYPE",
    "NET_DVR_RECORD_TYPE",
    "NET_DVR_PLAYBACK_CTRL",
    "NET_DVR_PTZ_CMD",
    "NET_DVR_LOGIN_MODE",
    "NET_DVR_DEVICE_TYPE",
    "NET_DVR_FILE_TYPE",
    "NET_DVR_SEARCH_MODE",
    "PREVIEW_CALLBACK",
    "PLAYBACK_CALLBACK",
    "ALARM_CALLBACK",
    "MESSAGE_CALLBACK",
    "EXCEPTION_CALLBACK",
    
    # Client
    "SDKClient",
    "LoginConfig",
    "PlaybackConfig",
    "SearchConfig",
    "create_client",
    "create_async_client",
    "sdk_session",
    
    # Exceptions
    "HikvisionSDKError",
    "SDKLoadError",
    "SDKInitializationError",
    "LoginError",
    "ConnectionError",
    "TimeoutError",
    "InvalidParameterError",
    "UnsupportedOperationError",
    "PlaybackError",
    "SearchError",
    "DownloadError",
    "PTZError",
    "CallbackError",
    "get_error_message",
    "raise_for_error",
    "ERROR_CODES",
]

__version__ = "0.2.0"