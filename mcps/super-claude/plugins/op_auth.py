"""
1Password Authentication Plugin

Provides secret retrieval and storage via 1Password.
Uses the core.secrets infrastructure layer.

Note: This plugin exposes infrastructure secrets as MCP tools.
For a full user-facing secrets service (account-based, domain-aware),
see services/secrets/ (planned).
"""

import sys
sys.path.insert(0, "/app")

from plugin_base import SuperClaudePlugin
from core.secrets import secrets_manager


class OnePasswordPlugin(SuperClaudePlugin):
    """1Password authentication and secret management plugin."""
    
    def initialize(self) -> None:
        """Initialize the 1Password plugin."""
        self.metadata = {
            "name": "onepassword",
            "version": "0.2.0",
            "description": "Authentication and secret management via 1Password",
            "author": "Matthew",
            "requires": ["1Password service account token"]
        }
        
        # Register tools
        self.tools = {
            "auth_get": self.auth_get,
            "auth_get_ref": self.auth_get_ref,
            "auth_set": self.auth_set,
        }
    
    async def auth_get(
        self,
        item_name: str,
        field: str = "credential",
        vault: str = "Key Vault"
    ) -> str:
        """
        Get a secret from 1Password.

        Args:
            item_name: Name of the item in 1Password (e.g., "GitHub PAT - Claude Code")
            field: Field name to retrieve (default: "credential")
            vault: Vault name (default: "Key Vault") - Note: uses configured backend's vault

        Returns:
            The secret value, or error message if retrieval fails
        """
        try:
            # Use the infrastructure secrets manager
            # Note: vault parameter is informational - actual vault comes from backend config
            return await secrets_manager.get(item_name, field)
        except KeyError as e:
            return f"❌ Secret not found: {e}"
        except Exception as e:
            return f"❌ Error retrieving secret: {e}"
    
    async def auth_get_ref(self, secret_ref: str) -> str:
        """
        Get a secret using a full 1Password secret reference.

        Args:
            secret_ref: Full secret reference URI (e.g., "op://Key Vault/GitHub PAT/credential")

        Returns:
            The secret value, or error message if retrieval fails
        """
        try:
            return await secrets_manager.get_ref(secret_ref)
        except KeyError as e:
            return f"❌ Secret not found: {e}"
        except ValueError as e:
            return f"❌ Invalid reference format: {e}"
        except Exception as e:
            return f"❌ Error retrieving secret: {e}"
    
    async def auth_set(
        self,
        title: str,
        fields: str,
        vault: str = "Key Vault",
        category: str = "api_credential",
        notes: str = ""
    ) -> str:
        """
        Create a new item in 1Password.

        Args:
            title: Item title (e.g., "Steam API Key")
            fields: JSON string of field names to values (e.g., '{"credential": "abc123", "steam_id": "12345"}')
            vault: Vault name (default: "Key Vault") - Note: uses configured backend's vault
            category: Item category (default: "api_credential").
                      Options: login, password, api_credential, secure_note
            notes: Optional notes field

        Returns:
            Success message with item ID, or error message if creation fails
        """
        try:
            import json as json_module
            fields_dict = json_module.loads(fields)
            
            result = await secrets_manager.set(
                title=title,
                fields=fields_dict,
                category=category,
                notes=notes if notes else None
            )
            
            return f"✅ Created item '{result.title}' with ID: {result.id}"
            
        except json_module.JSONDecodeError as e:
            return f"❌ Invalid JSON in fields: {e}"
        except Exception as e:
            return f"❌ Error creating item: {e}"
    
    def on_load(self) -> None:
        """Called when plugin loads."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin unloads."""
        pass
