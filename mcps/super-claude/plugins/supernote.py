"""
Supernote Sync Plugin

Syncs files between Super Claude domains and cloud storage (where Supernote device syncs).
Does NOT talk to Supernote directly - uses Super Claude's storage abstraction.

Architecture:
    Supernote Device → (auto-sync) → Cloud Storage ← (storage_* tools) ← Super Claude

Per-domain config stored in: domains/{name}/plugins/supernote/config.json
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add paths for imports
sys.path.insert(0, "/app/core")
sys.path.insert(0, "/app/plugins")

from plugin_base import SuperClaudePlugin

logger = logging.getLogger(__name__)

# Base paths
DOMAINS_ROOT = Path("/data/domains")


class SupernotePlugin(SuperClaudePlugin):
    """
    Supernote synchronization via cloud storage.
    
    Works by syncing to/from cloud storage that Supernote device also syncs to.
    Each domain can have its own Supernote config with account + subfolder.
    """
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        self.metadata = {
            "name": "supernote",
            "version": "0.2.0",
            "description": "Sync domains with Supernote via cloud storage",
            "author": "Matthew",
            "requires": []  # No external deps - uses core storage
        }
        
        self.tools = {
            "supernote_setup": self.supernote_setup,
            "supernote_status": self.supernote_status,
            "supernote_pull": self.supernote_pull,
            "supernote_push": self.supernote_push,
            "supernote_list_remote": self.supernote_list_remote,
        }
    
    def _get_storage_manager(self):
        """Get the storage manager from server module."""
        try:
            import server
            return server.storage_manager
        except Exception as e:
            logger.error(f"Could not access storage_manager: {e}")
            return None
    
    def _get_domain_path(self, domain: str) -> Path:
        """Get path to a domain."""
        return DOMAINS_ROOT / domain
    
    def _get_plugin_path(self, domain: str) -> Path:
        """Get path to supernote plugin directory for a domain."""
        return self._get_domain_path(domain) / "plugins" / "supernote"
    
    def _get_config_path(self, domain: str) -> Path:
        """Get path to supernote config for a domain."""
        return self._get_plugin_path(domain) / "config.json"
    
    def _load_config(self, domain: str) -> Optional[Dict[str, Any]]:
        """Load supernote config for a domain."""
        config_path = self._get_config_path(domain)
        if not config_path.exists():
            return None
        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load config for {domain}: {e}")
            return None
    
    def _save_config(self, domain: str, config: Dict[str, Any]) -> bool:
        """Save supernote config for a domain."""
        try:
            plugin_path = self._get_plugin_path(domain)
            plugin_path.mkdir(parents=True, exist_ok=True)
            
            config_path = self._get_config_path(domain)
            config_path.write_text(json.dumps(config, indent=2))
            return True
        except Exception as e:
            logger.error(f"Failed to save config for {domain}: {e}")
            return False
    
    def _ensure_directories(self, domain: str) -> None:
        """Create plugin directory structure for a domain."""
        plugin_path = self._get_plugin_path(domain)
        (plugin_path / "notes").mkdir(parents=True, exist_ok=True)
        (plugin_path / "documents").mkdir(parents=True, exist_ok=True)
        (plugin_path / "converted").mkdir(parents=True, exist_ok=True)
    
    async def supernote_setup(
        self,
        domain: str,
        account: str,
        subfolder: str,
        sync_notes: bool = True,
        sync_documents: bool = True,
        convert_to: str = "pdf,png"
    ) -> str:
        """
        Configure Supernote sync for a domain.
        
        Args:
            domain: Domain name to configure
            account: Storage account name (from storage_list_accounts)
            subfolder: Subfolder name on Supernote (e.g., "burrillville")
            sync_notes: Whether to sync .note files from device (default: True)
            sync_documents: Whether to sync documents to device (default: True)
            convert_to: Formats to convert .note files to (comma-separated: pdf,png)
        
        Returns:
            Success message with config details
        """
        # Validate domain exists
        domain_path = self._get_domain_path(domain)
        if not domain_path.exists():
            return f"❌ Domain '{domain}' does not exist"
        
        # Validate storage account exists
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        if account not in storage_manager.accounts:
            available = ", ".join(storage_manager.accounts.keys()) or "none configured"
            return f"❌ Storage account '{account}' not found. Available: {available}"
        
        # Parse convert formats
        convert_formats = [f.strip() for f in convert_to.split(",") if f.strip()]
        
        # Create config
        config = {
            "account": account,
            "subfolder": subfolder,
            "sync_notes": sync_notes,
            "sync_documents": sync_documents,
            "convert_to": convert_formats,
            "configured_at": datetime.now().isoformat(),
            "last_sync": None
        }
        
        # Create directory structure and save config
        self._ensure_directories(domain)
        if not self._save_config(domain, config):
            return "❌ Failed to save configuration"
        
        # Build remote paths for reference
        note_path = f"/Note/{subfolder}/"
        doc_path = f"/Document/{subfolder}/"
        
        return f"""✅ Supernote configured for domain: {domain}

