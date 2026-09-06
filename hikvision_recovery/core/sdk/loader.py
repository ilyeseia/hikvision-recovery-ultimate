"""
Dynamic library loader for Hikvision HCNetSDK.
Supports Linux x64 and ARM64, automatic library discovery.
"""

import os
import sys
import platform
import ctypes
import ctypes.util
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .exceptions import SDKLoadError, get_error_message

logger = logging.getLogger(__name__)


@dataclass
class LibraryInfo:
    """Information about a loaded SDK library."""
    name: str
    path: str
    version: Optional[str] = None
    architecture: Optional[str] = None
    handle: Optional[ctypes.CDLL] = None


class SDKLibraryLoader:
    """
    Loads Hikvision HCNetSDK shared libraries.
    
    Supports:
    - Linux x86_64 (libhcnetsdk.so, libHCCore.so, etc.)
    - Linux ARM64/aarch64
    - Custom library paths via environment variables
    """
    
    # Core library names (in load order - dependencies first)
    LIBRARY_NAMES = [
        "hcnetsdk",           # Main SDK library
        "hccore",             # Core library (dependency)
        "hcplaym4",           # Playback library
        "hcnetsdkplay",       # Playback SDK
        "hcconfig",           # Configuration library
    ]
    
    # Optional libraries
    OPTIONAL_LIBRARIES = [
        "hcvoice",            # Voice talk
        "hcvideoconfig",      # Video config
        "hcremoteconfig",     # Remote config
        "hcdecode",           # Decode
    ]
    
    def __init__(
        self,
        custom_paths: Optional[List[str]] = None,
        required_only: bool = True,
    ):
        """
        Initialize loader.
        
        Args:
            custom_paths: Additional directories to search for libraries
            required_only: If True, only load required libraries
        """
        self.custom_paths = custom_paths or []
        self.required_only = required_only
        self.loaded_libraries: Dict[str, LibraryInfo] = {}
        self._system_lib_dirs = self._get_system_library_dirs()
        
    def _get_system_library_dirs(self) -> List[Path]:
        """Get standard system library directories."""
        dirs = []
        
        # Standard Linux library paths
        dirs.extend([
            Path("/usr/lib"),
            Path("/usr/lib64"),
            Path("/usr/local/lib"),
            Path("/usr/local/lib64"),
            Path("/opt/hikvision/lib"),
            Path("/opt/hikvision/SDK/lib"),
            Path("/home/nonbios/hikvision_sdk/lib"),
        ])
        
        # Architecture-specific paths
        arch = platform.machine().lower()
        if arch in ("x86_64", "amd64"):
            dirs.extend([
                Path("/usr/lib/x86_64-linux-gnu"),
                Path("/usr/lib64"),
            ])
        elif arch in ("aarch64", "arm64"):
            dirs.extend([
                Path("/usr/lib/aarch64-linux-gnu"),
                Path("/usr/lib/arm64"),
            ])
        
        # LD_LIBRARY_PATH
        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        for p in ld_path.split(":"):
            if p:
                dirs.append(Path(p))
        
        # Custom paths from user
        for p in self.custom_paths:
            dirs.append(Path(p))
        
        # Deduplicate while preserving order
        seen = set()
        unique_dirs = []
        for d in dirs:
            try:
                resolved = d.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    unique_dirs.append(resolved)
            except Exception:
                pass
        
        return unique_dirs
    
    def find_library(self, name: str) -> Optional[Path]:
        """
        Find a library file by name.
        
        Searches in order:
        1. Custom paths
        2. System library directories
        3. ctypes.util.find_library (ldconfig cache)
        4. Common SDK installation paths
        """
        # Try different naming patterns
        patterns = [
            f"lib{name}.so",
            f"lib{name}.so.*",  # versioned
            f"{name}.so",
        ]
        
        for lib_dir in self._system_lib_dirs:
            if not lib_dir.exists():
                continue
            for pattern in patterns:
                matches = list(lib_dir.glob(pattern))
                if matches:
                    # Prefer non-versioned, then highest version
                    for m in matches:
                        if m.name == f"lib{name}.so":
                            return m
                    return matches[0]
        
        # Try ctypes.util.find_library
        found = ctypes.util.find_library(name)
        if found:
            return Path(found)
        
        return None
    
    def load_library(self, name: str, required: bool = True) -> Optional[LibraryInfo]:
        """
        Load a single library by name.
        
        Args:
            name: Library name (e.g., "hcnetsdk")
            required: If True, raise on failure
            
        Returns:
            LibraryInfo if loaded, None if optional and not found
        """
        if name in self.loaded_libraries:
            return self.loaded_libraries[name]
        
        lib_path = self.find_library(name)
        if not lib_path:
            msg = f"Library not found: {name}"
            if required:
                raise SDKLoadError(msg)
            logger.warning(msg)
            return None
        
        try:
            # Load with RTLD_GLOBAL to make symbols available to dependent libraries
            handle = ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
            
            info = LibraryInfo(
                name=name,
                path=str(lib_path),
                handle=handle,
            )
            
            # Try to get version if available
            info.version = self._get_library_version(handle, name)
            info.architecture = platform.machine()
            
            self.loaded_libraries[name] = info
            logger.info(f"Loaded {name} from {lib_path}")
            return info
            
        except OSError as e:
            msg = f"Failed to load {name} from {lib_path}: {e}"
            if required:
                raise SDKLoadError(msg) from e
            logger.warning(msg)
            return None
    
    def _get_library_version(self, handle: ctypes.CDLL, name: str) -> Optional[str]:
        """Try to extract version from library."""
        # Common version symbol names
        version_symbols = [
            "HCNetSDK_GetVersion",
            "NET_DVR_GetSDKVersion",
            "HCCore_GetVersion",
            "HCPlayM4_GetVersion",
        ]
        
        for sym in version_symbols:
            try:
                func = getattr(handle, sym)
                func.restype = ctypes.c_uint32
                version_num = func()
                # Convert version number to string (e.g., 0x04000000 -> "4.0.0.0")
                major = (version_num >> 24) & 0xFF
                minor = (version_num >> 16) & 0xFF
                patch = (version_num >> 8) & 0xFF
                build = version_num & 0xFF
                return f"{major}.{minor}.{patch}.{build}"
            except (AttributeError, OSError):
                continue
        
        return None
    
    def load_all(self) -> Dict[str, LibraryInfo]:
        """
        Load all required libraries in dependency order.
        
        Returns:
            Dictionary of loaded libraries
        """
        # Load required libraries first
        for name in self.LIBRARY_NAMES:
            self.load_library(name, required=True)
        
        # Load optional libraries
        if not self.required_only:
            for name in self.OPTIONAL_LIBRARIES:
                self.load_library(name, required=False)
        
        return self.loaded_libraries
    
    def get_library(self, name: str) -> Optional[ctypes.CDLL]:
        """Get loaded library handle."""
        info = self.loaded_libraries.get(name)
        return info.handle if info else None
    
    def get_main_sdk(self) -> ctypes.CDLL:
        """Get main HCNetSDK handle (required)."""
        handle = self.get_library("hcnetsdk")
        if not handle:
            raise SDKLoadError("Main HCNetSDK library not loaded")
        return handle
    
    def get_playback_sdk(self) -> Optional[ctypes.CDLL]:
        """Get playback library handle (optional)."""
        return self.get_library("hcplaym4") or self.get_library("hcnetsdkplay")
    
    def unload_all(self):
        """Unload all libraries (Linux: dlclose via _handle)."""
        for info in self.loaded_libraries.values():
            if info.handle and hasattr(info.handle, "_handle"):
                try:
                    ctypes.CDLL(None).dlclose(info.handle._handle)
                except Exception:
                    pass
        self.loaded_libraries.clear()
    
    def __enter__(self):
        self.load_all()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload_all()
    
    @property
    def is_loaded(self) -> bool:
        """Check if main SDK is loaded."""
        return "hcnetsdk" in self.loaded_libraries


def create_loader(
    sdk_path: Optional[str] = None,
    required_only: bool = True,
) -> SDKLibraryLoader:
    """
    Factory function to create and initialize loader.
    
    Args:
        sdk_path: Custom SDK installation path
        required_only: Only load required libraries
        
    Returns:
        Initialized SDKLibraryLoader
    """
    custom_paths = []
    if sdk_path:
        custom_paths.append(sdk_path)
        custom_paths.append(os.path.join(sdk_path, "lib"))
        custom_paths.append(os.path.join(sdk_path, "Lib"))
    
    # Check environment variable
    env_path = os.environ.get("HIKVISION_SDK_PATH")
    if env_path:
        custom_paths.insert(0, env_path)
    
    loader = SDKLibraryLoader(custom_paths=custom_paths, required_only=required_only)
    return loader