"""
ctypes bindings for Hikvision HCNetSDK.
Based on HCNetSDK.h - core structures and function definitions.
"""

import ctypes
import ctypes.util
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import IntEnum

from .loader import SDKLibraryLoader
from .exceptions import HikvisionSDKError, raise_for_error


# =============================================================================
# Basic Types
# =============================================================================

# Standard types
LONG = ctypes.c_long
DWORD = ctypes.c_ulong
WORD = ctypes.c_ushort
BYTE = ctypes.c_ubyte
BOOL = ctypes.c_int
CHAR = ctypes.c_char
LPSTR = ctypes.c_char_p
LPVOID = ctypes.c_void_p
HANDLE = ctypes.c_void_p

# SDK-specific types
NET_DVR_HANDLE = LONG
NET_DVR_USER_ID = LONG
NET_DVR_PLAY_HANDLE = LONG
NET_DVR_FIND_HANDLE = LONG
NET_DVR_DOWNLOAD_HANDLE = LONG
NET_DVR_PREVIEW_HANDLE = LONG


# =============================================================================
# Enums (from HCNetSDK.h)
# =============================================================================

class NET_DVR_DEVICE_TYPE(IntEnum):
    """Device types"""
    DVR = 1
    NVR = 2
    IPC = 3
    DVS = 4
    NVR_9000 = 5
    NVR_8000 = 6
    NVR_7000 = 7
    NVR_5000 = 8
    NVR_4000 = 9
    NVR_3000 = 10
    NVR_2000 = 11
    NVR_1000 = 12


class NET_DVR_LOGIN_MODE(IntEnum):
    """Login modes"""
    NORMAL = 0
    CLOUD = 1
    P2P = 2
    HI_DDNS = 3


class NET_DVR_STREAM_TYPE(IntEnum):
    """Stream types"""
    MAIN = 0
    SUB = 1
    TRANS = 2
    THREE = 3


class NET_DVR_RECORD_TYPE(IntEnum):
    """Recording types"""
    ALL = 0xFF
    SCHEDULE = 1
    MOTION = 2
    ALARM = 3
    MOTION_ALARM = 4
    SMART = 5
    POS = 6
    HEAT_MAP = 7
    ANR = 8


class NET_DVR_FILE_TYPE(IntEnum):
    """File types for search"""
    ALL = 0xFF
    VIDEO = 1
    PICTURE = 2


class NET_DVR_PLAYBACK_CTRL(IntEnum):
    """Playback control commands"""
    PLAY = 1
    PAUSE = 2
    STOP = 3
    RESTART = 4
    FAST = 5
    SLOW = 6
    NORMAL = 7
    FRAME = 8
    GET_TIME = 9
    SET_TIME = 10
    GET_SPEED = 11
    SET_SPEED = 12
    GET_POS = 13
    SET_POS = 14
    GET_DURATION = 15
    GET_FRAME_RATE = 16
    SET_FRAME_RATE = 17


class NET_DVR_PTZ_CMD(IntEnum):
    """PTZ control commands"""
    UP = 21
    DOWN = 22
    LEFT = 23
    RIGHT = 24
    UP_LEFT = 25
    UP_RIGHT = 26
    DOWN_LEFT = 27
    DOWN_RIGHT = 28
    PAN_AUTO = 29
    ZOOM_IN = 31
    ZOOM_OUT = 32
    FOCUS_NEAR = 33
    FOCUS_FAR = 34
    IRIS_OPEN = 35
    IRIS_CLOSE = 36
    PRESET_SET = 37
    PRESET_CLEAR = 38
    PRESET_GOTO = 39
    CRUISE_SET = 40
    CRUISE_RUN = 41
    CRUISE_STOP = 42
    TRACK_SET = 43
    TRACK_RUN = 44
    TRACK_STOP = 45
    GOTO_PRESET = 46


class NET_DVR_SEARCH_MODE(IntEnum):
    """Search modes"""
    NORMAL = 0
    TIME = 1
    EVENT = 2
    SMART = 3
    POS = 4
    FACE = 5
    PLATE = 6


# =============================================================================
# Structures
# =============================================================================

