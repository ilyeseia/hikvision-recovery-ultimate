"""
Utility functions for Hikvision Recovery.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path


def parse_hikvision_datetime(dt_str: str) -> Optional[datetime]:
    """Parse Hikvision datetime strings"""
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%dT%H%M%SZ",
        "%Y%m%d%H%M%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def format_hikvision_datetime(dt: datetime, with_timezone: bool = False) -> str:
    """Format datetime for Hikvision ISAPI"""
    if with_timezone:
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize filename for filesystem"""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Remove leading/trailing dots and spaces
    name = name.strip(". ")
    # Truncate
    if len(name) > max_length:
        name = name[:max_length]
    return name or "unnamed"


def human_readable_size(size_bytes: int) -> str:
    """Format bytes as human readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024 or unit == "TB":
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def human_readable_duration(seconds: float) -> str:
    """Format seconds as human readable duration"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def validate_ip(ip: str) -> bool:
    """Validate IP address"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_host(host: str) -> bool:
    """Validate hostname or IP"""
    if validate_ip(host):
        return True
    # Simple hostname validation
    if len(host) > 253:
        return False
    if host[-1] == ".":
        host = host[:-1]
    allowed = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
    return all(allowed.match(part) for part in host.split("."))


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)
    return path


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_per_second: float = 10):
        self.min_interval = 1.0 / max_per_second
        self.last_call = 0.0
    
    def wait(self):
        import time
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


def parse_camera_list(camera_str: str) -> list[int]:
    """Parse comma-separated camera list: '1,2,5-8' -> [1,2,5,6,7,8]"""
    result = []
    for part in camera_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            try:
                result.extend(range(int(start), int(end) + 1))
            except ValueError:
                pass
        else:
            try:
                result.append(int(part))
            except ValueError:
                pass
    return sorted(set(result))