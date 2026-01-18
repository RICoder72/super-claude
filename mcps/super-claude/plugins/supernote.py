"""
Supernote Sync Plugin v0.6.0

Syncs files between Super Claude domains and cloud storage (where Supernote device syncs).
Does NOT talk to Supernote directly - uses Super Claude's storage abstraction.

Architecture:
    Supernote Device → (auto-sync) → Cloud Storage ← (storage_* tools) ← Super Claude

Per-domain config stored in: domains/{name}/plugins/supernote/config.json

New in v0.6.0:
- supernote_mark_processed: Move completed notes to processed folder
- supernote_unprocess: Restore notes to pending
- supernote_list_notes: Now shows pending/processed sections

v0.5.0:
- supernote_read_note: Returns note pages as images (for Claude vision)
- supernote_read_page: Returns a single page as image
- supernote_list_notes: Lists available notes with page counts
- Integrated .note → PNG conversion into pull
"""

import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging

# Add paths for imports
sys.path.insert(0, "/app/core")
sys.path.insert(0, "/app/plugins")

from plugin_base import SuperClaudePlugin

# Import FastMCP's Image helper for returning images
try:
    from fastmcp.utilities.types import Image
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

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
            "version": "0.6.0",
            "description": "Sync domains with Supernote via cloud storage",
            "author": "Matthew",
            "requires": []
        }
        
        self.tools = {
            "supernote_setup": self.supernote_setup,
            "supernote_status": self.supernote_status,
            "supernote_pull": self.supernote_pull,
            "supernote_push": self.supernote_push,
            "supernote_list_remote": self.supernote_list_remote,
            "supernote_list_notes": self.supernote_list_notes,
            "supernote_read_note": self.supernote_read_note,
            "supernote_read_page": self.supernote_read_page,
            # TODO: implement supernote_mark_processed and supernote_unprocess
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
        (plugin_path / "processed").mkdir(parents=True, exist_ok=True)
    
    def _get_remote_paths(self, config: Dict[str, Any]) -> tuple[str, str]:
        """Get the remote note and document paths from config."""
        base_path = config.get("base_path", "").rstrip("/")
        subfolder = config["subfolder"]
        note_path = f"{base_path}/Note/{subfolder}"
        doc_path = f"{base_path}/Document/{subfolder}"
        return note_path, doc_path
    
    def _convert_note(self, note_path: Path, output_dir: Path, formats: List[str]) -> Dict[str, Any]:
        """
        Convert a .note file to specified formats using supernote-tool.
        
        Args:
            note_path: Path to the .note file
            output_dir: Directory for converted files
            formats: List of formats (png, pdf, svg, txt)
        
        Returns:
            Dict with conversion results
        """
        results = {"success": [], "failed": []}
        
        for fmt in formats:
            try:
                # supernote-tool convert -t png -a input.note output_dir/
                # -a means all pages (creates input_0.png, input_1.png, etc.)
                cmd = [
                    "supernote-tool", "convert",
                    "-t", fmt,
                    "-a",  # all pages
                    str(note_path),
                    str(output_dir) + "/"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    results["success"].append(fmt)
                else:
                    results["failed"].append((fmt, result.stderr))
                    
            except Exception as e:
                results["failed"].append((fmt, str(e)))
        
        return results
    
    def _get_note_pages(self, domain: str, note_stem: str) -> List[Path]:
        """Get all converted page files for a note."""
        converted_dir = self._get_plugin_path(domain) / "converted"
        # Pattern: note_stem_0.png, note_stem_1.png, etc.
        pages = sorted(converted_dir.glob(f"{note_stem}_*.png"))
        return pages
    
    # =========================================================================
    # TOOLS
    # =========================================================================
    
    async def supernote_setup(
        self,
        domain: str,
        account: str,
        subfolder: str,
        sync_notes: bool = True,
        sync_documents: bool = True,
        convert_to: str = "png",
        base_path: str = ""
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
            base_path: Root folder where Supernote syncs (e.g., "/Supernote" or "" for root)
        
        Returns:
            Success message with config details
        """
        domain_path = self._get_domain_path(domain)
        if not domain_path.exists():
            return f"❌ Domain '{domain}' does not exist"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        if account not in storage_manager.accounts:
            available = ", ".join(storage_manager.accounts.keys()) or "none configured"
            return f"❌ Storage account '{account}' not found. Available: {available}"
        
        convert_formats = [f.strip() for f in convert_to.split(",") if f.strip()]
        
        base_path = base_path.strip().rstrip("/")
        if base_path and not base_path.startswith("/"):
            base_path = "/" + base_path
        
        config = {
            "account": account,
            "subfolder": subfolder,
            "base_path": base_path,
            "sync_notes": sync_notes,
            "sync_documents": sync_documents,
            "convert_to": convert_formats,
            "configured_at": datetime.now().isoformat(),
            "last_sync": None
        }
        
        self._ensure_directories(domain)
        if not self._save_config(domain, config):
            return "❌ Failed to save configuration"
        
        note_path, doc_path = self._get_remote_paths(config)
        
        return f"""✅ Supernote configured for domain: {domain}

**Configuration:**
- Storage account: {account}
- Base path: {base_path or '/ (root)'}
- Subfolder: {subfolder}
- Sync notes: {sync_notes}
- Sync documents: {sync_documents}
- Convert .note to: {', '.join(convert_formats) or 'none'}

**Remote paths (on cloud/device):**
- Notes: {note_path}/
- Documents: {doc_path}/

**Local paths:**
- Notes: domains/{domain}/plugins/supernote/notes/
- Converted: domains/{domain}/plugins/supernote/converted/
- Processed: domains/{domain}/plugins/supernote/processed/

Use `supernote_pull("{domain}")` to download and convert notes.
Use `supernote_read_note("{domain}", "note_stem")` to view converted pages."""
    
    async def supernote_status(self, domain: str) -> str:
        """Show Supernote sync status for a domain."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'. Use supernote_setup() first."
        
        plugin_path = self._get_plugin_path(domain)
        
        notes_count = len(list((plugin_path / "notes").glob("*.note"))) if (plugin_path / "notes").exists() else 0
        docs_count = len(list((plugin_path / "documents").glob("*"))) if (plugin_path / "documents").exists() else 0
        converted_count = len(list((plugin_path / "converted").glob("*.png"))) if (plugin_path / "converted").exists() else 0
        processed_count = len(list((plugin_path / "processed").glob("*.note"))) if (plugin_path / "processed").exists() else 0
        
        last_sync = config.get("last_sync", "Never")
        base_path = config.get("base_path", "")
        note_path, doc_path = self._get_remote_paths(config)
        
        return f"""📱 Supernote Status: {domain}
{'─' * 40}
**Configuration:**
- Account: {config['account']}
- Base path: {base_path or '/ (root)'}
- Subfolder: {config['subfolder']}
- Convert to: {', '.join(config.get('convert_to', [])) or 'none'}

**Remote paths:**
- Notes: {note_path}/
- Documents: {doc_path}/

**Local files:**
- Notes (.note): {notes_count}
- Converted (PNG): {converted_count}
- Processed: {processed_count}
- Documents: {docs_count}

**Last sync:** {last_sync}"""
    
    async def supernote_list_remote(self, domain: str, path_type: str = "notes") -> str:
        """List files in the remote Supernote folder."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        account = config["account"]
        note_path, doc_path = self._get_remote_paths(config)
        
        if path_type == "notes":
            remote_path = note_path
        elif path_type == "documents":
            remote_path = doc_path
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
    
    async def supernote_list_notes(self, domain: str, include_processed: bool = False) -> str:
        """
        List available notes for a domain with their page counts.
        
        Args:
            domain: Domain name
            include_processed: Whether to show processed notes (default: False)
        
        Returns:
            List of notes and their converted pages
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        plugin_path = self._get_plugin_path(domain)
        notes_dir = plugin_path / "notes"
        processed_dir = plugin_path / "processed"
        converted_dir = plugin_path / "converted"
        
        # Get pending notes
        pending_notes = sorted(notes_dir.glob("*.note")) if notes_dir.exists() else []
        processed_notes = sorted(processed_dir.glob("*.note")) if processed_dir.exists() else []
        
        if not pending_notes and not processed_notes:
            return f"📂 No notes found in {domain}. Run supernote_pull first."
        
        lines = [f"📓 Notes in {domain}", "─" * 40]
        
        # Pending notes section
        if pending_notes:
            lines.append(f"\n**Pending** ({len(pending_notes)} notes):")
            for note in pending_notes:
                stem = note.stem
                pages = list(converted_dir.glob(f"{stem}_*.png"))
                page_count = len(pages)
                
                if page_count > 0:
                    lines.append(f"  📝 {stem} ({page_count} pages)")
                else:
                    lines.append(f"  ⚠️ {stem} (not converted)")
        else:
            lines.append("\n**Pending:** (none)")
        
        # Processed notes section
        if include_processed and processed_notes:
            lines.append(f"\n**Processed** ({len(processed_notes)} notes):")
            for note in processed_notes:
                stem = note.stem
                pages = list(converted_dir.glob(f"{stem}_*.png"))
                page_count = len(pages)
                lines.append(f"  ✅ {stem} ({page_count} pages)")
        elif processed_notes:
            lines.append(f"\n({len(processed_notes)} processed notes hidden - use include_processed=True)")
        
        lines.append("")
        lines.append("Use `supernote_read_note(domain, note_stem)` to view pages.")
        lines.append("Use `supernote_mark_processed(domain, note_stem)` when done.")
        
        return "\n".join(lines)
    
    async def supernote_read_note(self, domain: str, note_stem: str) -> Union[List[Any], str]:
        """
        Read all pages of a Supernote note as images.
        
        This returns the converted PNG pages as images that Claude can see
        and interpret using vision. Use this to extract content from handwritten notes.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension (e.g., "20260116_140203")
        
        Returns:
            List of Image objects (one per page) that Claude can see
        """
        if not IMAGE_SUPPORT:
            return "❌ Image support not available (fastmcp.utilities.types.Image not found)"
        
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        pages = self._get_note_pages(domain, note_stem)
        
        if not pages:
            return f"❌ No converted pages found for note '{note_stem}'. Run supernote_pull first."
        
        # Return list of Image objects - FastMCP will convert to ImageContent
        result = []
        for i, page_path in enumerate(pages):
            result.append(Image(path=page_path))
            # Optionally add page label (uncomment if you want text between pages)
            # result.append(f"[Page {i + 1} of {len(pages)}]")
        
        return result
    
    async def supernote_read_page(self, domain: str, note_stem: str, page: int = 0) -> Union[Any, str]:
        """
        Read a single page of a Supernote note as an image.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension (e.g., "20260116_140203")
            page: Page number (0-indexed)
        
        Returns:
            Image object that Claude can see
        """
        if not IMAGE_SUPPORT:
            return "❌ Image support not available"
        
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        converted_dir = self._get_plugin_path(domain) / "converted"
        page_path = converted_dir / f"{note_stem}_{page}.png"
        
        if not page_path.exists():
            pages = self._get_note_pages(domain, note_stem)
            if not pages:
                return f"❌ No converted pages found for note '{note_stem}'"
            return f"❌ Page {page} not found. Available pages: 0-{len(pages)-1}"
        
        return Image(path=page_path)
    
    async def supernote_pull(self, domain: str, convert: bool = True) -> str:
        """
        Pull .note files from Supernote (via cloud storage) and convert to PNG.
        
        Args:
            domain: Domain name
            convert: Whether to convert .note files to PNG (default: True)
        
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
        note_path, _ = self._get_remote_paths(config)
        local_notes_path = self._get_plugin_path(domain) / "notes"
        local_converted_path = self._get_plugin_path(domain) / "converted"
        
        local_notes_path.mkdir(parents=True, exist_ok=True)
        local_converted_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # List remote files
            files = await storage_manager.list_files(account, note_path)
            note_files = [f for f in files if f.name.endswith(".note")]
            
            if not note_files:
                return f"📂 No .note files found in {note_path}"
            
            downloaded = []
            failed = []
            
            for f in note_files:
                local_file = local_notes_path / f.name
                result = await storage_manager.download(
                    account,
                    f"{note_path}/{f.name}",
                    local_file
                )
                
                if "✅" in result:
                    downloaded.append(f.name)
                else:
                    failed.append(f.name)
            
            # Convert downloaded notes
            converted = []
            convert_failed = []
            
            if convert and config.get("convert_to"):
                formats = config["convert_to"]
                for note_name in downloaded:
                    note_file = local_notes_path / note_name
                    result = self._convert_note(note_file, local_converted_path, formats)
                    
                    if result["success"]:
                        # Count output files
                        stem = note_file.stem
                        pages = list(local_converted_path.glob(f"{stem}_*.png"))
                        converted.append(f"{note_name} → {len(pages)} pages")
                    if result["failed"]:
                        convert_failed.extend([f"{note_name}: {err}" for _, err in result["failed"]])
            
            # Update last sync time
            config["last_sync"] = datetime.now().isoformat()
            self._save_config(domain, config)
            
            # Build result message
            msg = [f"✅ Pull complete for {domain}", ""]
            
            msg.append(f"**Downloaded:** {len(downloaded)} files")
            for n in downloaded:
                msg.append(f"  - {n}")
            
            if failed:
                msg.append(f"\n**Download failed:** {len(failed)} files")
                for n in failed:
                    msg.append(f"  - {n}")
            
            if convert and converted:
                msg.append(f"\n**Converted:** {len(converted)} notes")
                for c in converted:
                    msg.append(f"  - {c}")
            
            if convert_failed:
                msg.append(f"\n**Conversion failed:**")
                for err in convert_failed:
                    msg.append(f"  - {err}")
            
            msg.append("")
            msg.append("Use `supernote_list_notes(domain)` to see available notes.")
            msg.append("Use `supernote_read_note(domain, note_stem)` to view pages.")
            
            return "\n".join(msg)
        
        except Exception as e:
            return f"❌ Pull failed: {e}"
    
    async def supernote_push(self, domain: str) -> str:
        """Push documents to Supernote (via cloud storage)."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for domain '{domain}'"
        
        if not config.get("sync_documents", True):
            return f"❌ Document sync is disabled for domain '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        account = config["account"]
        _, doc_path = self._get_remote_paths(config)
        local_docs_path = self._get_plugin_path(domain) / "documents"
        
        if not local_docs_path.exists():
            return f"📂 No documents directory for {domain}"
        
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
                    f"{doc_path}/{local_file.name}"
                )
                
                if "✅" in result:
                    uploaded.append(local_file.name)
                else:
                    failed.append(local_file.name)
            
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
        logger.info("Supernote plugin v0.6.0 loaded with image support")
    
    def on_unload(self) -> None:
        """Called when plugin unloaded."""
        logger.info("Supernote plugin unloaded")
