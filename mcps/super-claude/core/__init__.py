"""
Super Claude Core

Core abstractions and interfaces.

Infrastructure:
- secrets: Internal secrets management (not exposed as tools)

Legacy (to be migrated to services/):
- storage_interface, storage_manager: Being moved to services/storage/
"""

import logging

logger = logging.getLogger(__name__)

# Infrastructure secrets (internal, not exposed as MCP tools)
# Import these unconditionally as they're needed by plugins
try:
    from .secrets import secrets_manager, SecretsBackend, SecretItem
    SECRETS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Secrets module unavailable: {e}")
    secrets_manager = None
    SecretsBackend = None
    SecretItem = None
    SECRETS_AVAILABLE = False

# Legacy storage (to be migrated) - import lazily/optionally
# These are imported by server.py directly when needed
_storage_loaded = False
StorageProvider = None
StorageAccount = None
FileInfo = None
StorageManager = None

def _load_storage():
    """Lazily load storage components."""
    global _storage_loaded, StorageProvider, StorageAccount, FileInfo, StorageManager
    if _storage_loaded:
        return
    try:
        from .storage_interface import StorageProvider as SP, StorageAccount as SA, FileInfo as FI
        from .storage_manager import StorageManager as SM
        StorageProvider = SP
        StorageAccount = SA
        FileInfo = FI
        StorageManager = SM
        _storage_loaded = True
    except ImportError as e:
        logger.warning(f"Storage module unavailable: {e}")
        _storage_loaded = True  # Don't retry


__all__ = [
    # Infrastructure secrets
    "secrets_manager",
    "SecretsBackend",
    "SecretItem",
    "SECRETS_AVAILABLE",
    # Legacy storage (lazy loaded)
    "StorageProvider",
    "StorageAccount", 
    "FileInfo",
    "StorageManager",
    "_load_storage",
]
