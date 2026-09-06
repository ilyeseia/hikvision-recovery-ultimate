"""
Tests for Hikvision Recovery.
"""

import pytest
from datetime import datetime, timedelta

from hikvision_recovery.core.models import (
    DeviceInfo,
    RecordingInfo,
    RecordingList,
    SearchCriteria,
    RecordingType,
    StreamType,
    VideoCodec,
    DownloadProgress,
)


class TestModels:
    """Test Pydantic models"""
    
    def test_recording_type_enum(self):
        assert RecordingType.CONTINUOUS.value == "continuous"
        assert RecordingType.MOTION.value == "motion"
        assert RecordingType.ALL.value == "all"
    
    def test_stream_type_enum(self):
        assert StreamType.MAIN.value == "main"
        assert StreamType.SUB.value == "sub"
        assert StreamType.TRANS.value == "trans"
    
    def test_video_codec_enum(self):
        assert VideoCodec.H264.value == "h264"
        assert VideoCodec.H265.value == "h265"
    
    def test_search_criteria_to_params(self):
        criteria = SearchCriteria(
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 12, 0, 0),
            camera_ids=[1, 2],
            recording_types=[RecordingType.MOTION, RecordingType.ALARM],
            stream_type=StreamType.MAIN,
            max_results=50,
        )
        
        params = criteria.to_isapi_params()
        
        assert params["startTime"] == "2024-01-15T10:00:00Z"
        assert params["endTime"] == "2024-01-15T12:00:00Z"
        assert params["cameraIDs"] == "1,2"
        assert "motion" in params["recordingTypes"]
        assert "alarm" in params["recordingTypes"]
        assert params["streamType"] == "main"
        assert params["maxResults"] == "50"
    
    def test_search_criteria_no_cameras(self):
        criteria = SearchCriteria(
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 12, 0, 0),
        )
        
        params = criteria.to_isapi_params()
        assert params["cameraIDs"] == ""
    
    def test_recording_duration(self):
        rec = RecordingInfo(
            id="test123",
            name="Test Recording",
            camera_id=1,
            channel=1,
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 30, 45),
            recording_type=RecordingType.CONTINUOUS,
            file_size=1024 * 1024 * 100,  # 100 MB
        )
        
        assert rec.duration_seconds == 1845  # 30m 45s
        assert "30m" in rec.duration_human
    
    def test_recording_list_has_more(self):
        rec_list = RecordingList(
            recordings=[RecordingInfo(
                id="1", name="Test", camera_id=1, channel=1,
                start_time=datetime.now(), end_time=datetime.now(),
                recording_type=RecordingType.CONTINUOUS, file_size=100
            )] * 20,
            total_matches=50,
            page_size=20,
            page_number=1,
        )
        
        assert rec_list.has_more is True
        
        rec_list.page_number = 3
        assert rec_list.has_more is False
    
    def test_download_progress(self):
        prog = DownloadProgress(
            recording_id="test123",
            file_name="test.mp4",
            total_bytes=1000000,
            downloaded_bytes=500000,
        )
        
        assert prog.progress_percent == 50.0
        assert prog.downloaded_mb == 500000 / (1024 * 1024)
        assert prog.total_mb == 1000000 / (1024 * 1024)
    
    def test_recording_datetime_parsing(self):
        # Test various Hikvision datetime formats
        formats = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+08:00",
            "2024-01-15T10:30:00.123Z",
            "2024-01-15 10:30:00",
        ]
        
        for fmt in formats:
            rec = RecordingInfo(
                id="test",
                name="Test",
                camera_id=1,
                channel=1,
                start_time=fmt,
                end_time=fmt,
                recording_type=RecordingType.CONTINUOUS,
                file_size=100,
            )
            assert isinstance(rec.start_time, datetime)
            assert isinstance(rec.end_time, datetime)


class TestUtils:
    """Test utility functions"""
    
    def test_parse_camera_list(self):
        from hikvision_recovery.utils import parse_camera_list
        
        assert parse_camera_list("1,2,3") == [1, 2, 3]
        assert parse_camera_list("1-3") == [1, 2, 3]
        assert parse_camera_list("1,3-5,7") == [1, 3, 4, 5, 7]
        assert parse_camera_list("") == []
        assert parse_camera_list("  1 , 2  ") == [1, 2]
    
    def test_human_readable_size(self):
        from hikvision_recovery.utils import human_readable_size
        
        assert human_readable_size(500) == "500.0 B"
        assert human_readable_size(1024) == "1.0 KB"
        assert human_readable_size(1024 * 1024) == "1.0 MB"
        assert human_readable_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_human_readable_duration(self):
        from hikvision_recovery.utils import human_readable_duration
        
        assert human_readable_duration(30) == "30s"
        assert human_readable_duration(90) == "1m 30s"
        assert human_readable_duration(3661) == "1h 1m"
        assert human_readable_duration(90061) == "1d 1h"
    
    def test_sanitize_filename(self):
        from hikvision_recovery.utils import sanitize_filename
        
        assert sanitize_filename("normal_file.mp4") == "normal_file.mp4"
        assert sanitize_filename('file<name>.mp4') == "file_name_.mp4"
        assert sanitize_filename('file:name.mp4') == "file_name.mp4"
        assert sanitize_filename("  spaces  ") == "spaces"
    
    def test_validate_ip(self):
        from hikvision_recovery.utils import validate_ip
        
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.0.0.1") is True
        assert validate_ip("256.1.1.1") is False
        assert validate_ip("not.an.ip") is False
    
    def test_validate_host(self):
        from hikvision_recovery.utils import validate_host
        
        assert validate_host("192.168.1.1") is True
        assert validate_host("dvr.local") is True
        assert validate_host("my-dvr.example.com") is True
        assert validate_host("-invalid.com") is False


class TestISAPIConfig:
    """Test ISAPI configuration"""
    
    def test_base_url_http(self):
        from hikvision_recovery.core.isapi_client import ISAPIConfig
        
        config = ISAPIConfig(host="192.168.1.100", username="admin", password="pass")
        assert config.base_url == "http://192.168.1.100:80"
        assert config.isapi_base == "http://192.168.1.100:80/ISAPI/"
    
    def test_base_url_https(self):
        from hikvision_recovery.core.isapi_client import ISAPIConfig
        
        config = ISAPIConfig(
            host="192.168.1.100", 
            username="admin", 
            password="pass",
            use_https=True,
            port=443
        )
        assert config.base_url == "https://192.168.1.100:443"
        assert config.isapi_base == "https://192.168.1.100:443/ISAPI/"
    
    def test_custom_port(self):
        from hikvision_recovery.core.isapi_client import ISAPIConfig
        
        config = ISAPIConfig(host="192.168.1.100", username="admin", password="pass", port=8080)
        assert config.base_url == "http://192.168.1.100:8080"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])