class NET_DVR_DEVICEINFO_V30(ctypes.Structure):
    """Device info structure (returned on login)"""
    _fields_ = [
        ("byChanNum", BYTE),           # Number of analog channels
        ("byStartChan", BYTE),         # Start channel number
        ("byIPChanNum", BYTE),         # Number of IP channels
        ("byStartIPChan", BYTE),       # Start IP channel number
        ("bySupport", BYTE),           # Support flags
        ("bySupport1", BYTE),          # Support flags 1
        ("bySupport2", BYTE),          # Support flags 2
        ("wDevType", WORD),            # Device type
        ("bySupport3", BYTE),          # Support flags 3
        ("byMultiStreamProto", BYTE),  # Multi-stream protocol
        ("byStartDChan", BYTE),        # Start digital channel
        ("byStartDChanHigh", BYTE),    # Start digital channel high byte
        ("byRes", BYTE * 25),          # Reserved
    ]


class NET_DVR_DEVICEINFO_V40(ctypes.Structure):
    """Extended device info structure"""
    _fields_ = [
        ("dwSize", DWORD),
        ("byChanNum", BYTE),
        ("byStartChan", BYTE),
        ("byIPChanNum", BYTE),
        ("byStartIPChan", BYTE),
        ("bySupport", BYTE),
        ("bySupport1", BYTE),
        ("bySupport2", BYTE),
        ("wDevType", WORD),
        ("bySupport3", BYTE),
        ("byMultiStreamProto", BYTE),
        ("byStartDChan", BYTE),
        ("byStartDChanHigh", BYTE),
        ("byAudioChanNum", BYTE),
        ("byAudioChanStart", BYTE),
        ("byAlarmInNum", BYTE),
        ("byAlarmOutNum", BYTE),
        ("byRS485Num", BYTE),
        ("bySupport4", BYTE),
        ("bySupport5", BYTE),
        ("bySupport6", BYTE),
        ("bySupport7", BYTE),
        ("byRes2", BYTE * 247),
    ]


class NET_DVR_TIME(ctypes.Structure):
    """Time structure"""
    _fields_ = [
        ("dwYear", DWORD),
        ("dwMonth", DWORD),
        ("dwDay", DWORD),
        ("dwHour", DWORD),
        ("dwMinute", DWORD),
        ("dwSecond", DWORD),
    ]


class NET_DVR_TIME_V30(ctypes.Structure):
    """Extended time structure with milliseconds"""
    _fields_ = [
        ("dwYear", WORD),
        ("byMonth", BYTE),
        ("byDay", BYTE),
        ("byHour", BYTE),
        ("byMinute", BYTE),
        ("bySecond", BYTE),
        ("byRes", BYTE),
        ("wMilliSec", WORD),
        ("byRes1", BYTE * 2),
    ]


class NET_DVR_IPPARACFG_V40(ctypes.Structure):
    """IP channel configuration"""
    _fields_ = [
        ("dwSize", DWORD),
        ("dwGroupNum", DWORD),
        ("struIPDevInfo", ctypes.c_byte * 512),  # NET_DVR_IPDEVINFO_V31[64]
        ("byRes", BYTE * 128),
    ]


class NET_DVR_USER_LOGIN_INFO(ctypes.Structure):
    """Login information structure"""
    _fields_ = [
        ("dwSize", DWORD),
        ("sDeviceAddress", CHAR * 129),
        ("byUseTransport", BYTE),
        ("wPort", WORD),
        ("sUserName", CHAR * 64),
        ("sPassword", CHAR * 64),
        ("byLoginMode", BYTE),
        ("byProxyType", BYTE),
        ("byHttps", BYTE),
        ("iProxyID", LONG),
        ("byVerifyMode", BYTE),
        ("byRes2", BYTE * 119),
    ]


class NET_DVR_PREVIEWINFO(ctypes.Structure):
    """Preview/playback info"""
    _fields_ = [
        ("lChannel", LONG),
        ("dwStreamType", DWORD),
        ("dwLinkMode", DWORD),
        ("hPlayWnd", HANDLE),
        ("bBlocked", BOOL),
        ("bPassbackRecord", BOOL),
        ("byPreviewMode", BYTE),
        ("byStreamID", BYTE * 32),
        ("byProtoType", BYTE),
        ("byRes", BYTE * 237),
    ]


class NET_DVR_FIND_DATA(ctypes.Structure):
    """File find data"""
    _fields_ = [
        ("sFileName", CHAR * 100),
        ("struStartTime", NET_DVR_TIME),
        ("struStopTime", NET_DVR_TIME),
        ("dwFileSize", DWORD),
        ("byFileType", BYTE),
        ("byLocked", BYTE),
        ("byRes", BYTE * 2),
    ]