**Configuration:**
- Storage account: {account}
- Subfolder: {subfolder}
- Sync notes: {sync_notes}
- Sync documents: {sync_documents}
- Convert .note to: {', '.join(convert_formats) or 'none'}

**Remote paths (on cloud/device):**
- Notes: {note_path}
- Documents: {doc_path}

**Local paths:**
- Notes: domains/{domain}/plugins/supernote/notes/
- Documents: domains/{domain}/plugins/supernote/documents/
- Converted: domains/{domain}/plugins/supernote/converted/

Use `supernote_pull("{domain}")` to download notes from device.
Use `supernote_push("{domain}")` to upload documents to device."""
    
    async def supernote_status(self, domain: str) -> str:
        """
        Show Supernote sync status for a domain.
        
        Args:
            domain: Domain name to check
        
        Returns:
            Current configuration and sync status
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'. Use supernote_setup() first."
        
        plugin_path = self._get_plugin_path(domain)
        
        # Count local files
        notes_count = len(list((plugin_path / "notes").glob("*.note"))) if (plugin_path / "notes").exists() else 0
        docs_count = len(list((plugin_path / "documents").glob("*"))) if (plugin_path / "documents").exists() else 0
        converted_count = len(list((plugin_path / "converted").glob("*"))) if (plugin_path / "converted").exists() else 0
        
        last_sync = config.get("last_sync", "Never")
        
        return f"""📱 Supernote Status: {domain}
{'─' * 40}
**Configuration:**
- Account: {config['account']}
- Subfolder: {config['subfolder']}
- Sync notes: {config.get('sync_notes', True)}
- Sync documents: {config.get('sync_documents', True)}
- Convert to: {', '.join(config.get('convert_to', [])) or 'none'}

**Local files:**
- Notes (.note): {notes_count}
- Documents: {docs_count}
- Converted: {converted_count}

**Last sync:** {last_sync}"""
    
    async def supernote_list_remote(self, domain: str, path_type: str = "notes") -> str:
        """
        List files in the remote Supernote folder.
        
        Args:
            domain: Domain name
            path_type: "notes" or "documents"
        
        Returns:
            List of files in the remote folder
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        account = config["account"]
        subfolder = config["subfolder"]
        
        if path_type == "notes":
            remote_path = f"/Note/{subfolder}"
        elif path_type == "documents":
            remote_path = f"/Document/{subfolder}"
        else:
            return f"❌ Invalid path_type: {path_type}. Use 'notes' or 'documents'."
        
        try:
            files = await storage_manager.list_files(account, remote_path)
            
            if not files:
                return f"📂 {remote_path}\n   (empty or folder doesn't exist)"
            
            lines = [f"📂 {remote_path}", "─" * 40]
            for f in files:
                size_str = f"{f.size / 1024:.1f} KB" if f.size else ""
                icon = "📁" if f.is_directory else "📄"
                lines.append(f"{icon} {f.name}  {size_str}")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"❌ Failed to list remote files: {e}"
    
    async def supernote_pull(self, domain: str, convert: bool = True) -> str:
        """
        Pull .note files from Supernote (via cloud storage).
        
        Args:
            domain: Domain name
            convert: Whether to convert .note files to PDF/PNG (default: True)
        
        Returns:
            Summary of downloaded and converted files
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        if not config.get("sync_notes", True):
            return f"❌ Note sync is disabled for domain '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        account = config["account"]
        subfolder = config["subfolder"]
        remote_path = f"/Note/{subfolder}"
        local_notes_path = self._get_plugin_path(domain) / "notes"
        local_converted_path = self._get_plugin_path(domain) / "converted"
        
        # Ensure directories exist
        local_notes_path.mkdir(parents=True, exist_ok=True)
        local_converted_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # List remote files
            files = await storage_manager.list_files(account, remote_path)
            note_files = [f for f in files if f.name.endswith(".note")]
            
            if not note_files:
                return f"📂 No .note files found in {remote_path}"
            
            downloaded = []
            failed = []
            
            for f in note_files:
                local_file = local_notes_path / f.name
                result = await storage_manager.download(
                    account,
                    f"{remote_path}/{f.name}",
                    local_file
                )
                
                if "✅" in result:
                    downloaded.append(f.name)
                else:
                    failed.append(f.name)
            
            # Update last sync time
            config["last_sync"] = datetime.now().isoformat()
            self._save_config(domain, config)
            
            # TODO: Convert .note files to PDF/PNG
            # This requires a .note parser - could use supernote-tool or similar
            converted_msg = ""
            if convert and config.get("convert_to"):
                converted_msg = f"\n\n⚠️ Conversion to {', '.join(config['convert_to'])} not yet implemented"
            
            return f"""✅ Pull complete for {domain}

**Downloaded:** {len(downloaded)} files
{chr(10).join(f'  - {n}' for n in downloaded) if downloaded else '  (none)'}

**Failed:** {len(failed)} files
{chr(10).join(f'  - {n}' for n in failed) if failed else '  (none)'}{converted_msg}"""
        
        except Exception as e:
            return f"❌ Pull failed: {e}"
    
    async def supernote_push(self, domain: str) -> str:
        """
        Push documents to Supernote (via cloud storage).
        
        Args:
            domain: Domain name
        
        Returns:
            Summary of uploaded files
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        if not config.get("sync_documents", True):
            return f"❌ Document sync is disabled for domain '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        account = config["account"]
        subfolder = config["subfolder"]
        remote_path = f"/Document/{subfolder}"
        local_docs_path = self._get_plugin_path(domain) / "documents"
        
        if not local_docs_path.exists():
            return f"📂 No documents directory for {domain}"
        
        # Get local files to upload
        local_files = [f for f in local_docs_path.iterdir() if f.is_file()]
        
        if not local_files:
            return f"📂 No documents to push in {local_docs_path}"
        
        try:
            uploaded = []
            failed = []
            
            for local_file in local_files:
                result = await storage_manager.upload(
                    account,
                    local_file,
                    f"{remote_path}/{local_file.name}"
                )
                
                if "✅" in result:
                    uploaded.append(local_file.name)
                else:
                    failed.append(local_file.name)
            
            # Update last sync time
            config["last_sync"] = datetime.now().isoformat()
            self._save_config(domain, config)
            
            return f"""✅ Push complete for {domain}

**Uploaded:** {len(uploaded)} files
{chr(10).join(f'  - {n}' for n in uploaded) if uploaded else '  (none)'}

**Failed:** {len(failed)} files
{chr(10).join(f'  - {n}' for n in failed) if failed else '  (none)'}"""
        
        except Exception as e:
            return f"❌ Push failed: {e}"
    
    def on_load(self) -> None:
        """Called when plugin loads."""
        logger.info("Supernote plugin loaded")
    
    def on_unload(self) -> None:
        """Called when plugin unloads."""
        logger.info("Supernote plugin unloaded")
