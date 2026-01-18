"""
1Password Secrets Backend

Implements SecretsBackend for 1Password using the official SDK.
"""

import os
import logging
from typing import Optional, Dict, List

from ..interface import SecretsBackend, SecretItem

logger = logging.getLogger(__name__)


class OnePasswordBackend(SecretsBackend):
    """
    1Password secrets backend.
    
    Config:
        vault: Default vault name (required)
        service_account_env: Environment variable name for service account token
                            (default: "OP_SERVICE_ACCOUNT_TOKEN")
    """
    
    backend_type = "onepassword"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.vault = config.get("vault", "Key Vault")
        self.service_account_env = config.get("service_account_env", "OP_SERVICE_ACCOUNT_TOKEN")
        self._client = None
        self._vault_id = None
    
    async def connect(self) -> bool:
        """Initialize 1Password client."""
        try:
            from onepassword.client import Client
            
            token = os.getenv(self.service_account_env)
            if not token:
                logger.error(f"Environment variable {self.service_account_env} not set")
                return False
            
            self._client = await Client.authenticate(
                auth=token,
                integration_name="Super Claude",
                integration_version="v1.0.0"
            )
            
            # Cache vault ID
            vaults = await self._client.vaults.list()
            for v in vaults:
                if v.title.lower() == self.vault.lower():
                    self._vault_id = v.id
                    break
            
            if not self._vault_id:
                logger.warning(f"Vault '{self.vault}' not found, some operations may fail")
            
            logger.info(f"✅ Connected to 1Password vault: {self.vault}")
            return True
            
        except ImportError:
            logger.error("❌ 1Password SDK not installed: pip install onepassword-sdk")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to 1Password: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from 1Password."""
        self._client = None
        self._vault_id = None
    
    async def _ensure_connected(self):
        """Ensure we're connected, auto-connect if not."""
        if self._client is None:
            if not await self.connect():
                raise ConnectionError("Failed to connect to 1Password")
    
    async def get(self, item: str, field: str = "credential") -> str:
        """Get a secret from 1Password."""
        await self._ensure_connected()
        
        secret_ref = f"op://{self.vault}/{item}/{field}"
        try:
            return await self._client.secrets.resolve(secret_ref)
        except Exception as e:
            raise KeyError(f"Secret not found: {item}/{field} in {self.vault}: {e}")
    
    async def get_ref(self, reference: str) -> str:
        """Get a secret using full op:// reference."""
        await self._ensure_connected()
        
        if not reference.startswith("op://"):
            raise ValueError(f"Invalid 1Password reference format: {reference}")
        
        try:
            return await self._client.secrets.resolve(reference)
        except Exception as e:
            raise KeyError(f"Secret reference not found: {reference}: {e}")
    
    async def set(
        self,
        title: str,
        fields: Dict[str, str],
        category: str = "api_credential",
        notes: Optional[str] = None
    ) -> SecretItem:
        """Create a secret in 1Password."""
        await self._ensure_connected()
        
        from onepassword.types import ItemCreateParams, ItemField, ItemFieldType, ItemCategory
        
        if not self._vault_id:
            raise ConnectionError(f"Vault '{self.vault}' not found")
        
        # Map category string to enum
        category_map = {
            "login": ItemCategory.LOGIN,
            "password": ItemCategory.PASSWORD,
            "api_credential": ItemCategory.APICREDENTIALS,
            "secure_note": ItemCategory.SECURENOTE,
        }
        item_category = category_map.get(category.lower(), ItemCategory.APICREDENTIALS)
        
        # Build fields list
        item_fields = []
        for field_name, field_value in fields.items():
            # Sensitive field names get concealed type
            if field_name.lower() in ("credential", "password", "secret", "api_key", "token", "key"):
                field_type = ItemFieldType.CONCEALED
            else:
                field_type = ItemFieldType.TEXT
            
            item_fields.append(ItemField(
                id=field_name.lower().replace(" ", "_"),
                title=field_name,
                value=field_value,
                field_type=field_type
            ))
        
        # Create item
        item_params = ItemCreateParams(
            title=title,
            category=item_category,
            vault_id=self._vault_id,
            fields=item_fields,
            notes=notes if notes else None
        )
        
        created = await self._client.items.create(item_params)
        
        return SecretItem(
            id=created.id,
            title=title,
            vault=self.vault,
            category=category,
            fields=fields,
            notes=notes
        )
    
    async def delete(self, item: str) -> bool:
        """Delete a secret from 1Password."""
        await self._ensure_connected()
        
        # 1Password SDK doesn't have a simple delete by name
        # We'd need to list items, find by title, then delete by ID
        # For now, raise not implemented
        raise NotImplementedError("Delete not yet implemented for 1Password backend")
    
    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """List secret items in the vault."""
        await self._ensure_connected()
        
        if not self._vault_id:
            return []
        
        try:
            items = await self._client.items.list(self._vault_id)
            titles = [item.title for item in items]
            
            if prefix:
                titles = [t for t in titles if t.lower().startswith(prefix.lower())]
            
            return titles
        except Exception as e:
            logger.error(f"Failed to list items: {e}")
            return []
    
    async def exists(self, item: str) -> bool:
        """Check if an item exists in the vault."""
        await self._ensure_connected()
        
        try:
            # Try to resolve a common field - if it works, item exists
            await self.get(item, "credential")
            return True
        except KeyError:
            # Try with 'password' field as fallback
            try:
                await self.get(item, "password")
                return True
            except KeyError:
                return False
        except Exception:
            return False
