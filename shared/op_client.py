"""
Shared 1Password client for Claude MCPs.

Usage:
    from op_client import get_secret, get_secrets

    # Single secret
    token = await get_secret("GitHub PAT - Claude Code")
    
    # With custom field/vault
    api_key = await get_secret("Jira API Key", field="password", vault="Work")
    
    # Multiple secrets at once
    secrets = await get_secrets([
        "op://Key Vault/GitHub PAT - Claude Code/credential",
        "op://Key Vault/Some Other Secret/password",
    ])
"""

import os
from onepassword.client import Client

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
            integration_version="v0.1.0"
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
