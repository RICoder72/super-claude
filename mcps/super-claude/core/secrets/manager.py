"""
Infrastructure Secrets Manager

Singleton manager for infrastructure secrets.
Loads backend configuration and provides unified access.

Usage:
    from core.secrets import secrets_manager
    
    # Get a secret from the default backend
    token = await secrets_manager.get("GitHub PAT")
    
    # Get from a specific backend
    token = await secrets_manager.get("Work API Key", backend="work")
    
    # Get using full reference
    token = await secrets_manager.get_ref("op://Burrillville/Google Workspace/oauth_token")
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

from .interface import SecretsBackend, SecretItem
from .backends import BACKENDS

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/data/config/secrets_backends.json")

# Default configuration if no config file exists
DEFAULT_CONFIG = {
    "backends": {
        "default": {
            "adapter": "onepassword",
            "vault": "Key Vault",
            "service_account_env": "OP_SERVICE_ACCOUNT_TOKEN"
        }
    },
    "default_backend": "default"
}


class SecretsManager:
    """
    Manages infrastructure secrets backends.
    
    This is internal plumbing - not exposed as MCP tools.
    Service adapters use this to get their credentials.
    """
    
    def __init__(self):
        self._config: Dict = {}
        self._backends: Dict[str, SecretsBackend] = {}
        self._default_backend: str = "default"
        self._loaded = False
    
    def _load_config(self) -> None:
        """Load backend configuration from file."""
        if self._loaded:
            return
        
        try:
            if CONFIG_PATH.exists():
                self._config = json.loads(CONFIG_PATH.read_text())
                logger.info(f"Loaded secrets config from {CONFIG_PATH}")
            else:
                self._config = DEFAULT_CONFIG
                logger.info("Using default secrets configuration")
            
            self._default_backend = self._config.get("default_backend", "default")
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load secrets config: {e}")
            self._config = DEFAULT_CONFIG
            self._loaded = True
    
    def _get_backend(self, name: str) -> SecretsBackend:
        """Get or create a backend instance."""
        self._load_config()
        
        if name in self._backends:
            return self._backends[name]
        
        backend_config = self._config.get("backends", {}).get(name)
        if not backend_config:
            raise KeyError(f"Unknown secrets backend: {name}")
        
        adapter_type = backend_config.get("adapter", "onepassword")
        if adapter_type not in BACKENDS:
            raise ValueError(f"Unknown backend adapter type: {adapter_type}")
        
        backend_class = BACKENDS[adapter_type]
        backend = backend_class(backend_config)
        self._backends[name] = backend
        
        return backend
    
    async def get(
        self,
        item: str,
        field: str = "credential",
        backend: Optional[str] = None
    ) -> str:
        """
        Get a secret value.
        
        Args:
            item: Item name
            field: Field name (default: "credential")
            backend: Backend name (default: use default_backend from config)
        
        Returns:
            The secret value
        """
        backend_name = backend or self._default_backend
        backend_instance = self._get_backend(backend_name)
        return await backend_instance.get(item, field)
    
    async def get_ref(self, reference: str, backend: Optional[str] = None) -> str:
        """
        Get a secret using a provider-specific reference.
        
        Args:
            reference: Full reference URI (e.g., "op://vault/item/field")
            backend: Backend name (optional - will try to infer from reference)
        
        Returns:
            The secret value
        """
        # Try to infer backend from reference format
        if backend is None:
            if reference.startswith("op://"):
                # 1Password reference - find a 1password backend
                self._load_config()
                for name, config in self._config.get("backends", {}).items():
                    if config.get("adapter") in ("onepassword", "1password"):
                        backend = name
                        break
        
        backend_name = backend or self._default_backend
        backend_instance = self._get_backend(backend_name)
        return await backend_instance.get_ref(reference)
    
    async def set(
        self,
        title: str,
        fields: Dict[str, str],
        category: str = "api_credential",
        notes: Optional[str] = None,
        backend: Optional[str] = None
    ) -> SecretItem:
        """
        Create a secret.
        
        Args:
            title: Item title
            fields: Dict of field names to values
            category: Item category
            notes: Optional notes
            backend: Backend name (default: use default_backend)
        
        Returns:
            Created SecretItem
        """
        backend_name = backend or self._default_backend
        backend_instance = self._get_backend(backend_name)
        return await backend_instance.set(title, fields, category, notes)
    
    async def list(
        self,
        prefix: Optional[str] = None,
        backend: Optional[str] = None
    ) -> list:
        """
        List secret items.
        
        Args:
            prefix: Optional prefix filter
            backend: Backend name (default: use default_backend)
        
        Returns:
            List of item names
        """
        backend_name = backend or self._default_backend
        backend_instance = self._get_backend(backend_name)
        return await backend_instance.list(prefix)
    
    async def exists(
        self,
        item: str,
        backend: Optional[str] = None
    ) -> bool:
        """
        Check if a secret exists.
        
        Args:
            item: Item name
            backend: Backend name (default: use default_backend)
        
        Returns:
            True if exists
        """
        backend_name = backend or self._default_backend
        backend_instance = self._get_backend(backend_name)
        return await backend_instance.exists(item)
    
    def list_backends(self) -> list:
        """List configured backend names."""
        self._load_config()
        return list(self._config.get("backends", {}).keys())
    
    def get_default_backend(self) -> str:
        """Get the default backend name."""
        self._load_config()
        return self._default_backend


# Singleton instance
secrets_manager = SecretsManager()
