"""
Custom exceptions for Hikvision SDK wrapper.
"""

from typing import Optional


class HikvisionSDKError(Exception):
    """Base exception for all Hikvision SDK errors."""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self):
        if self.error_code is not None:
            return f"{self.message} (Error code: {self.error_code})"
        return self.message


class SDKLoadError(HikvisionSDKError):
    """Failed to load SDK library."""
    pass


class SDKInitializationError(HikvisionSDKError):
    """Failed to initialize SDK."""
    pass


class LoginError(HikvisionSDKError):
    """Login/authentication failed."""
    pass


class ConnectionError(HikvisionSDKError):
    """Connection to device failed."""
    pass


class TimeoutError(HikvisionSDKError):
    """Operation timed out."""
    pass


class InvalidParameterError(HikvisionSDKError):
    """Invalid parameter passed to SDK function."""
    pass


class UnsupportedOperationError(HikvisionSDKError):
    """Operation not supported by device/firmware."""
    pass


class PlaybackError(HikvisionSDKError):
    """Playback operation failed."""
    pass


class SearchError(HikvisionSDKError):
    """Search operation failed."""
    pass


class DownloadError(HikvisionSDKError):
    """File download failed."""
    pass


class PTZError(HikvisionSDKError):
    """PTZ control failed."""
    pass


class CallbackError(HikvisionSDKError):
    """Callback registration/execution failed."""
    pass


# Error code mappings (from HCNetSDK.h)
ERROR_CODES = {
    0: "No error",
    1: "User not logged in",
    2: "Invalid password",
    3: "Invalid username",
    4: "Insufficient permissions",
    5: "Device not found",
    6: "Connection timeout",
    7: "Network error",
    8: "Invalid handle",
    9: "Unsupported function",
    10: "Invalid parameter",
    11: "Channel not exist",
    12: "No resource",
    13: "File not found",
    14: "Disk full",
    15: "Configuration error",
    16: "Already in use",
    17: "Not supported",
    18: "Timeout",
    19: "Buffer too small",
    20: "Data error",
    21: "Not initialized",
    22: "Already initialized",
    23: "SDK not loaded",
    24: "Version mismatch",
    25: "License error",
    100: "Unknown error",
}


def get_error_message(error_code: int) -> str:
    """Get human-readable error message for SDK error code."""
    return ERROR_CODES.get(error_code, f"Unknown error code: {error_code}")


def raise_for_error(error_code: int, context: str = ""):
    """Raise appropriate exception for error code."""
    if error_code == 0:
        return
    
    msg = get_error_message(error_code)
    full_msg = f"{context}: {msg}" if context else msg
    
    # Map error codes to specific exceptions
    if error_code in (1, 2, 3):
        raise LoginError(full_msg, error_code)
    elif error_code in (6, 7):
        raise ConnectionError(full_msg, error_code)
    elif error_code == 18:
        raise TimeoutError(full_msg, error_code)
    elif error_code == 10:
        raise InvalidParameterError(full_msg, error_code)
    elif error_code == 9:
        raise UnsupportedOperationError(full_msg, error_code)
    else:
        raise HikvisionSDKError(full_msg, error_code)