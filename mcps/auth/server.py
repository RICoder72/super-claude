"""
Auth MCP - 1Password secret management.

Provides tools to retrieve secrets from 1Password Key Vault.
"""

import sys
sys.path.insert(0, "/app/shared")

from fastmcp import FastMCP
from op_client import get_secret, get_secret_by_ref

mcp = FastMCP("Claude-Auth")


@mcp.tool()
def ping() -> str:
    """Health check. Returns pong if the auth MCP is running."""
    return "pong from Auth MCP 🔐"


@mcp.tool()
async def auth_get(
    item_name: str,
    field: str = "credential",
    vault: str = "Key Vault"
) -> str:
    """
    Get a secret from 1Password.
    
    Args:
        item_name: Name of the item in 1Password (e.g., "GitHub PAT - Claude Code")
        field: Field name to retrieve (default: "credential")
        vault: Vault name (default: "Key Vault")
    
    Returns:
        The secret value, or error message if retrieval fails
    """
    try:
        return await get_secret(item_name, field=field, vault=vault)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def auth_get_ref(secret_ref: str) -> str:
    """
    Get a secret using a full 1Password secret reference.
    
    Args:
        secret_ref: Full secret reference URI (e.g., "op://Key Vault/GitHub PAT/credential")
    
    Returns:
        The secret value, or error message if retrieval fails
    """
    try:
        return await get_secret_by_ref(secret_ref)
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
