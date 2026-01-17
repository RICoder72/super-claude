"""
Super Claude Core

Core abstractions and interfaces for the plugin system.
"""

from .storage_interface import StorageProvider, StorageAccount, FileInfo
from .storage_manager import StorageManager

__all__ = [
    "StorageProvider",
    "StorageAccount", 
    "FileInfo",
    "StorageManager"
]