class NET_DVR_FILECOND_V40(ctypes.Structure):
    """File search conditions"""
    _fields_ = [
        ("dwSize", DWORD),
        ("byChannel", BYTE),
        ("byFileType", BYTE),
        ("byRes", BYTE * 2),
        ("dwFileSize", DWORD),
        ("struStartTime", NET_DVR_TIME),
        ("struStopTime", NET_DVR_TIME),
        ("byRes1", BYTE * 128),
    ]


class NET_DVR_PLAYBACK_POS(ctypes.Structure):
    """Playback position info"""
    _fields_ = [
        ("dwFileIndex", DWORD),
        ("dwFileOffset", DWORD),
        ("dwFrameNum", DWORD),
        ("dwFrameOffset", DWORD),
        ("dwRelativeTime", DWORD),
        ("dwAbsoluteTime", DWORD),
    ]


class NET_DVR_PLAYBACKSTATUS(ctypes.Structure):
    """Playback status"""
    _fields_ = [
        ("dwFileIndex", DWORD),
        ("dwFileOffset", DWORD),
        ("dwFrameNum", DWORD),
        ("dwFrameOffset", DWORD),
        ("dwRelativeTime", DWORD),
        ("dwAbsoluteTime", DWORD),
        ("byPlayStatus", BYTE),
        ("byRes", BYTE * 3),
    ]


class NET_DVR_PTZCTRL(ctypes.Structure):
    """PTZ control parameters"""
    _fields_ = [
        ("dwSize", DWORD),
        ("dwChannel", DWORD),
        ("dwPTZCommand", DWORD),
        ("dwStop", DWORD),
        ("dwSpeed", DWORD),
        ("dwPresetIndex", DWORD),
        ("dwPresetCmd", DWORD),
        ("byRes", BYTE * 16),
    ]


class NET_DVR_ALARMININFO(ctypes.Structure):
    """Alarm input info"""
    _fields_ = [
        ("dwSize", DWORD),
        ("dwAlarmInNum", DWORD),
        ("byAlarmInType", BYTE),
        ("byRes", BYTE * 3),
        ("dwAlarmInDelay", DWORD),
        ("dwAlarmInSensitivity", DWORD),
        ("byRes1", BYTE * 128),
    ]


class NET_DVR_ALARMOUTINFO(ctypes.Structure):
    """Alarm output info"""
    _fields_ = [
        ("dwSize", DWORD),
        ("dwAlarmOutNum", DWORD),
        ("dwAlarmOutDelay", DWORD),
        ("byRes", BYTE * 128),
    ]


# =============================================================================
# Callback Types
# =============================================================================

# Preview callback
PREVIEW_CALLBACK = ctypes.CFUNCTYPE(
    None,
    LONG,           # lRealHandle
    DWORD,          # dwDataType
    LPVOID,         # pBuffer
    DWORD,          # dwBufSize
    LPVOID,         # pUser
)

# Playback callback
PLAYBACK_CALLBACK = ctypes.CFUNCTYPE(
    None,
    LONG,           # lPlayHandle
    DWORD,          # dwDataType
    LPVOID,         # pBuffer
    DWORD,          # dwBufSize
    LPVOID,         # pUser
)

# Alarm callback
ALARM_CALLBACK = ctypes.CFUNCTYPE(
    None,
    LONG,           # lCommand
    LPVOID,         # pAlarmer
    DWORD,          # dwBufLen
    LPVOID,         # pUser
)

# Message callback
MESSAGE_CALLBACK = ctypes.CFUNCTYPE(
    BOOL,
    LONG,           # lCommand
    LPVOID,         # pBuffer
    DWORD,          # dwBufLen
    LPVOID,         # pUser
)

# Exception callback
EXCEPTION_CALLBACK = ctypes.CFUNCTYPE(
    None,
    DWORD,          # dwType
    LONG,           # lUserID
    LONG,           # lHandle
    LPVOID,         # pUser
)


# =============================================================================
# Function Prototypes
# =============================================================================

def define_function(lib: ctypes.CDLL, name: str, restype, argtypes):
    """Helper to define function prototype."""
    if hasattr(lib, name):
        func = getattr(lib, name)
        func.restype = restype
        func.argtypes = argtypes
        return func
    return None


