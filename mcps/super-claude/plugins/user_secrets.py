"""
User Secrets Plugin v1.0.0

Manages user-facing secrets (passwords, credentials) separate from infrastructure secrets.
This is for YOUR passwords - firewall logins, vendor credentials, system passwords.

Architecture:
- Infrastructure secrets (core/secrets/) = internal plumbing (API keys, OAuth tokens)
- User secrets (this plugin) = user-facing password storage

Each "account" is a logical grouping (like a folder) in 1Password:
- "work": Work-related credentials
- "personal": Personal accounts
- "homelab": Home infrastructure passwords

Usage:
    secrets_list_accounts()          - See configured accounts
    secrets_add_account("homelab", vault="Home Lab")
    secrets_list("homelab")          - List items
    secrets_get("homelab", "router admin")
    secrets_set("homelab", "router admin", "password123", username="admin")
"""

import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

sys.path.insert(0, "/app/plugins")
from plugin_base import SuperClaudePlugin

logger = logging.getLogger(__name__)

CONFIG_DIR = Path("/data/config")
ACCOUNTS_CONFIG = CONFIG_DIR / "user_secrets_accounts.json"


class UserSecretsPlugin(SuperClaudePlugin):
    """
    User-facing secrets management.
    
    Provides password storage separate from infrastructure secrets.
    Uses 1Password as the backend via the op CLI.
    """
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        self.metadata = {
            "name": "user_secrets",
            "version": "1.0.0",
            "description": "User-facing password and credential storage",
            "author": "Matthew",
            "requires": []
        }
        
        self.tools = {
            "secrets_list_accounts": self.secrets_list_accounts,
            "secrets_add_account": self.secrets_add_account,
            "secrets_remove_account": self.secrets_remove_account,
            "secrets_list": self.secrets_list,
            "secrets_get": self.secrets_get,
            "secrets_set": self.secrets_set,
            "secrets_delete": self.secrets_delete,
        }
        
        self._accounts: Dict[str, Dict] = {}
        self._load_accounts()
    
    def _load_accounts(self) -> None:
        """Load account configuration."""
        if not ACCOUNTS_CONFIG.exists():
            return
        
        try:
            config = json.loads(ACCOUNTS_CONFIG.read_text())
            self._accounts = config.get("accounts", {})
            logger.info(f"Loaded {len(self._accounts)} user secrets accounts")
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
    
    def _save_accounts(self) -> None:
        """Save account configuration."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config = {"accounts": self._accounts}
            ACCOUNTS_CONFIG.write_text(json.dumps(config, indent=2))
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
    
    def _run_op(self, args: List[str], timeout: int = 30) -> tuple[bool, str]:
        """Run an op CLI command."""
        try:
            result = subprocess.run(
                ["op"] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return False, "op CLI not found"
        except Exception as e:
            return False, str(e)
    
    # =========================================================================
    # ACCOUNT MANAGEMENT
    # =========================================================================
    
    async def secrets_list_accounts(self) -> str:
        """
        List all configured user secrets accounts.
        
        Each account maps to a 1Password vault for organizing credentials.
        """
        if not self._accounts:
            return """🔐 No user secrets accounts configured.

Add one with: secrets_add_account("name", vault="Vault Name")

