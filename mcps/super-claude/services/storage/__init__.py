"""Storage Service - Cloud file storage abstraction."""

from .interface import (
    StorageAdapter,
    StorageAccount,
    FileInfo,
    FilePage,
)
from .manager import StorageManager
from .adapters.gdrive import GDriveAdapter

__all__ = [
    "StorageAdapter",
    "StorageAccount", 
    "FileInfo",
    "FilePage",
    "StorageManager",
    "GDriveAdapter",
]
