"""
Storage Service Interface

Core abstraction for cloud storage providers. Adapters implement this interface
to provide storage functionality for Google Drive, OneDrive, Dropbox, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FileInfo:
    """Information about a remote file."""
    name: str
    path: str                          # Full remote path
    size: int                          # Size in bytes
    modified: Optional[datetime] = None  # Timezone-aware UTC
    is_directory: bool = False
    mime_type: Optional[str] = None
    
    # Provider metadata
    id: Optional[str] = None           # Provider-specific file ID
    provider: str = ""
    account: str = ""


@dataclass
class FilePage:
    """Paginated file listing results."""
    files: List[FileInfo]
    next_cursor: Optional[str] = None  # None means no more pages


@dataclass
class StorageAccount:
    """A named storage account configuration."""
    name: str             # User-defined label: "work", "personal"
    adapter: str          # Adapter type: "gdrive", "onedrive", "dropbox"
    credentials_ref: str  # 1Password reference
    config: Dict[str, Any] = field(default_factory=dict)  # Adapter-specific config
    
    # Common config options:
    # - root_path: Base path to use as root (e.g., "/SuperClaude")


# =============================================================================
# Adapter Interface
# =============================================================================

class StorageAdapter(ABC):
    """
    Base class for storage adapters.
    
    Each adapter (Google Drive, OneDrive, etc.) implements this interface.
    """
    
    adapter_type: str = "base"  # Override in subclass: "gdrive", "onedrive", "dropbox"
    
    def __init__(self, account: StorageAccount):
        """
        Initialize adapter with account config.
        
        Args:
            account: StorageAccount with credentials and config
        """
        self.account = account
        self._client = None
    
    # =========================================================================
    # Connection
    # =========================================================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to storage service.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage service."""
        pass
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> str:
        """
        Upload a file to remote storage.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> str:
        """
        Download a file from remote storage.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def delete(self, remote_path: str) -> str:
        """
        Delete a remote file.
        
        Args:
            remote_path: Remote file path
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def move(self, source_path: str, dest_path: str) -> str:
        """
        Move or rename a remote file.
        
        Args:
            source_path: Current remote path
            dest_path: New remote path
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def copy(self, source_path: str, dest_path: str) -> str:
        """
        Copy a remote file.
        
        Args:
            source_path: Source remote path
            dest_path: Destination remote path
        
        Returns:
            Success message or error
        """
        pass
    
    # =========================================================================
    # Directory Operations
    # =========================================================================
    
    @abstractmethod
    async def list_files(
        self,
        remote_path: str = "/",
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> FilePage:
        """
        List files at a remote path with cursor-based pagination.
        
        Args:
            remote_path: Remote directory path
            limit: Maximum files to return
            cursor: Pagination cursor from previous FilePage.next_cursor
        
        Returns:
            FilePage with files and optional next_cursor
        """
        pass
    
    @abstractmethod
    async def mkdir(self, remote_path: str) -> str:
        """
        Create a remote directory.
        
        Creates parent directories if needed.
        
        Args:
            remote_path: Remote directory path
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def rmdir(self, remote_path: str, recursive: bool = False) -> str:
        """
        Remove a remote directory.
        
        Args:
            remote_path: Remote directory path
            recursive: If True, delete contents; if False, fail if not empty
        
        Returns:
            Success message or error
        """
        pass
    
    # =========================================================================
    # Metadata
    # =========================================================================
    
    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """
        Check if a remote path exists.
        
        Args:
            remote_path: Remote file/directory path
        
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    async def get_info(self, remote_path: str) -> Optional[FileInfo]:
        """
        Get info about a specific file.
        
        Args:
            remote_path: Remote file path
        
        Returns:
            FileInfo or None if not found
        """
        pass
    
    # =========================================================================
    # Search (Optional)
    # =========================================================================
    
    async def search(
        self,
        query: str,
        path: Optional[str] = None,
        limit: int = 50
    ) -> List[FileInfo]:
        """
        Search for files. Override if provider supports it.
        
        Args:
            query: Search text (filename, content - provider dependent)
            path: Optional path to search within
            limit: Maximum results
        
        Returns:
            List of matching FileInfo
        """
        return []  # Default: search not supported
