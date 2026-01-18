"""
Super Claude Core

Core abstractions and interfaces.

Infrastructure:
- secrets: Internal secrets management (not exposed as tools)

Legacy (to be migrated to services/):
- storage_interface, storage_manager: Being moved to services/storage/
"""

from .storage_interface import StorageProvider, StorageAccount, FileInfo
from .storage_manager import StorageManager

# Infrastructure secrets (internal, not exposed as MCP tools)
from .secrets import secrets_manager, SecretsBackend, SecretItem

__all__ = [
    # Legacy storage (to be migrated)
    "StorageProvider",
    "StorageAccount", 
    "FileInfo",
    "StorageManager",
    # Infrastructure secrets
    "secrets_manager",
    "SecretsBackend",
    "SecretItem",
]