Examples:
- secrets_add_account("work", vault="Work Credentials")
- secrets_add_account("homelab", vault="Home Lab")"""
        
        lines = ["🔐 User Secrets Accounts", "─" * 40]
        for name, config in self._accounts.items():
            vault = config.get("vault", "Default")
            desc = config.get("description", "")
            lines.append(f"  • {name} → vault: {vault}")
            if desc:
                lines.append(f"    {desc}")
        
        return "\n".join(lines)
    
    async def secrets_add_account(
        self,
        name: str,
        vault: str = "Secrets",
        description: str = ""
    ) -> str:
        """
        Add a new user secrets account.
        
        Args:
            name: Account name (e.g., "work", "homelab", "personal")
            vault: 1Password vault name to use
            description: Optional description
        
        Returns:
            Success message
        """
        if name in self._accounts:
            return f"❌ Account '{name}' already exists"
        
        # Verify vault exists
        success, output = self._run_op(["vault", "get", vault, "--format=json"])
        if not success:
            return f"❌ Vault '{vault}' not found or not accessible: {output}"
        
        self._accounts[name] = {
            "vault": vault,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        self._save_accounts()
        
        return f"✅ Added user secrets account: {name} → vault: {vault}"
    
    async def secrets_remove_account(self, name: str) -> str:
        """
        Remove a user secrets account.
        
        Note: This only removes the account mapping, not the actual vault/items.
        
        Args:
            name: Account name to remove
        """
        if name not in self._accounts:
            return f"❌ Account '{name}' not found"
        
        vault = self._accounts[name].get("vault")
        del self._accounts[name]
        self._save_accounts()
        
        return f"✅ Removed account '{name}' (vault '{vault}' unchanged)"
    
    # =========================================================================
    # SECRET OPERATIONS
    # =========================================================================
    
    async def secrets_list(self, account: str, search: str = None) -> str:
        """
        List secrets in an account.
        
        Args:
            account: Account name
            search: Optional search term to filter items
        
        Returns:
            List of secret names
        """
        if account not in self._accounts:
            available = ", ".join(self._accounts.keys()) or "none"
            return f"❌ Account '{account}' not found. Available: {available}"
        
        vault = self._accounts[account]["vault"]
        
        args = ["item", "list", f"--vault={vault}", "--format=json"]
        success, output = self._run_op(args)
        
        if not success:
            return f"❌ Failed to list secrets: {output}"
        
        try:
            items = json.loads(output) if output else []
        except json.JSONDecodeError:
            return f"❌ Invalid response from op CLI"
        
        if not items:
            return f"🔐 No secrets in account '{account}' (vault: {vault})"
        
        # Filter if search term provided
        if search:
            search_lower = search.lower()
            items = [i for i in items if search_lower in i.get("title", "").lower()]
        
        lines = [f"🔐 Secrets in '{account}'", "─" * 40]
        for item in items:
            title = item.get("title", "Untitled")
            category = item.get("category", "")
            lines.append(f"  • {title} ({category})")
        
        if search:
            lines.append(f"\n(filtered by: '{search}')")
        
        return "\n".join(lines)
    
    async def secrets_get(
        self,
        account: str,
        item_name: str,
        field: str = "password"
    ) -> str:
        """
        Get a secret value.
        
        Args:
            account: Account name
            item_name: Name of the item to retrieve
            field: Field to get (default: "password")
        
        Returns:
            The secret value
        
        Common fields:
            - password: The main password
            - username: Associated username
            - url: Website URL
            - notes: Notes field
        """
        if account not in self._accounts:
            available = ", ".join(self._accounts.keys()) or "none"
            return f"❌ Account '{account}' not found. Available: {available}"
        
        vault = self._accounts[account]["vault"]
        
        # Build op:// reference
        ref = f"op://{vault}/{item_name}/{field}"
        success, output = self._run_op(["read", ref])
        
        if not success:
            if "isn't an item" in output or "could not be found" in output:
                return f"❌ Item '{item_name}' not found in account '{account}'"
            if "isn't a field" in output:
                return f"❌ Field '{field}' not found in item '{item_name}'"
            return f"❌ Failed to read secret: {output}"
        
        return output
    
    async def secrets_set(
        self,
        account: str,
        item_name: str,
        password: str,
        username: str = None,
        url: str = None,
        notes: str = None
    ) -> str:
        """
        Create or update a secret.
        
        Args:
            account: Account name
            item_name: Name for the item
            password: The password to store
            username: Optional username
            url: Optional URL
            notes: Optional notes
        
        Returns:
            Success message
        """
        if account not in self._accounts:
            available = ", ".join(self._accounts.keys()) or "none"
            return f"❌ Account '{account}' not found. Available: {available}"
        
        vault = self._accounts[account]["vault"]
        
        # Check if item exists
        success, _ = self._run_op(["item", "get", item_name, f"--vault={vault}"])
        
        if success:
            # Update existing item
            args = ["item", "edit", item_name, f"--vault={vault}"]
            args.append(f"password={password}")
            if username:
                args.append(f"username={username}")
            if url:
                args.append(f"url={url}")
            if notes:
                args.append(f"notesPlain={notes}")
            
            success, output = self._run_op(args)
            action = "Updated"
        else:
            # Create new item
            args = [
                "item", "create",
                f"--vault={vault}",
                "--category=login",
                f"--title={item_name}",
                f"password={password}"
            ]
            if username:
                args.append(f"username={username}")
            if url:
                args.append(f"url={url}")
            if notes:
                args.append(f"notesPlain={notes}")
            
            success, output = self._run_op(args)
            action = "Created"
        
        if success:
            return f"✅ {action} secret '{item_name}' in account '{account}'"
        else:
            return f"❌ Failed to save secret: {output}"
    
    async def secrets_delete(self, account: str, item_name: str) -> str:
        """
        Delete a secret.
        
        Args:
            account: Account name
            item_name: Name of the item to delete
        
        Returns:
            Success message
        """
        if account not in self._accounts:
            available = ", ".join(self._accounts.keys()) or "none"
            return f"❌ Account '{account}' not found. Available: {available}"
        
        vault = self._accounts[account]["vault"]
        
        # Archive (soft delete) instead of permanent delete
        success, output = self._run_op([
            "item", "delete", item_name,
            f"--vault={vault}",
            "--archive"  # Move to archive rather than permanent delete
        ])
        
        if success:
            return f"✅ Deleted (archived) '{item_name}' from account '{account}'"
        else:
            if "isn't an item" in output or "could not be found" in output:
                return f"❌ Item '{item_name}' not found in account '{account}'"
            return f"❌ Failed to delete: {output}"
    
    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    def on_load(self) -> None:
        """Called when plugin loads."""
        logger.info(f"User secrets plugin loaded with {len(self._accounts)} accounts")
    
    def on_unload(self) -> None:
        """Called when plugin unloaded."""
        logger.info("User secrets plugin unloaded")