class HCNetSDKBindings:
    """
    HCNetSDK function bindings.
    Wraps the loaded library with proper ctypes prototypes.
    """
    
    def __init__(self, loader: SDKLibraryLoader):
        self.loader = loader
        self.lib = loader.get_main_sdk()
        self.playback_lib = loader.get_playback_sdk()
        self._define_functions()
    
    def _define_functions(self):
        """Define all function prototypes."""
        if not self.lib:
            return
        
        # ---------------------------------------------------------
        # Initialization / Cleanup
        # ---------------------------------------------------------
        self.NET_DVR_Init = define_function(
            self.lib, "NET_DVR_Init", BOOL, []
        )
        
        self.NET_DVR_Cleanup = define_function(
            self.lib, "NET_DVR_Cleanup", BOOL, []
        )
        
        self.NET_DVR_SetSDKInitCfg = define_function(
            self.lib, "NET_DVR_SetSDKInitCfg",
            BOOL, [DWORD, LPVOID]
        )
        
        self.NET_DVR_GetSDKVersion = define_function(
            self.lib, "NET_DVR_GetSDKVersion", DWORD, []
        )
        
        self.NET_DVR_GetLastError = define_function(
            self.lib, "NET_DVR_GetLastError", DWORD, []
        )
        
        self.NET_DVR_SetConnectTime = define_function(
            self.lib, "NET_DVR_SetConnectTime",
            BOOL, [DWORD, DWORD]
        )
        
        self.NET_DVR_SetReconnect = define_function(
            self.lib, "NET_DVR_SetReconnect",
            BOOL, [DWORD, BOOL]
        )
        
        # ---------------------------------------------------------
        # Login / Logout
        # ---------------------------------------------------------
        self.NET_DVR_Login_V30 = define_function(
            self.lib, "NET_DVR_Login_V30",
            LONG, [LPSTR, WORD, LPSTR, LPSTR, ctypes.POINTER(NET_DVR_DEVICEINFO_V30)]
        )
        
        self.NET_DVR_Login_V40 = define_function(
            self.lib, "NET_DVR_Login_V40",
            LONG, [ctypes.POINTER(NET_DVR_USER_LOGIN_INFO), ctypes.POINTER(NET_DVR_DEVICEINFO_V40)]
        )
        
        self.NET_DVR_Logout = define_function(
            self.lib, "NET_DVR_Logout", BOOL, [LONG]
        )
        
        self.NET_DVR_Logout_V30 = define_function(
            self.lib, "NET_DVR_Logout_V30", BOOL, [LONG]
        )
        
        # ---------------------------------------------------------
        # Preview / Live View
        # ---------------------------------------------------------
        self.NET_DVR_RealPlay_V40 = define_function(
            self.lib, "NET_DVR_RealPlay_V40",
            LONG, [LONG, ctypes.POINTER(NET_DVR_PREVIEWINFO), PREVIEW_CALLBACK, LPVOID]
        )
        
        self.NET_DVR_StopRealPlay = define_function(
            self.lib, "NET_DVR_StopRealPlay", BOOL, [LONG]
        )
        
        self.NET_DVR_SetRealDataCallBack = define_function(
            self.lib, "NET_DVR_SetRealDataCallBack",
            BOOL, [LONG, PREVIEW_CALLBACK, LPVOID]
        )
        
        # ---------------------------------------------------------
        # Playback
        # ---------------------------------------------------------
        self.NET_DVR_PlayBackByTime = define_function(
            self.lib, "NET_DVR_PlayBackByTime",
            LONG, [LONG, LONG, ctypes.POINTER(NET_DVR_TIME), ctypes.POINTER(NET_DVR_TIME), HANDLE]
        )
        
        self.NET_DVR_PlayBackByName = define_function(
            self.lib, "NET_DVR_PlayBackByName",
            LONG, [LONG, LPSTR, HANDLE]
        )
        
        self.NET_DVR_PlayBackControl = define_function(
            self.lib, "NET_DVR_PlayBackControl",
            BOOL, [LONG, DWORD, LPVOID]
        )
        
        self.NET_DVR_PlayBackSetPos = define_function(
            self.lib, "NET_DVR_PlayBackSetPos",
            BOOL, [LONG, DWORD]
        )
        
        self.NET_DVR_PlayBackGetPos = define_function(
            self.lib, "NET_DVR_PlayBackGetPos",
            BOOL, [LONG, ctypes.POINTER(NET_DVR_PLAYBACK_POS)]
        )
        
        self.NET_DVR_PlayBackGetStatus = define_function(
            self.lib, "NET_DVR_PlayBackGetStatus",
            BOOL, [LONG, ctypes.POINTER(NET_DVR_PLAYBACKSTATUS)]
        )
        
        self.NET_DVR_StopPlayBack = define_function(
            self.lib, "NET_DVR_StopPlayBack", BOOL, [LONG]
        )
        
        self.NET_DVR_SetPlayDataCallBack = define_function(
            self.lib, "NET_DVR_SetPlayDataCallBack",
            BOOL, [LONG, PLAYBACK_CALLBACK, LPVOID]
        )
        
        self.NET_DVR_PlayBackSaveData = define_function(
            self.lib, "NET_DVR_PlayBackSaveData",
            BOOL, [LONG, LPSTR]
        )
        
        self.NET_DVR_PlayBackCaptureFile = define_function(
            self.lib, "NET_DVR_PlayBackCaptureFile",
            BOOL, [LONG, LPSTR]
        )
        
        # ---------------------------------------------------------
        # File Search
        # ---------------------------------------------------------
        self.NET_DVR_FindFile_V30 = define_function(
            self.lib, "NET_DVR_FindFile_V30",
            LONG, [LONG, ctypes.POINTER(NET_DVR_FILECOND_V40)]
        )
        
        self.NET_DVR_FindNextFile_V30 = define_function(
            self.lib, "NET_DVR_FindNextFile_V30",
            BOOL, [LONG, ctypes.POINTER(NET_DVR_FIND_DATA)]
        )
        
        self.NET_DVR_FindClose_V30 = define_function(
            self.lib, "NET_DVR_FindClose_V30",
            BOOL, [LONG]
        )
        
        # ---------------------------------------------------------
        # PTZ Control
        # ---------------------------------------------------------
        self.NET_DVR_PTZControl_Other = define_function(
            self.lib, "NET_DVR_PTZControl_Other",
            BOOL, [LONG, LONG, DWORD, DWORD]
        )
        
        self.NET_DVR_PTZControlWithSpeed = define_function(
            self.lib, "NET_DVR_PTZControlWithSpeed",
            BOOL, [LONG, LONG, DWORD, DWORD, DWORD]
        )
        
        self.NET_DVR_PTZPreset = define_function(
            self.lib, "NET_DVR_PTZPreset",
            BOOL, [LONG, LONG, DWORD, DWORD]
        )
        
        self.NET_DVR_PTZCruise = define_function(
            self.lib, "NET_DVR_PTZCruise",
            BOOL, [LONG, LONG, DWORD, DWORD]
        )
        
        self.NET_DVR_PTZTrack = define_function(
            self.lib, "NET_DVR_PTZTrack",
            BOOL, [LONG, LONG, DWORD, DWORD]
        )
        
        # ---------------------------------------------------------
        # Download
        # ---------------------------------------------------------
        self.NET_DVR_GetFileByName = define_function(
            self.lib, "NET_DVR_GetFileByName",
            LONG, [LONG, LPSTR, LPSTR]
        )
        
        self.NET_DVR_GetFileByTime = define_function(
            self.lib, "NET_DVR_GetFileByTime",
            LONG, [LONG, LONG, ctypes.POINTER(NET_DVR_TIME), ctypes.POINTER(NET_DVR_TIME), LPSTR]
        )
        
        self.NET_DVR_StopGetFile = define_function(
            self.lib, "NET_DVR_StopGetFile", BOOL, [LONG]
        )
        
        self.NET_DVR_GetDownloadPos = define_function(
            self.lib, "NET_DVR_GetDownloadPos", DWORD, [LONG]
        )
        
        self.NET_DVR_SetDownloadDataCallBack = define_function(
            self.lib, "NET_DVR_SetDownloadDataCallBack",
            BOOL, [LONG, ctypes.CFUNCTYPE(None, LONG, DWORD, LPVOID, DWORD, LPVOID), LPVOID]
        )
        
        # ---------------------------------------------------------
        # Device Configuration
        # ---------------------------------------------------------
        self.NET_DVR_GetDVRConfig = define_function(
            self.lib, "NET_DVR_GetDVRConfig",
            BOOL, [LONG, DWORD, LONG, LPVOID, DWORD, ctypes.POINTER(DWORD)]
        )
        
        self.NET_DVR_SetDVRConfig = define_function(
            self.lib, "NET_DVR_SetDVRConfig",
            BOOL, [LONG, DWORD, LONG, LPVOID, DWORD]
        )
        
        # ---------------------------------------------------------
        # Capabilities
        # ---------------------------------------------------------
        self.NET_DVR_GetDeviceAbility = define_function(
            self.lib, "NET_DVR_GetDeviceAbility",
            BOOL, [LONG, DWORD, LPVOID, DWORD, ctypes.POINTER(DWORD)]
        )
        
        # ---------------------------------------------------------
        # Alarm / Event
        # ---------------------------------------------------------
        self.NET_DVR_SetupAlarmChan = define_function(
            self.lib, "NET_DVR_SetupAlarmChan", LONG, [LONG]
        )
        
        self.NET_DVR_CloseAlarmChan = define_function(
            self.lib, "NET_DVR_CloseAlarmChan", BOOL, [LONG]
        )
        
        self.NET_DVR_SetMessageCallBack = define_function(
            self.lib, "NET_DVR_SetMessageCallBack",
            BOOL, [MESSAGE_CALLBACK, LPVOID]
        )
        
        self.NET_DVR_SetExceptionCallBack = define_function(
            self.lib, "NET_DVR_SetExceptionCallBack",
            BOOL, [EXCEPTION_CALLBACK, LPVOID]
        )
        
        # ---------------------------------------------------------
        # Smart Search (VCA)
        # ---------------------------------------------------------
        self.NET_DVR_SmartSearch = define_function(
            self.lib, "NET_DVR_SmartSearch",
            LONG, [LONG, LPVOID]
        )
        
        # ---------------------------------------------------------
        # Playback Library (HCPlayM4)
        # ---------------------------------------------------------
        if self.playback_lib:
            self._define_playback_functions()
    
    def _define_playback_functions(self):
        """Define HCPlayM4 playback library functions."""
        lib = self.playback_lib
        
        self.PlayM4_GetPort = define_function(
            lib, "PlayM4_GetPort", BOOL, [ctypes.POINTER(LONG)]
        )
        
        self.PlayM4_FreePort = define_function(
            lib, "PlayM4_FreePort", BOOL, [LONG]
        )
        
        self.PlayM4_OpenFile = define_function(
            lib, "PlayM4_OpenFile", BOOL, [LONG, LPSTR]
        )
        
        self.PlayM4_CloseFile = define_function(
            lib, "PlayM4_CloseFile", BOOL, [LONG]
        )
        
        self.PlayM4_Play = define_function(
            lib, "PlayM4_Play", BOOL, [LONG, HANDLE]
        )
        
        self.PlayM4_Stop = define_function(
            lib, "PlayM4_Stop", BOOL, [LONG]
        )
        
        self.PlayM4_Pause = define_function(
            lib, "PlayM4_Pause", BOOL, [LONG]
        )
        
        self.PlayM4_SetPlaySpeed = define_function(
            lib, "PlayM4_SetPlaySpeed", BOOL, [LONG, DWORD]
        )
        
        self.PlayM4_GetPlaySpeed = define_function(
            lib, "PlayM4_GetPlaySpeed", DWORD, [LONG]
        )
        
        self.PlayM4_SetFilePos = define_function(
            lib, "PlayM4_SetFilePos", BOOL, [LONG, DWORD]
        )
        
        self.PlayM4_GetFilePos = define_function(
            lib, "PlayM4_GetFilePos", DWORD, [LONG]
        )
        
        self.PlayM4_GetFileLength = define_function(
            lib, "PlayM4_GetFileLength", DWORD, [LONG]
        )
        
        self.PlayM4_SetDecCallBack = define_function(
            lib, "PlayM4_SetDecCallBack",
            BOOL, [LONG, ctypes.CFUNCTYPE(None, LONG, LPVOID, DWORD, LPVOID), LPVOID]
        )
        
        self.PlayM4_GetPicture = define_function(
            lib, "PlayM4_GetPicture", BOOL, [LONG, LPSTR]
        )
        
        self.PlayM4_InputData = define_function(
            lib, "PlayM4_InputData",
            BOOL, [LONG, LPVOID, DWORD]
        )
    
    # =============================================================
    # Helper Methods
    # =============================================================
    
    def get_last_error(self) -> int:
        """Get last error code."""
        if self.NET_DVR_GetLastError:
            return self.NET_DVR_GetLastError()
        return -1
    
    def check_error(self, context: str = "") -> None:
        """Check and raise for last error."""
        error = self.get_last_error()
        if error != 0:
            raise_for_error(error, context)
    
    def init(self) -> bool:
        """Initialize SDK."""
        if self.NET_DVR_Init:
            result = self.NET_DVR_Init()
            self.check_error("NET_DVR_Init")
            return bool(result)
        return False
    
    def cleanup(self) -> bool:
        """Cleanup SDK."""
        if self.NET_DVR_Cleanup:
            result = self.NET_DVR_Cleanup()
            self.check_error("NET_DVR_Cleanup")
            return bool(result)
        return False


