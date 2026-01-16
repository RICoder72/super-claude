"""
Shared 1Password client for Claude MCPs.

Usage:
    from op_client import get_secret, get_secrets, create_item

    # Single secret
    token = await get_secret("GitHub PAT - Claude Code")
    
    # With custom field/vault
    api_key = await get_secret("Jira API Key", field="password", vault="Work")
    
    # Multiple secrets at once
    secrets = await get_secrets([
        "op://Key Vault/GitHub PAT - Claude Code/credential",
        "op://Key Vault/Some Other Secret/password",
    ])
    
    # Create a new item
    await create_item(
        title="Steam API Key",
        fields={"credential": "abc123", "steam_id": "12345"},
        vault="Key Vault",
        category="api_credential"
    )
"""

import os
from onepassword.client import Client
from onepassword.types import ItemCreateParams, ItemField, ItemFieldType, ItemCategory

_client: Client | None = None

async def _get_client() -> Client:
    """Get or create authenticated 1Password client."""
    global _client
    if _client is None:
        token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
        if not token:
            raise ValueError("OP_SERVICE_ACCOUNT_TOKEN not set")
        _client = await Client.authenticate(
            auth=token,
            integration_name="Claude MCP",
            integration_version="v0.2.0"
        )
    return _client


async def get_secret(
    item_name: str,
    field: str = "credential",
    vault: str = "Key Vault"
) -> str:
    """
    Get a single secret from 1Password.
    
    Args:
        item_name: Name of the item (e.g., "GitHub PAT - Claude Code")
        field: Field to retrieve (default: "credential")
        vault: Vault name (default: "Key Vault")
    
    Returns:
        The secret value
    
    Raises:
        Exception: If secret cannot be retrieved
    """
    client = await _get_client()
    secret_ref = f"op://{vault}/{item_name}/{field}"
    return await client.secrets.resolve(secret_ref)


async def get_secrets(secret_refs: list[str]) -> dict[str, str]:
    """
    Get multiple secrets at once using secret reference URIs.
    
    Args:
        secret_refs: List of full secret references 
                     (e.g., ["op://Key Vault/Item/field"])
    
    Returns:
        Dict mapping secret reference to value
    """
    client = await _get_client()
    return await client.secrets.resolve_all(secret_refs)


async def get_secret_by_ref(secret_ref: str) -> str:
    """
    Get a secret using a full secret reference URI.
    
    Args:
        secret_ref: Full reference (e.g., "op://Key Vault/GitHub PAT/credential")
    
    Returns:
        The secret value
    """
    client = await _get_client()
    return await client.secrets.resolve(secret_ref)


async def get_vault_id(vault_name: str) -> str:
    """
    Get vault ID by name.
    
    Args:
        vault_name: Name of the vault
    
    Returns:
        Vault ID
    
    Raises:
        ValueError: If vault not found
    """
    client = await _get_client()
    vaults = await client.vaults.list()
    for vault in vaults:
        if vault.title.lower() == vault_name.lower():
            return vault.id
    raise ValueError(f"Vault not found: {vault_name}")


async def create_item(
    title: str,
    fields: dict[str, str],
    vault: str = "Key Vault",
    category: str = "api_credential",
    notes: str = ""
) -> str:
    """
    Create a new item in 1Password.
    
    Args:
        title: Item title (e.g., "Steam API Key")
        fields: Dict of field names to values (e.g., {"credential": "abc123", "steam_id": "12345"})
        vault: Vault name (default: "Key Vault")
        category: Item category (default: "api_credential"). 
                  Options: login, password, api_credential, secure_note
        notes: Optional notes field
    
    Returns:
        Success message with item ID
    
    Raises:
        Exception: If item cannot be created
    """
    client = await _get_client()
    
    # Get vault ID
    vault_id = await get_vault_id(vault)
    
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
        # Fields named credential/password/secret/api_key/token get concealed type
        if field_name.lower() in ("credential", "password", "secret", "api_key", "token"):
            field_type = ItemFieldType.CONCEALED
        else:
            field_type = ItemFieldType.TEXT
        
        item_fields.append(ItemField(
            id=field_name.lower().replace(" ", "_"),
            title=field_name,
            value=field_value,
            field_type=field_type
        ))
    
    # Create item using ItemCreateParams
    item = ItemCreateParams(
        title=title,
        category=item_category,
        vault_id=vault_id,
        fields=item_fields,
        notes=notes if notes else None
    )
    
    created = await client.items.create(item)
    return f"✅ Created item '{title}' with ID: {created.id}"
