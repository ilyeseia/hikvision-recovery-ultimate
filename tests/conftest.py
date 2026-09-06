"""
Pytest configuration and fixtures.
"""

import pytest
from datetime import datetime, timedelta

from hikvision_recovery.core.models import (
    DeviceInfo,
    RecordingInfo,
    SearchCriteria,
    RecordingType,
    StreamType,
)


@pytest.fixture
def sample_device_info():
    return DeviceInfo(
        deviceName="Test DVR",
        deviceID="123456",
        model="DS-7608NI-K2",
        serialNumber="ABC123456",
        macAddress="00:11:22:33:44:55",
        firmwareVersion="V4.0.0",
        firmwareReleasedDate="2023-01-01",
        encodingVersion="V1.0",
        buildDate="2023-01-01",
        isSupportIPv6=True,
        isSupportDDNS=True,
        isSupportPPPoE=True,
        isSupportUPnP=True,
        isSupportNAT=True,
        isSupportSNMP=True,
        isSupportRTSP=True,
        isSupportHTTPS=True,
        isSupport8021x=True,
        isSupportNTP=True,
        isSupportIPFilter=True,
        isSupportAutoReboot=True,
        isSupportEmail=True,
        isSupportFTP=True,
        isSupportAlarmServer=True,
        isSupportCloud=True,
        isSupportP2P=True,
        language="English",
        timezone="UTC+8",
    )


@pytest.fixture
def sample_recording():
    return RecordingInfo(
        id="rec_001",
        name="Camera1_20240115100000",
        cameraID=1,
        channel=1,
        startTime=datetime(2024, 1, 15, 10, 0, 0),
        endTime=datetime(2024, 1, 15, 11, 30, 0),
        recordingType=RecordingType.CONTINUOUS,
        fileSize=1024 * 1024 * 500,  # 500 MB
        locked=False,
    )


@pytest.fixture
def sample_search_criteria():
    return SearchCriteria(
        start_time=datetime(2024, 1, 15, 0, 0, 0),
        end_time=datetime(2024, 1, 15, 23, 59, 59),
        camera_ids=[1, 2],
        recording_types=[RecordingType.MOTION, RecordingType.ALARM],
        stream_type=StreamType.MAIN,
        max_results=100,
        page_size=20,
    )