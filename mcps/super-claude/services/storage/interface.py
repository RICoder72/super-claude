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


@dataclass
class FileInfo:
    """Information about a remote file."""
    name: str
    path: str
    size: int
    modified: Optional[datetime] = None
    is_directory: bool = False
    mime_type: Optional[str] = None
    id: Optional[str] = None
    provider: str = ""
    account: str = ""


@dataclass
class FilePage:
    """Paginated file listing results."""
    files: List[FileInfo]
    next_cursor: Optional[str] = None


@dataclass
class StorageAccount:
    """A named storage account configuration."""
    name: str
    adapter: str
    credentials_ref: str
    config: Dict[str, Any] = field(default_factory=dict)


class StorageAdapter(ABC):
    """Base class for storage adapters."""
    
    adapter_type: str = "base"
    
    def __init__(self, account: StorageAccount):
        self.account = account
        self._client = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to storage service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage service."""
        pass
    
    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload a file to remote storage."""
        pass
    
    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> str:
        """Download a file from remote storage."""
        pass
    
    @abstractmethod
    async def delete(self, remote_path: str) -> str:
        """Delete a remote file."""
        pass
    
    @abstractmethod
    async def move(self, source_path: str, dest_path: str) -> str:
        """Move or rename a remote file."""
        pass
    
    @abstractmethod
    async def copy(self, source_path: str, dest_path: str) -> str:
        """Copy a remote file."""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        remote_path: str = "/",
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> FilePage:
        """List files at a remote path with cursor-based pagination."""
        pass
    
    @abstractmethod
    async def mkdir(self, remote_path: str) -> str:
        """Create a remote directory."""
        pass
    
    @abstractmethod
    async def rmdir(self, remote_path: str, recursive: bool = False) -> str:
        """Remove a remote directory."""
        pass
    
    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        """Check if a remote path exists."""
        pass
    
    @abstractmethod
    async def get_info(self, remote_path: str) -> Optional[FileInfo]:
        """Get info about a specific file."""
        pass
    
    async def search(
        self,
        query: str,
        path: Optional[str] = None,
        limit: int = 50
    ) -> List[FileInfo]:
        """Search for files. Override if provider supports it."""
        return []