# =============================================================================
# High-level Structures (Python wrappers)
# =============================================================================

@dataclass
class DeviceInfo:
    """Parsed device information."""
    channel_count: int
    start_channel: int
    ip_channel_count: int
    start_ip_channel: int
    device_type: int
    support_flags: dict
    
    @classmethod
    def from_v30(cls, info: NET_DVR_DEVICEINFO_V30) -> "DeviceInfo":
        return cls(
            channel_count=info.byChanNum,
            start_channel=info.byStartChan,
            ip_channel_count=info.byIPChanNum,
            start_ip_channel=info.byStartIPChan,
            device_type=info.wDevType,
            support_flags={
                "support": info.bySupport,
                "support1": info.bySupport1,
                "support2": info.bySupport2,
                "support3": info.bySupport3,
                "multi_stream_proto": info.byMultiStreamProto,
            }
        )
    
    @classmethod
    def from_v40(cls, info: NET_DVR_DEVICEINFO_V40) -> "DeviceInfo":
        return cls(
            channel_count=info.byChanNum,
            start_channel=info.byStartChan,
            ip_channel_count=info.byIPChanNum,
            start_ip_channel=info.byStartIPChan,
            device_type=info.wDevType,
            support_flags={
                "support": info.bySupport,
                "support1": info.bySupport1,
                "support2": info.bySupport2,
                "support3": info.bySupport3,
                "multi_stream_proto": info.byMultiStreamProto,
                "audio_channels": info.byAudioChanNum,
                "alarm_in": info.byAlarmInNum,
                "alarm_out": info.byAlarmOutNum,
                "rs485": info.byRS485Num,
            }
        )


