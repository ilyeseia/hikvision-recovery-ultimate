"""
Core data models for Hikvision ISAPI responses.
Using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RecordingType(str, Enum):
    CONTINUOUS = "continuous"
    MOTION = "motion"
    ALARM = "alarm"
    ALARM_MOTION = "alarmMotion"
    SMART = "smart"
    POS = "pos"
    HEAT_MAP = "heatMap"
    ANR = "anr"
    ALL = "all"


class StreamType(str, Enum):
    MAIN = "main"
    SUB = "sub"
    TRANS = "trans"


class VideoCodec(str, Enum):
    H264 = "h264"
    H265 = "h265"
    MPEG4 = "mpeg4"
    MJPEG = "mjpeg"


class DeviceInfo(BaseModel):
    device_name: str = Field(alias="deviceName")
    device_id: str = Field(alias="deviceID")
    model: str
    serial_number: str = Field(alias="serialNumber")
    mac_address: str = Field(alias="macAddress")
    firmware_version: str = Field(alias="firmwareVersion")
    firmware_date: str = Field(alias="firmwareReleasedDate")
    encoding_version: str = Field(alias="encodingVersion")
    build_date: str = Field(alias="buildDate")
    is_support_ipv6: bool = Field(alias="isSupportIPv6")
    is_support_ddns: bool = Field(alias="isSupportDDNS")
    is_support_pppoe: bool = Field(alias="isSupportPPPoE")
    is_support_upnp: bool = Field(alias="isSupportUPnP")
    is_support_nat: bool = Field(alias="isSupportNAT")
    is_support_snmp: bool = Field(alias="isSupportSNMP")
    is_support_rtsp: bool = Field(alias="isSupportRTSP")
    is_support_https: bool = Field(alias="isSupportHTTPS")
    is_support_8021x: bool = Field(alias="isSupport8021x")
    is_support_ntp: bool = Field(alias="isSupportNTP")
    is_support_ip_filter: bool = Field(alias="isSupportIPFilter")
    is_support_auto_reboot: bool = Field(alias="isSupportAutoReboot")
    is_support_email: bool = Field(alias="isSupportEmail")
    is_support_ftp: bool = Field(alias="isSupportFTP")
    is_support_alarm_server: bool = Field(alias="isSupportAlarmServer")
    is_support_cloud: bool = Field(alias="isSupportCloud")
    is_support_p2p: bool = Field(alias="isSupportP2P")
    language: str
    timezone: str
    dst: Optional[str] = None
    ntp_server: Optional[str] = Field(default=None, alias="ntpServer")
    manufacturer: Optional[str] = None
    device_type: Optional[str] = Field(default=None, alias="deviceType")
    
    class Config:
        populate_by_name = True
        extra = "allow"


class RecordingInfo(BaseModel):
    id: str
    name: str
    camera_id: int = Field(alias="cameraID")
    channel: int
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    recording_type: RecordingType = Field(alias="recordingType")
    file_size: int = Field(alias="fileSize", ge=0)
    locked: bool = False
    download_url: Optional[str] = Field(default=None, alias="downloadURL")
    playback_url: Optional[str] = Field(default=None, alias="playbackURL")
    stream_type: StreamType = Field(default=StreamType.MAIN, alias="streamType")
    video_codec: Optional[VideoCodec] = Field(default=None, alias="videoCodec")
    resolution_width: Optional[int] = Field(default=None, alias="resolutionWidth")
    resolution_height: Optional[int] = Field(default=None, alias="resolutionHeight")
    frame_rate: Optional[float] = Field(default=None, alias="frameRate")
    bit_rate: Optional[int] = Field(default=None, alias="bitRate")
    is_encrypted: bool = Field(default=False, alias="isEncrypted")
    
    class Config:
        populate_by_name = True
        extra = "allow"
    
    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        return v
    
    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def duration_human(self) -> str:
        secs = int(self.duration_seconds)
        h, m = divmod(secs, 3600)
        m, s = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        elif m:
            return f"{m}m {s}s"
        return f"{s}s"


class RecordingList(BaseModel):
    recordings: List[RecordingInfo] = Field(default_factory=list)
    total_matches: int = Field(default=0, alias="totalMatches")
    page_size: int = Field(default=20, alias="pageSize")
    page_number: int = Field(default=1, alias="pageNumber")
    search_id: Optional[str] = Field(default=None, alias="searchID")
    
    class Config:
        populate_by_name = True
        extra = "allow"
    
    @property
    def has_more(self) -> bool:
        return (self.page_number * self.page_size) < self.total_matches


class SearchCriteria(BaseModel):
    start_time: datetime
    end_time: datetime
    camera_ids: Optional[List[int]] = Field(default=None, alias="cameraIDs")
    recording_types: List[RecordingType] = Field(default=[RecordingType.ALL], alias="recordingTypes")
    stream_type: StreamType = Field(default=StreamType.MAIN, alias="streamType")
    max_results: int = Field(default=100, alias="maxResults", ge=1, le=1000)
    page_size: int = Field(default=20, alias="pageSize", ge=1, le=100)
    page_number: int = Field(default=1, alias="pageNumber", ge=1)
    
    class Config:
        populate_by_name = True
        extra = "allow"
    
    def to_isapi_params(self) -> Dict[str, Any]:
        return {
            "startTime": self.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": self.end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cameraIDs": ",".join(map(str, self.camera_ids)) if self.camera_ids else "",
            "recordingTypes": ",".join([t.value for t in self.recording_types]),
            "streamType": self.stream_type.value,
            "maxResults": str(self.max_results),
            "pageSize": str(self.page_size),
            "pageNumber": str(self.page_number),
        }


class StreamInfo(BaseModel):
    channel: int
    stream_type: StreamType = Field(alias="streamType")
    video_codec: VideoCodec = Field(alias="videoCodec")
    resolution_width: int = Field(alias="resolutionWidth")
    resolution_height: int = Field(alias="resolutionHeight")
    frame_rate: int = Field(alias="frameRate")
    bit_rate: int = Field(alias="bitRate")
    is_enabled: bool = Field(default=True, alias="isEnabled")
    
    class Config:
        populate_by_name = True
        extra = "allow"
    
    @property
    def resolution(self) -> str:
        return f"{self.resolution_width}x{self.resolution_height}"


class Capability(BaseModel):
    device_type: str = Field(alias="deviceType")
    max_channels: int = Field(alias="maxChannels")
    max_analog_channels: int = Field(default=0, alias="maxAnalogChannels")
    max_ip_channels: int = Field(default=0, alias="maxIPChannels")
    max_encoding_channels: int = Field(default=0, alias="maxEncodingChannels")
    supported_codecs: List[VideoCodec] = Field(default_factory=list, alias="supportedCodecs")
    supported_resolutions: List[str] = Field(default_factory=list, alias="supportedResolutions")
    supports_motion_detection: bool = Field(default=False, alias="supportsMotionDetection")
    supports_alarm_input: bool = Field(default=False, alias="supportsAlarmInput")
    supports_alarm_output: bool = Field(default=False, alias="supportsAlarmOutput")
    supports_audio: bool = Field(default=False, alias="supportsAudio")
    supports_two_way_audio: bool = Field(default=False, alias="supportsTwoWayAudio")
    supports_ptz: bool = Field(default=False, alias="supportsPTZ")
    supports_preset: bool = Field(default=False, alias="supportsPreset")
    supports_cruise: bool = Field(default=False, alias="supportsCruise")
    supports_track: bool = Field(default=False, alias="supportsTrack")
    supports_smart: bool = Field(default=False, alias="supportsSmart")
    supports_anr: bool = Field(default=False, alias="supportsANR")
    supports_cloud: bool = Field(default=False, alias="supportsCloud")
    supports_p2p: bool = Field(default=False, alias="supportsP2P")
    supports_https: bool = Field(default=False, alias="supportsHTTPS")
    supports_rtsp: bool = Field(default=False, alias="supportsRTSP")
    supports_onvif: bool = Field(default=False, alias="supportsONVIF")
    
    class Config:
        populate_by_name = True
        extra = "allow"


class DownloadProgress(BaseModel):
    recording_id: str
    file_name: str
    total_bytes: int
    downloaded_bytes: int = 0
    start_time: datetime = Field(default_factory=datetime.now)
    last_update: datetime = Field(default_factory=datetime.now)
    speed_bps: float = 0.0
    eta_seconds: Optional[float] = None
    status: str = "pending"
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100
    
    @property
    def downloaded_mb(self) -> float:
        return self.downloaded_bytes / (1024 * 1024)
    
    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)
    
    @property
    def speed_mbps(self) -> float:
        return self.speed_bps / (1024 * 1024)