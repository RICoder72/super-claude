"""
Storage Account Manager

Manages named storage accounts and adapter instances.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Type, List
import logging

from .interface import StorageAdapter, StorageAccount, FileInfo, FilePage

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("/data/config/storage_accounts.json")


class StorageManager:
    """
    Manages storage accounts and adapter instances.
    
    Provides a unified interface for accessing any configured
    storage account without knowing the underlying provider.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self.accounts: Dict[str, StorageAccount] = {}
        self.adapters: Dict[str, StorageAdapter] = {}
        self.adapter_classes: Dict[str, Type[StorageAdapter]] = {}
        
        self._load_accounts()
    
    def register_adapter_type(self, adapter_type: str, adapter_class: Type[StorageAdapter]) -> None:
        """Register an adapter implementation."""
        self.adapter_classes[adapter_type] = adapter_class
        logger.info(f"✅ Registered storage adapter: {adapter_type}")
    
    def _load_accounts(self) -> None:
        """Load accounts from config file."""
        if not self.config_path.exists():
            logger.info("No storage accounts config found, starting fresh")
            return
        
        try:
            config = json.loads(self.config_path.read_text())
            for name, data in config.get("accounts", {}).items():
                self.accounts[name] = StorageAccount(
                    name=name,
                    adapter=data.get("provider", data.get("adapter", "")),  # Support both old "provider" and new "adapter"
                    credentials_ref=data.get("credentials_ref", ""),
                    config=data.get("config", {})
                )
            logger.info(f"✅ Loaded {len(self.accounts)} storage accounts")
        except Exception as e:
            logger.error(f"❌ Failed to load accounts: {e}")
    
    def _save_accounts(self) -> None:
        """Save accounts to config file."""
        config = {"accounts": {}}
        for name, account in self.accounts.items():
            config["accounts"][name] = {
                "adapter": account.adapter,
                "credentials_ref": account.credentials_ref,
                "config": account.config
            }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
    
    def add_account(
        self,
        name: str,
        adapter: str,
        credentials_ref: str = "",
        config: Optional[Dict] = None
    ) -> str:
        """Add a new storage account."""
        if name in self.accounts:
            return f"❌ Account '{name}' already exists"
        
        if adapter not in self.adapter_classes:
            available = ", ".join(self.adapter_classes.keys()) or "none"
            return f"❌ Unknown adapter '{adapter}'. Available: {available}"
        
        self.accounts[name] = StorageAccount(
            name=name,
            adapter=adapter,
            credentials_ref=credentials_ref,
            config=config or {}
        )
        self._save_accounts()
        
        return f"✅ Added storage account: {name} ({adapter})"
    
    def remove_account(self, name: str) -> str:
        """Remove a storage account."""
        if name not in self.accounts:
            return f"❌ Account '{name}' not found"
        
        if name in self.adapters:
            del self.adapters[name]
        
        del self.accounts[name]
        self._save_accounts()
        
        return f"✅ Removed storage account: {name}"
    
    def list_accounts(self) -> str:
        """List all configured accounts."""
        if not self.accounts:
            return "📂 No storage accounts configured"
        
        lines = ["📂 Storage Accounts", "─" * 40]
        for name, account in self.accounts.items():
            connected = "🟢" if name in self.adapters else "⚪"
            lines.append(f"{connected} {name} ({account.adapter})")
            if account.config.get("root_path"):
                lines.append(f"   Root: {account.config['root_path']}")
        
        return "\n".join(lines)
    
    async def get_adapter(self, account_name: str) -> Optional[StorageAdapter]:
        """Get or create an adapter instance for an account."""
        if account_name not in self.accounts:
            logger.error(f"Account not found: {account_name}")
            return None
        
        if account_name in self.adapters:
            return self.adapters[account_name]
        
        account = self.accounts[account_name]
        adapter_type = account.adapter
        
        # Support legacy "provider" field mapped to adapter
        if adapter_type == "gdrive":
            adapter_type = "gdrive"
        
        if adapter_type not in self.adapter_classes:
            logger.error(f"Adapter not registered: {adapter_type}")
            return None
        
        adapter_class = self.adapter_classes[adapter_type]
        adapter = adapter_class(account)
        
        if await adapter.connect():
            self.adapters[account_name] = adapter
            return adapter
        
        return None
    
    # Convenience methods that route to the appropriate adapter
    
    async def upload(self, account_name: str, local_path: Path, remote_path: str) -> str:
        adapter = await self.get_adapter(account_name)
        if not adapter:
            return f"❌ Could not connect to account: {account_name}"
        return await adapter.upload(local_path, remote_path)
    
    async def download(self, account_name: str, remote_path: str, local_path: Path) -> str:
        adapter = await self.get_adapter(account_name)
        if not adapter:
            return f"❌ Could not connect to account: {account_name}"
        return await adapter.download(remote_path, local_path)
    
    async def list_files(self, account_name: str, remote_path: str = "/", limit: int = 100, cursor: Optional[str] = None) -> FilePage:
        adapter = await self.get_adapter(account_name)
        if not adapter:
            return FilePage(files=[])
        return await adapter.list_files(remote_path, limit, cursor)
    
    async def exists(self, account_name: str, remote_path: str) -> bool:
        adapter = await self.get_adapter(account_name)
        if not adapter:
            return False
        return await adapter.exists(remote_path)
    
    async def delete(self, account_name: str, remote_path: str) -> str:
        adapter = await self.get_adapter(account_name)
        if not adapter:
            return f"❌ Could not connect to account: {account_name}"
        return await adapter.delete(remote_path)