@dataclass
class TimeInfo:
    """Parsed time information."""
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int = 0
    
    @classmethod
    def from_net_dvr_time(cls, t: NET_DVR_TIME) -> "TimeInfo":
        return cls(
            year=t.dwYear,
            month=t.dwMonth,
            day=t.dwDay,
            hour=t.dwHour,
            minute=t.dwMinute,
            second=t.dwSecond,
        )
    
    @classmethod
    def from_net_dvr_time_v30(cls, t: NET_DVR_TIME_V30) -> "TimeInfo":
        return cls(
            year=t.dwYear,
            month=t.byMonth,
            day=t.byDay,
            hour=t.byHour,
            minute=t.byMinute,
            second=t.bySecond,
            millisecond=t.wMilliSec,
        )
    
    def to_net_dvr_time(self) -> NET_DVR_TIME:
        t = NET_DVR_TIME()
        t.dwYear = self.year
        t.dwMonth = self.month
        t.dwDay = self.day
        t.dwHour = self.hour
        t.dwMinute = self.minute
        t.dwSecond = self.second
        return t
    
    def to_datetime(self):
        from datetime import datetime
        return datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)
    
    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}"


@dataclass
class FileInfo:
    """Parsed file information from search."""
    filename: str
    start_time: TimeInfo
    stop_time: TimeInfo
    file_size: int
    file_type: int
    locked: bool
    
    @classmethod
    def from_find_data(cls, data: NET_DVR_FIND_DATA) -> "FileInfo":
        return cls(
            filename=data.sFileName.decode('utf-8', errors='ignore').rstrip('\x00'),
            start_time=TimeInfo.from_net_dvr_time(data.struStartTime),
            stop_time=TimeInfo.from_net_dvr_time(data.struStopTime),
            file_size=data.dwFileSize,
            file_type=data.byFileType,
            locked=bool(data.byLocked),
        )
    
    @property
    def duration_seconds(self) -> int:
        start = self.start_time.to_datetime()
        stop = self.stop_time.to_datetime()
        return int((stop - start).total_seconds())