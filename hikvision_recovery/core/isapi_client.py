"""
ISAPI Client for Hikvision devices.
Supports Digest/Basic auth, automatic session management, retry logic.
"""

import time
import logging
from typing import Optional, Dict, Any, List, BinaryIO, Iterator
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .models import (
    DeviceInfo,
    RecordingInfo,
    RecordingList,
    SearchCriteria,
    StreamInfo,
    Capability,
    DownloadProgress,
)

logger = logging.getLogger(__name__)


@dataclass
class ISAPIConfig:
    """Configuration for ISAPI client"""
    host: str
    username: str
    password: str
    port: int = 80
    use_https: bool = False
    verify_ssl: bool = False
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5
    digest_auth: bool = True
    user_agent: str = "HikvisionRecovery/0.1.0"
    
    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"
    
    @property
    def isapi_base(self) -> str:
        return urljoin(self.base_url, "/ISAPI/")


class ISAPIError(Exception):
    """Base exception for ISAPI errors"""
    def __init__(self, message: str, status_code: int = 0, response: Optional[requests.Response] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ISAPIAuthError(ISAPIError):
    """Authentication failed"""
    pass


class ISAPIConnectionError(ISAPIError):
    """Connection/timeout error"""
    pass


class ISAPIClient:
    """
    Professional ISAPI client for Hikvision DVR/NVR devices.
    
    Features:
    - Automatic Digest/Basic authentication
    - Session persistence with cookie jar
    - Automatic retry with exponential backoff
    - Streaming downloads with progress tracking
    - Comprehensive error handling
    """
    
    def __init__(self, config: ISAPIConfig):
        self.config = config
        self.session = self._create_session()
        self._device_info: Optional[DeviceInfo] = None
        self._capabilities: Optional[Capability] = None
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": self.config.user_agent})
        
        # Retry strategy for transient errors
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth(self):
        if self.config.digest_auth:
            return HTTPDigestAuth(self.config.username, self.config.password)
        return HTTPBasicAuth(self.config.username, self.config.password)
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        stream: bool = False,
        **kwargs
    ) -> requests.Response:
        url = urljoin(self.config.isapi_base, endpoint.lstrip("/"))
        
        request_headers = {"Accept": "application/json, */*"}
        if headers:
            request_headers.update(headers)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=request_headers,
                auth=self._get_auth(),
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                stream=stream,
                **kwargs
            )
            
            if response.status_code == 401:
                raise ISAPIAuthError("Authentication failed - check credentials", 401, response)
            elif response.status_code >= 500:
                raise ISAPIConnectionError(f"Server error: {response.status_code}", response.status_code, response)
            
            return response
            
        except requests.exceptions.Timeout as e:
            raise ISAPIConnectionError(f"Request timeout: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ISAPIConnectionError(f"Connection error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise ISAPIError(f"Request failed: {e}") from e
    
    def _get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        return self._request("GET", endpoint, params=params, **kwargs)
    
    def _post(self, endpoint: str, data: Any = None, json: Dict = None, **kwargs) -> requests.Response:
        return self._request("POST", endpoint, data=data, json=json, **kwargs)
    
    def _put(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        return self._request("PUT", endpoint, data=data, **kwargs)
    
    def _delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self._request("DELETE", endpoint, **kwargs)
    
    # ==================== Device Info ====================
    
    def get_device_info(self, force_refresh: bool = False) -> DeviceInfo:
        """Get device information from /ISAPI/System/deviceInfo"""
        if self._device_info and not force_refresh:
            return self._device_info
        
        response = self._get("System/deviceInfo")
        response.raise_for_status()
        
        # ISAPI returns XML, parse it
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # Convert XML to dict
        data = {}
        for elem in root.iter():
            if elem.text and elem.text.strip():
                tag = elem.tag.split("}")[-1]  # Remove namespace
                data[tag] = elem.text.strip()
        
        self._device_info = DeviceInfo(**data)
        return self._device_info
    
    def get_capabilities(self, force_refresh: bool = False) -> Capability:
        """Get device capabilities from /ISAPI/System/capabilities"""
        if self._capabilities and not force_refresh:
            return self._capabilities
        
        response = self._get("System/capabilities")
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        data = {}
        for elem in root.iter():
            if elem.text and elem.text.strip():
                tag = elem.tag.split("}")[-1]
                data[tag] = elem.text.strip()
        
        self._capabilities = Capability(**data)
        return self._capabilities
    
    # ==================== Recording Search ====================
    
    def search_recordings(self, criteria: SearchCriteria) -> RecordingList:
        """Search for recordings matching criteria"""
        params = criteria.to_isapi_params()
        response = self._get("ContentMgmt/recordings", params=params)
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        recordings = []
        for recording_elem in root.findall(".//recording") or root.findall(".//Recording"):
            rec_data = {}
            for child in recording_elem:
                tag = child.tag.split("}")[-1]
                rec_data[tag] = child.text.strip() if child.text else ""
            
            if rec_data:
                try:
                    recordings.append(RecordingInfo(**rec_data))
                except Exception as e:
                    logger.warning(f"Failed to parse recording: {e}")
        
        total = 0
        for total_elem in root.findall(".//totalMatches") or root.findall(".//total"):
            try:
                total = int(total_elem.text or 0)
                break
            except ValueError:
                pass
        
        return RecordingList(
            recordings=recordings,
            total_matches=total,
            page_size=criteria.page_size,
            page_number=criteria.page_number,
        )
    
    def search_all_recordings(self, criteria: SearchCriteria) -> Iterator[RecordingInfo]:
        """Iterate through ALL matching recordings (handles pagination)"""
        current_page = criteria.page_number
        while True:
            criteria.page_number = current_page
            result = self.search_recordings(criteria)
            
            for rec in result.recordings:
                yield rec
            
            if not result.has_more:
                break
            current_page += 1
    
    # ==================== Download ====================
    
    def get_download_url(self, recording: RecordingInfo) -> str:
        """Get direct download URL for a recording"""
        if recording.download_url:
            return recording.download_url
        
        # Construct standard ISAPI download URL
        return urljoin(self.config.isapi_base, f"ContentMgmt/download/{recording.id}")
    
    def download_recording(
        self,
        recording: RecordingInfo,
        output_path: str,
        progress_callback: Optional[callable] = None,
        chunk_size: int = 8192,
        resume: bool = True,
    ) -> DownloadProgress:
        """
        Download a recording with progress tracking and resume support.
        
        Args:
            recording: RecordingInfo object
            output_path: Local file path to save
            progress_callback: Optional callback(progress: DownloadProgress)
            chunk_size: Download chunk size in bytes
            resume: Whether to resume partial downloads
        """
        import os
        from pathlib import Path
        
        url = self.get_download_url(recording)
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check for existing partial download
        existing_size = 0
        if resume and output_file.exists():
            existing_size = output_file.stat().st_size
        
        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"
        
        progress = DownloadProgress(
            recording_id=recording.id,
            file_name=output_file.name,
            total_bytes=recording.file_size or 0,
            downloaded_bytes=existing_size,
        )
        
        mode = "ab" if existing_size > 0 else "wb"
        
        try:
            response = self._get(url, headers=headers, stream=True)
            
            if response.status_code == 416:  # Range not satisfiable
                # File already complete
                progress.status = "completed"
                progress.downloaded_bytes = recording.file_size or existing_size
                if progress_callback:
                    progress_callback(progress)
                return progress
            
            response.raise_for_status()
            
            total_size = recording.file_size or int(response.headers.get("Content-Length", 0))
            if total_size > 0:
                progress.total_bytes = total_size + existing_size
            
            progress.status = "downloading"
            start_time = time.time()
            last_update = start_time
            last_bytes = existing_size
            
            with open(output_file, mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    
                    f.write(chunk)
                    progress.downloaded_bytes += len(chunk)
                    
                    now = time.time()
                    if now - last_update >= 0.5:  # Update every 500ms
                        elapsed = now - start_time
                        recent_bytes = progress.downloaded_bytes - last_bytes
                        progress.speed_bps = recent_bytes / (now - last_update) if now > last_update else 0
                        progress.last_update = now
                        last_update = now
                        last_bytes = progress.downloaded_bytes
                        
                        if progress.speed_bps > 0 and progress.total_bytes > 0:
                            remaining = progress.total_bytes - progress.downloaded_bytes
                            progress.eta_seconds = remaining / progress.speed_bps
                        
                        if progress_callback:
                            progress_callback(progress)
            
            progress.status = "completed"
            progress.eta_seconds = 0
            if progress_callback:
                progress_callback(progress)
            
            return progress
            
        except Exception as e:
            progress.status = "failed"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            raise
    
    def download_multiple(
        self,
        recordings: List[RecordingInfo],
        output_dir: str,
        progress_callback: Optional[callable] = None,
        max_concurrent: int = 1,
    ) -> List[DownloadProgress]:
        """Download multiple recordings sequentially"""
        from pathlib import Path
        results = []
        
        for i, recording in enumerate(recordings):
            file_name = f"{recording.start_time.strftime('%Y%m%d_%H%M%S')}_{recording.name}.mp4"
            output_path = Path(output_dir) / file_name
            
            def make_callback(idx):
                def cb(prog: DownloadProgress):
                    if progress_callback:
                        prog.file_name = f"[{idx+1}/{len(recordings)}] {prog.file_name}"
                        progress_callback(prog)
                return cb
            
            try:
                prog = self.download_recording(recording, str(output_path), make_callback(i))
                results.append(prog)
            except Exception as e:
                prog = DownloadProgress(
                    recording_id=recording.id,
                    file_name=file_name,
                    total_bytes=recording.file_size or 0,
                    status="failed",
                    error=str(e)
                )
                results.append(prog)
                if progress_callback:
                    progress_callback(prog)
        
        return results
    
    # ==================== Streaming ====================
    
    def get_rtsp_url(self, channel: int, stream_type: str = "main") -> str:
        """Generate RTSP URL for live streaming"""
        stream_map = {"main": "1", "sub": "2", "trans": "3"}
        stream_id = stream_map.get(stream_type, "1")
        return f"rtsp://{self.config.username}:{self.config.password}@{self.config.host}:554/Streaming/Channels/{channel}{stream_id}"
    
    def get_playback_rtsp_url(self, channel: int, start_time: str, end_time: str, stream_type: str = "main") -> str:
        """Generate RTSP URL for playback"""
        stream_map = {"main": "1", "sub": "2", "trans": "3"}
        stream_id = stream_map.get(stream_type, "1")
        # Format: rtsp://user:pass@host:554/playback?channel=1&starttime=...&endtime=...
        return (
            f"rtsp://{self.config.username}:{self.config.password}@{self.config.host}:554/"
            f"playback?channel={channel}&streamtype={stream_id}&starttime={start_time}&endtime={end_time}"
        )
    
    # ==================== PTZ (if supported) ====================
    
    def ptz_control(self, channel: int, command: str, speed: int = 5) -> bool:
        """Control PTZ: up, down, left, right, zoom_in, zoom_out, stop"""
        ptz_commands = {
            "up": "tiltUp",
            "down": "tiltDown",
            "left": "panLeft",
            "right": "panRight",
            "zoom_in": "zoomIn",
            "zoom_out": "zoomOut",
            "stop": "stop",
        }
        
        if command not in ptz_commands:
            raise ValueError(f"Unknown PTZ command: {command}")
        
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<PTZData>
    <pan>{0 if 'pan' not in command else (1 if 'right' in command else -1)}</pan>
    <tilt>{0 if 'tilt' not in command else (1 if 'up' in command else -1)}</tilt>
    <zoom>{0 if 'zoom' not in command else (1 if 'in' in command else -1)}</zoom>
    <speed>{speed}</speed>
</PTZData>"""
        
        response = self._put(f"PTZCtrl/channels/{channel}/continuous", data=xml_data)
        return response.status_code in (200, 201, 204)
    
    def ptz_preset(self, channel: int, preset_id: int, action: str = "goto") -> bool:
        """Go to or set PTZ preset"""
        actions = {"goto": "goto", "set": "set", "clear": "clear"}
        if action not in actions:
            raise ValueError(f"Unknown preset action: {action}")
        
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<PTZPreset>
    <id>{preset_id}</id>
    <action>{actions[action]}</action>
</PTZPreset>"""
        
        response = self._put(f"PTZCtrl/channels/{channel}/presets/{preset_id}", data=xml_data)
        return response.status_code in (200, 201, 204)
    
    # ==================== Context Manager ====================
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    def close(self):
        self.session.close()