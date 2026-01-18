"""
Infrastructure Secrets Module

Provides internal access to secrets for service adapters.
NOT exposed as MCP tools - this is plumbing.

Usage:
    from core.secrets import secrets_manager
    
    # Get a secret from default backend
    token = await secrets_manager.get("GitHub PAT")
    
    # Get from specific backend  
    token = await secrets_manager.get("Work Credentials", backend="work")
    
    # Get using full reference
    token = await secrets_manager.get_ref("op://Vault/Item/field")

Configuration:
    Backends are configured in /data/config/secrets_backends.json:
    
    {
        "backends": {
            "personal": {
                "adapter": "onepassword",
                "vault": "Key Vault",
                "service_account_env": "OP_SERVICE_ACCOUNT_TOKEN"
            },
            "work": {
                "adapter": "onepassword",
                "vault": "Burrillville",
                "service_account_env": "OP_WORK_SERVICE_ACCOUNT_TOKEN"
            }
        },
        "default_backend": "personal"
    }
"""

from .interface import SecretsBackend, SecretItem
from .manager import secrets_manager, SecretsManager

__all__ = [
    "secrets_manager",
    "SecretsManager", 
    "SecretsBackend",
    "SecretItem",
]
