"""
Core module for Hikvision Recovery.
"""

from .models import (
    DeviceInfo,
    RecordingInfo,
    RecordingList,
    SearchCriteria,
    StreamInfo,
    Capability,
    DownloadProgress,
    RecordingType,
    StreamType,
    VideoCodec,
)

from .isapi_client import (
    ISAPIClient,
    ISAPIConfig,
    ISAPIError,
    ISAPIAuthError,
    ISAPIConnectionError,
)

__all__ = [
    # Models
    "DeviceInfo",
    "RecordingInfo",
    "RecordingList",
    "SearchCriteria",
    "SearchResult",
    "StreamInfo",
    "Capability",
    "DownloadProgress",
    "RecordingType",
    "StreamType",
    "VideoCodec",
    # Client
    "ISAPIClient",
    "ISAPIConfig",
    "ISAPIError",
    "ISAPIAuthError",
    "ISAPIConnectionError",
]