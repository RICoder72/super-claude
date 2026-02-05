"""
Supernote Sync Plugin v1.0.0

Streamlined two-phase workflow:
- PULL: Ingest from device, convert, archive locally, clean remote
- PROCESS: Human-in-the-loop review via Claude vision

Storage Structure:
    plugins/supernote/
    ├── inbox/
    │   ├── notes/           # Unprocessed note PNGs
    │   └── annotations/     # Unprocessed merged annotation PNGs
    ├── archive/
    │   ├── notes/           # Processed: .note files + PNGs
    │   └── annotations/     # Processed: .mark files + PNGs
    └── config.json
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import re
import sys

sys.path.insert(0, "/app/core")
sys.path.insert(0, "/app/plugins")

from plugin_base import SuperClaudePlugin

try:
    from fastmcp.utilities.types import Image
    from mcp.types import TextContent, ImageContent
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False
    TextContent = None
    ImageContent = None

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)
DOMAINS_ROOT = Path("/data/domains")


class SupernotePlugin(SuperClaudePlugin):
    """
    Supernote synchronization via cloud storage.
    
    Two-phase workflow:
    1. PULL: Ingest from device -> convert -> archive -> clean remote
    2. PROCESS: Vision review -> extract content -> mark processed
    """
    
    def initialize(self) -> None:
        self.metadata = {
            "name": "supernote",
            "version": "1.0.0",
            "description": "Bidirectional sync with Supernote device via cloud storage. Pull handwritten notes, process with vision, send documents back.",
            "author": "Matthew",
            "requires": [],
            
            # Recognition: keywords/phrases that suggest this plugin is relevant
            "triggers": [
                "supernote",
                "handwritten notes",
                "stylus notes",
                "e-ink notes",
                "pen notes",
                "meeting notes",  # when context suggests handwritten
                "annotations",
                ".note files",
                ".mark files",
                "send to my device",
                "push to supernote",
                "notes from my tablet"
            ],
            
            # Common multi-step patterns
            "workflows": {
                "check_for_new_notes": "supernote_pull(domain) → supernote_list_unprocessed(domain)",
                "process_a_note": "supernote_list_unprocessed → supernote_process_note(domain, stem) → [review content] → supernote_mark_note_processed(domain, stem)",
                "process_annotations": "supernote_list_unprocessed → supernote_process_annotation(domain, stem) → [review] → supernote_mark_annotation_processed(domain, stem)",
                "send_document_to_device": "supernote_md2pdf(domain, source, to_outbox=True) → supernote_push(domain)",
                "full_sync_cycle": "supernote_pull → supernote_list_unprocessed → [process each] → supernote_push"
            },
            
            # What NOT to do when this plugin applies
            "anti_patterns": [
                "Don't manually read from domains/*/plugins/supernote/inbox/ - use supernote_list_unprocessed and supernote_process_note",
                "Don't ask user to manually move files to their device - use supernote_md2pdf + supernote_push",
                "Don't ask 'do you have notes on X?' without first running supernote_list_unprocessed to check",
                "Don't use fs_read on .note or .mark files - they're binary; use the supernote_process_* tools",
                "Don't skip supernote_pull - always pull first to get latest from device before listing unprocessed",
                "Don't forget to mark notes processed after reviewing - otherwise they stay in inbox forever"
            ]
        }
        self.tools = {
            # Setup & Status
            "supernote_setup": self.supernote_setup,
            "supernote_status": self.supernote_status,
            "supernote_list_remote": self.supernote_list_remote,
            # PULL Phase
            "supernote_pull": self.supernote_pull,
            "supernote_pull_notes": self.supernote_pull_notes,
            "supernote_pull_annotations": self.supernote_pull_annotations,
            # PROCESS Phase
            "supernote_list_unprocessed": self.supernote_list_unprocessed,
            "supernote_process_note": self.supernote_process_note,
            "supernote_process_annotation": self.supernote_process_annotation,
            "supernote_mark_note_processed": self.supernote_mark_note_processed,
            "supernote_mark_annotation_processed": self.supernote_mark_annotation_processed,
            # Push
            "supernote_push": self.supernote_push,
            # Utilities
            "supernote_md2pdf": self.supernote_md2pdf,
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    
    def _get_storage_manager(self):
        try:
            import server
            return server.storage_manager
        except Exception as e:
            logger.error(f"Could not access storage_manager: {e}")
            return None

    def _get_domain_path(self, domain: str) -> Path:
        return DOMAINS_ROOT / domain

    def _get_plugin_path(self, domain: str) -> Path:
        return self._get_domain_path(domain) / "plugins" / "supernote"

    def _get_config_path(self, domain: str) -> Path:
        return self._get_plugin_path(domain) / "config.json"

    def _load_config(self, domain: str) -> Optional[Dict[str, Any]]:
        config_path = self._get_config_path(domain)
        if not config_path.exists():
            return None
        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load config for {domain}: {e}")
            return None

    def _save_config(self, domain: str, config: Dict[str, Any]) -> bool:
        try:
            plugin_path = self._get_plugin_path(domain)
            plugin_path.mkdir(parents=True, exist_ok=True)
            self._get_config_path(domain).write_text(json.dumps(config, indent=2))
            return True
        except Exception as e:
            logger.error(f"Failed to save config for {domain}: {e}")
            return False

    def _ensure_directories(self, domain: str) -> None:
        """Create the directory structure."""
        plugin_path = self._get_plugin_path(domain)
        (plugin_path / "inbox" / "notes").mkdir(parents=True, exist_ok=True)
        (plugin_path / "inbox" / "annotations").mkdir(parents=True, exist_ok=True)
        (plugin_path / "archive" / "notes").mkdir(parents=True, exist_ok=True)
        (plugin_path / "archive" / "annotations").mkdir(parents=True, exist_ok=True)
        (plugin_path / "outbox").mkdir(parents=True, exist_ok=True)

    def _get_remote_paths(self, config: Dict[str, Any]) -> tuple:
        base_path = config.get("base_path", "").rstrip("/")
        subfolder = config["subfolder"]
        return f"{base_path}/Note/{subfolder}", f"{base_path}/Document/{subfolder}"

    def _convert_note_to_png(self, note_path: Path, output_dir: Path) -> Dict[str, Any]:
        """Convert a .note file to PNG images using supernote-tool."""
        try:
            output_file = output_dir / f"{note_path.stem}.png"
            result = subprocess.run(
                ["supernote-tool", "convert", "-t", "png", "-a", str(note_path), str(output_file)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                pages = sorted(output_dir.glob(f"{note_path.stem}_*.png"))
                return {"success": True, "pages": pages}
            return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _convert_mark_to_merged_png(self, mark_path: Path, pdf_path: Path, output_dir: Path) -> Dict[str, Any]:
        """Convert .mark file to PNG merged with PDF content."""
        if not PYMUPDF_AVAILABLE:
            return {"success": False, "error": "PyMuPDF not installed"}
        
        doc_stem = mark_path.stem.replace(".pdf", "")
        try:
            # Convert .mark to transparent PNGs
            mark_png_base = output_dir / f"{doc_stem}_mark_temp.png"
            result = subprocess.run(
                ["supernote-tool", "convert", "-t", "png", "-a", "--exclude-background",
                 str(mark_path), str(mark_png_base)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return {"success": False, "error": f"supernote-tool failed: {result.stderr}"}
            
            mark_pngs = sorted(output_dir.glob(f"{doc_stem}_mark_temp_*.png"))
            if not mark_pngs:
                return {"success": False, "error": "No annotation pages generated"}
            
            # Open PDF and merge
            import fitz
            doc = fitz.open(pdf_path)
            merged_pages = []
            
            for i, page in enumerate(doc):
                mark_png = output_dir / f"{doc_stem}_mark_temp_{i}.png"
                if mark_png.exists():
                    page.insert_image(page.rect, filename=str(mark_png), overlay=True)
                
                # Render merged page to PNG
                mat = fitz.Matrix(2, 2)  # 2x zoom for clarity
                pix = page.get_pixmap(matrix=mat)
                merged_path = output_dir / f"{doc_stem}_{i}.png"
                pix.save(merged_path)
                merged_pages.append(merged_path)
                
                # Clean up temp mark PNG
                if mark_png.exists():
                    mark_png.unlink()
            
            doc.close()
            return {"success": True, "pages": merged_pages}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SETUP & STATUS
    # =========================================================================
    
    async def supernote_setup(self, domain: str, account: str, subfolder: str, 
                              base_path: str = "/Supernote") -> str:
        """
        Configure Supernote sync for a domain.
        
        Args:
            domain: Domain name to configure
            account: Storage account name (from storage_list_accounts)
            subfolder: Subfolder name on Supernote (e.g., "Burrillville Technology")
            base_path: Root folder where Supernote syncs (default: "/Supernote")
        """
        domain_path = self._get_domain_path(domain)
        if not domain_path.exists():
            return f"❌ Domain '{domain}' does not exist"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        if account not in storage_manager.accounts:
            return f"❌ Storage account '{account}' not found"
        
        base_path = base_path.strip().rstrip("/")
        if base_path and not base_path.startswith("/"):
            base_path = "/" + base_path
        
        config = {
            "account": account,
            "subfolder": subfolder,
            "base_path": base_path,
            "configured_at": datetime.now().isoformat(),
            "last_pull": None
        }
        
        self._ensure_directories(domain)
        self._save_config(domain, config)
        note_path, doc_path = self._get_remote_paths(config)
        
        return f"""✅ Supernote configured for {domain}

**Remote paths:**
- Notes: {note_path}/
- Documents: {doc_path}/

**Workflow:**
1. `supernote_pull("{domain}")` - Pull & clean remote
2. `supernote_list_unprocessed("{domain}")` - See inbox
3. `supernote_process_note("{domain}", "stem")` - Review via vision
4. `supernote_mark_note_processed("{domain}", "stem")` - Archive"""

    async def supernote_status(self, domain: str) -> str:
        """Show Supernote sync status for a domain."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for '{domain}'"
        
        plugin_path = self._get_plugin_path(domain)
        
        # Count items
        def count_pngs(d): return list(d.glob("*.png")) if d.exists() else []
        def count_files(d, ext): return list(d.glob(f"*{ext}")) if d.exists() else []
        
        inbox_notes = count_pngs(plugin_path / "inbox" / "notes")
        inbox_annot = count_pngs(plugin_path / "inbox" / "annotations")
        archive_notes = count_files(plugin_path / "archive" / "notes", ".note")
        archive_annot = count_files(plugin_path / "archive" / "annotations", ".mark")
        outbox = list((plugin_path / "outbox").glob("*")) if (plugin_path / "outbox").exists() else []
        
        # Count unique stems
        def count_stems(pngs):
            stems = set()
            for p in pngs:
                parts = p.stem.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    stems.add(parts[0])
            return stems
        
        note_stems = count_stems(inbox_notes)
        annot_stems = count_stems(inbox_annot)
        note_path, doc_path = self._get_remote_paths(config)
        
        return f"""📱 Supernote Status: {domain}
{'─' * 40}
**Config:** {config['account']} / {config['subfolder']}
**Remote:** {note_path}/

**Inbox (unprocessed):**
  Notes: {len(note_stems)} ({len(inbox_notes)} pages)
  Annotations: {len(annot_stems)} ({len(inbox_annot)} pages)

**Archive:** {len(archive_notes)} notes, {len(archive_annot)} annotations
**Outbox:** {len(outbox)} files

**Last pull:** {config.get('last_pull', 'Never')}"""

    async def supernote_list_remote(self, domain: str, path_type: str = "notes") -> str:
        """List files in the remote Supernote folder."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for '{domain}'"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        note_path, doc_path = self._get_remote_paths(config)
        remote_path = note_path if path_type == "notes" else doc_path
        
        try:
            files = await storage_manager.list_files(config["account"], remote_path)
            if not files:
                return f"📂 {remote_path} (empty)"
            
            lines = [f"📂 {remote_path}", "─" * 40]
            for f in files:
                size_str = f"{f.size / 1024:.1f}KB" if f.size else ""
                lines.append(f"  {f.name}  {size_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed: {e}"

    # =========================================================================
    # PULL PHASE
    # =========================================================================
    
    async def supernote_pull(self, domain: str, convert: bool = True) -> str:
        """
        Pull both notes and annotations from Supernote.
        
        Downloads, converts to PNG, archives originals, deletes from remote.
        
        Args:
            domain: Domain name
            convert: Convert to PNG (default: True) - kept for API compatibility
        """
        config = self._load_config(domain)
        if not config:
            return f"❌ Supernote not configured for '{domain}'"
        
        self._ensure_directories(domain)
        
        notes_result = await self.supernote_pull_notes(domain)
        annot_result = await self.supernote_pull_annotations(domain)
        
        config["last_pull"] = datetime.now().isoformat()
        self._save_config(domain, config)
        
        return f"""📥 Pull complete for {domain}

**Notes:**
{notes_result}

**Annotations:**
{annot_result}"""

    async def supernote_pull_notes(self, domain: str) -> str:
        """
        Pull .note files from Supernote.
        
        For each .note: download → convert to PNG → archive .note → delete from remote
        """
        config = self._load_config(domain)
        if not config:
            return "Not configured"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "Storage manager not available"
        
        self._ensure_directories(domain)
        plugin_path = self._get_plugin_path(domain)
        inbox_notes = plugin_path / "inbox" / "notes"
        archive_notes = plugin_path / "archive" / "notes"
        temp_dir = plugin_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        account = config["account"]
        note_path, _ = self._get_remote_paths(config)
        
        try:
            files = await storage_manager.list_files(account, note_path)
            note_files = [f for f in files if f.name.endswith(".note")]
            
            if not note_files:
                return "No notes on device"
            
            pulled, failed = [], []
            
            for f in note_files:
                stem = f.name.replace(".note", "")
                local_note = temp_dir / f.name
                
                try:
                    # 1. Download
                    result = await storage_manager.download(account, f"{note_path}/{f.name}", local_note)
                    if "fail" in result.lower() or "error" in result.lower():
                        failed.append(f"{stem}: download failed")
                        continue
                    
                    # 2. Convert to PNG
                    conv = self._convert_note_to_png(local_note, inbox_notes)
                    if not conv["success"]:
                        failed.append(f"{stem}: {conv['error']}")
                        continue
                    
                    pages = conv["pages"]
                    if not pages:
                        failed.append(f"{stem}: no pages")
                        continue
                    
                    # 3. Archive .note locally
                    shutil.move(str(local_note), str(archive_notes / f.name))
                    
                    # 4. Delete from remote
                    await storage_manager.delete(account, f"{note_path}/{f.name}")
                    
                    pulled.append(f"{stem} ({len(pages)} pages)")
                except Exception as e:
                    failed.append(f"{stem}: {e}")
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            lines = []
            if pulled:
                lines.append(f"✅ Pulled {len(pulled)}: " + ", ".join(pulled))
            if failed:
                lines.append(f"❌ Failed {len(failed)}: " + ", ".join(failed))
            return "\n".join(lines) if lines else "Nothing to pull"
        except Exception as e:
            return f"Pull failed: {e}"

    async def supernote_pull_annotations(self, domain: str) -> str:
        """
        Pull .mark annotation files from Supernote.
        
        Only pulls PDFs that have .mark files.
        For each .mark: download with PDF → merge to PNG → archive .mark → delete .mark from remote
        """
        config = self._load_config(domain)
        if not config:
            return "Not configured"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "Storage manager not available"
        
        if not PYMUPDF_AVAILABLE:
            return "PyMuPDF not installed"
        
        self._ensure_directories(domain)
        plugin_path = self._get_plugin_path(domain)
        inbox_annot = plugin_path / "inbox" / "annotations"
        archive_annot = plugin_path / "archive" / "annotations"
        temp_dir = plugin_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        account = config["account"]
        _, doc_path = self._get_remote_paths(config)
        
        try:
            files = await storage_manager.list_files(account, doc_path)
            mark_files = [f for f in files if f.name.endswith(".mark")]
            
            if not mark_files:
                return "No annotations on device"
            
            pulled, failed = [], []
            
            for f in mark_files:
                pdf_name = f.name[:-5]  # Remove ".mark"
                doc_stem = f.name[:-9]  # Remove ".pdf.mark"
                local_mark = temp_dir / f.name
                local_pdf = temp_dir / pdf_name
                
                try:
                    # 1. Download .mark
                    result = await storage_manager.download(account, f"{doc_path}/{f.name}", local_mark)
                    if "fail" in result.lower() or "error" in result.lower():
                        failed.append(f"{doc_stem}: mark download failed")
                        continue
                    
                    # 2. Download PDF
                    result = await storage_manager.download(account, f"{doc_path}/{pdf_name}", local_pdf)
                    if "fail" in result.lower() or "error" in result.lower():
                        failed.append(f"{doc_stem}: PDF download failed")
                        continue
                    
                    # 3. Merge to PNG
                    merge = self._convert_mark_to_merged_png(local_mark, local_pdf, inbox_annot)
                    if not merge["success"]:
                        failed.append(f"{doc_stem}: {merge['error']}")
                        continue
                    
                    pages = merge["pages"]
                    if not pages:
                        failed.append(f"{doc_stem}: no pages")
                        continue
                    
                    # 4. Archive .mark locally
                    shutil.move(str(local_mark), str(archive_annot / f.name))
                    
                    # 5. Delete .mark from remote (PDF stays)
                    await storage_manager.delete(account, f"{doc_path}/{f.name}")
                    
                    # Clean up local PDF
                    local_pdf.unlink(missing_ok=True)
                    
                    pulled.append(f"{doc_stem} ({len(pages)} pages)")
                except Exception as e:
                    failed.append(f"{doc_stem}: {e}")
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            lines = []
            if pulled:
                lines.append(f"✅ Pulled {len(pulled)}: " + ", ".join(pulled))
            if failed:
                lines.append(f"❌ Failed {len(failed)}: " + ", ".join(failed))
            return "\n".join(lines) if lines else "Nothing to pull"
        except Exception as e:
            return f"Pull failed: {e}"

    # =========================================================================
    # PROCESS PHASE
    # =========================================================================
    
    async def supernote_list_unprocessed(self, domain: str) -> str:
        """List notes and annotations waiting to be processed."""
        config = self._load_config(domain)
        if not config:
            return f"❌ Not configured for '{domain}'"
        
        plugin_path = self._get_plugin_path(domain)
        inbox_notes = plugin_path / "inbox" / "notes"
        inbox_annot = plugin_path / "inbox" / "annotations"
        
        def get_stems(d: Path) -> Dict[str, int]:
            stems = {}
            if d.exists():
                for png in d.glob("*.png"):
                    parts = png.stem.rsplit("_", 1)
                    stem = parts[0] if len(parts) == 2 and parts[1].isdigit() else png.stem
                    stems[stem] = stems.get(stem, 0) + 1
            return stems
        
        note_stems = get_stems(inbox_notes)
        annot_stems = get_stems(inbox_annot)
        
        lines = [f"📋 Unprocessed in {domain}", "─" * 40]
        
        if note_stems:
            lines.append(f"\n**Notes** ({len(note_stems)}):")
            for stem, pgs in sorted(note_stems.items()):
                lines.append(f"  📝 {stem} ({pgs} pages)")
        else:
            lines.append("\n**Notes:** (none)")
        
        if annot_stems:
            lines.append(f"\n**Annotations** ({len(annot_stems)}):")
            for stem, pgs in sorted(annot_stems.items()):
                lines.append(f"  ✏️ {stem} ({pgs} pages)")
        else:
            lines.append("\n**Annotations:** (none)")
        
        if note_stems or annot_stems:
            lines.append("\n**Next:**")
            if note_stems:
                ex = list(note_stems.keys())[0]
                lines.append(f'  supernote_process_note("{domain}", "{ex}")')
            if annot_stems:
                ex = list(annot_stems.keys())[0]
                lines.append(f'  supernote_process_annotation("{domain}", "{ex}")')
        
        return "\n".join(lines)

    async def supernote_process_note(self, domain: str, note_stem: str) -> Union[List[Any], str]:
        """
        Process a note via vision.
        
        Returns PNG pages as images for Claude to interpret.
        """
        if not IMAGE_SUPPORT:
            return "❌ Image support not available"
        
        config = self._load_config(domain)
        if not config:
            return f"❌ Not configured"
        
        plugin_path = self._get_plugin_path(domain)
        pages = sorted((plugin_path / "inbox" / "notes").glob(f"{note_stem}_*.png"))
        
        if not pages:
            return f"❌ Note '{note_stem}' not found in inbox"
        
        # Build result as proper MCP ContentBlock types
        # This avoids fastmcp serialization issues with mixed lists
        result = []
        result.append(TextContent(type="text", text=f"📝 **Note: {note_stem}** ({len(pages)} pages)\n\nReview and describe the content:\n"))
        
        for i, p in enumerate(pages):
            result.append(TextContent(type="text", text=f"\n**Page {i+1}:**"))
            # Convert Image to ImageContent directly
            img = Image(path=p)
            result.append(img.to_image_content())
        
        result.append(TextContent(type="text", text=f'\n---\nWhen done: `supernote_mark_note_processed("{domain}", "{note_stem}")`'))
        return result

    async def supernote_process_annotation(self, domain: str, doc_stem: str) -> Union[List[Any], str]:
        """
        Process an annotation via vision.
        
        Returns merged PNG (PDF + annotations) for Claude to interpret.
        """
        if not IMAGE_SUPPORT:
            return "❌ Image support not available"
        
        config = self._load_config(domain)
        if not config:
            return f"❌ Not configured"
        
        plugin_path = self._get_plugin_path(domain)
        pages = sorted((plugin_path / "inbox" / "annotations").glob(f"{doc_stem}_*.png"))
        
        if not pages:
            return f"❌ Annotation '{doc_stem}' not found in inbox"
        
        # Build result as proper MCP ContentBlock types
        result = []
        result.append(TextContent(type="text", text=f"✏️ **Annotation: {doc_stem}** ({len(pages)} pages)\n\nReview what was marked up:\n"))
        
        for i, p in enumerate(pages):
            result.append(TextContent(type="text", text=f"\n**Page {i+1}:**"))
            # Convert Image to ImageContent directly
            img = Image(path=p)
            result.append(img.to_image_content())
        
        result.append(TextContent(type="text", text=f'\n---\nWhen done: `supernote_mark_annotation_processed("{domain}", "{doc_stem}")`'))
        return result

    async def supernote_mark_note_processed(self, domain: str, note_stem: str) -> str:
        """Mark a note as processed. Moves PNGs from inbox to archive."""
        config = self._load_config(domain)
        if not config:
            return "❌ Not configured"
        
        plugin_path = self._get_plugin_path(domain)
        inbox = plugin_path / "inbox" / "notes"
        archive = plugin_path / "archive" / "notes"
        
        pages = list(inbox.glob(f"{note_stem}_*.png"))
        if not pages:
            return f"❌ Note '{note_stem}' not in inbox"
        
        for p in pages:
            shutil.move(str(p), str(archive / p.name))
        
        return f"✅ Archived '{note_stem}' ({len(pages)} pages)"

    async def supernote_mark_annotation_processed(self, domain: str, doc_stem: str) -> str:
        """Mark an annotation as processed. Moves PNGs from inbox to archive."""
        config = self._load_config(domain)
        if not config:
            return "❌ Not configured"
        
        plugin_path = self._get_plugin_path(domain)
        inbox = plugin_path / "inbox" / "annotations"
        archive = plugin_path / "archive" / "annotations"
        
        pages = list(inbox.glob(f"{doc_stem}_*.png"))
        if not pages:
            return f"❌ Annotation '{doc_stem}' not in inbox"
        
        for p in pages:
            shutil.move(str(p), str(archive / p.name))
        
        return f"✅ Archived '{doc_stem}' ({len(pages)} pages)"

    # =========================================================================
    # PUSH
    # =========================================================================
    
    async def supernote_push(self, domain: str) -> str:
        """Push documents from outbox to Supernote."""
        config = self._load_config(domain)
        if not config:
            return "❌ Not configured"
        
        storage_manager = self._get_storage_manager()
        if not storage_manager:
            return "❌ Storage manager not available"
        
        plugin_path = self._get_plugin_path(domain)
        outbox = plugin_path / "outbox"
        
        if not outbox.exists():
            return "📂 Outbox empty"
        
        files = [f for f in outbox.iterdir() if f.is_file()]
        if not files:
            return "📂 Outbox empty"
        
        _, doc_path = self._get_remote_paths(config)
        uploaded, failed = [], []
        
        for local_file in files:
            try:
                result = await storage_manager.upload(
                    config["account"], local_file, f"{doc_path}/{local_file.name}"
                )
                if "fail" not in result.lower() and "error" not in result.lower():
                    uploaded.append(local_file.name)
                    local_file.unlink()
                else:
                    failed.append(local_file.name)
            except Exception as e:
                failed.append(f"{local_file.name}: {e}")
        
        lines = [f"📤 Push for {domain}:"]
        if uploaded:
            lines.append(f"✅ Uploaded: {', '.join(uploaded)}")
        if failed:
            lines.append(f"❌ Failed: {', '.join(failed)}")
        return "\n".join(lines)

    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    async def supernote_md2pdf(self, domain: str, source: str, to_outbox: bool = True) -> str:
        """
        Convert markdown to PDF.
        
        Args:
            domain: Domain name
            source: Path to markdown file relative to domain
            to_outbox: Copy PDF to outbox for pushing (default: True)
        """
        if not REPORTLAB_AVAILABLE:
            return "❌ reportlab not installed"
        
        domain_path = self._get_domain_path(domain)
        md_path = domain_path / source
        
        if not md_path.exists():
            return f"❌ File not found: {source}"
        if md_path.suffix.lower() != ".md":
            return f"❌ Not markdown: {source}"
        
        pdf_path = md_path.with_suffix(".pdf")
        
        try:
            self._convert_md_to_pdf(md_path, pdf_path)
            result = f"✅ Created: {pdf_path.name}"
            
            if to_outbox:
                outbox = self._get_plugin_path(domain) / "outbox"
                outbox.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pdf_path, outbox / pdf_path.name)
                result += " (copied to outbox)"
            
            return result
        except Exception as e:
            return f"❌ Failed: {e}"

    @staticmethod
    def _build_ruled_space(width: float, num_lines: int = 4, line_spacing: float = None) -> 'Flowable':
        """Build a ruled annotation space for handwriting on Supernote.
        
        Returns a Flowable that draws light gray ruled lines.
        Args:
            width: Available width in points
            num_lines: Number of ruled lines to draw (default 4)
            line_spacing: Points between lines (default 22 — good for stylus)
        """
        if line_spacing is None:
            line_spacing = 22
        
        class RuledAnnotationSpace(Flowable):
            def __init__(self, w, n, spacing):
                Flowable.__init__(self)
                self.width = w
                self.num_lines = n
                self.line_spacing = spacing
                self.height = n * spacing + 6  # small top/bottom padding
            
            def draw(self):
                self.canv.setStrokeColor(colors.HexColor('#cccccc'))
                self.canv.setLineWidth(0.5)
                for i in range(self.num_lines):
                    y = self.height - 6 - (i * self.line_spacing)
                    self.canv.line(0, y, self.width, y)
        
        return RuledAnnotationSpace(width, num_lines, line_spacing)

    @staticmethod
    def _parse_markdown_table(lines: List[str]) -> List[List[str]]:
        rows = []
        for line in lines:
            line = line.strip()
            if line.startswith('|') and line.endswith('|'):
                cells = [c.strip() for c in line[1:-1].split('|')]
                if not all(re.match(r'^[-:]+$', c) for c in cells):
                    rows.append(cells)
        return rows

    def _convert_md_to_pdf(self, md_path: Path, pdf_path: Path = None) -> Path:
        """Convert markdown to PDF optimized for Supernote display.
        
        Supports:
            - # / ## / ### headings
            - **bold** text
            - Markdown tables
            - `- [ ]` / `- [x]` checkboxes (with nesting via indentation)
            - `<!-- pagebreak -->` forced page breaks
            - `<!-- space -->` ruled annotation lines for handwriting
            - `<!-- space:N -->` ruled annotation lines with N lines (default 4)
            - `---` horizontal rule / section separator
        """
        if pdf_path is None:
            pdf_path = md_path.with_suffix('.pdf')
        
        content = md_path.read_text()
        lines = content.split('\n')
        
        # Supernote-optimized margins (0.75" for safe pen area)
        available_width = 7.0 * inch  # letter width minus margins
        doc = SimpleDocTemplate(
            str(pdf_path), pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch
        )
        
        # Larger fonts for e-ink readability
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('T', parent=styles['Title'], fontSize=20, alignment=TA_CENTER, spaceAfter=18)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=16, spaceBefore=16, spaceAfter=8)
        h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=14, spaceBefore=12, spaceAfter=6)
        h4_style = ParagraphStyle('H4', parent=styles['Heading4'], fontSize=12, spaceBefore=10, spaceAfter=4)
        normal_style = ParagraphStyle('N', parent=styles['Normal'], fontSize=12, spaceAfter=8, leading=16)
        
        # Checkbox styles with indentation levels
        checkbox_style = ParagraphStyle(
            'CB0', parent=styles['Normal'], fontSize=12, spaceAfter=4, leading=18,
            leftIndent=0
        )
        checkbox_style_l1 = ParagraphStyle(
            'CB1', parent=styles['Normal'], fontSize=11, spaceAfter=3, leading=16,
            leftIndent=18
        )
        checkbox_style_l2 = ParagraphStyle(
            'CB2', parent=styles['Normal'], fontSize=11, spaceAfter=3, leading=16,
            leftIndent=36
        )
        
        # Bullet style (non-checkbox list items)
        bullet_style = ParagraphStyle(
            'BL0', parent=styles['Normal'], fontSize=12, spaceAfter=4, leading=18,
            leftIndent=0
        )
        bullet_style_l1 = ParagraphStyle(
            'BL1', parent=styles['Normal'], fontSize=11, spaceAfter=3, leading=16,
            leftIndent=18
        )
        
        story = []
        i = 0
        
        # Regex for checkbox lines: optional leading whitespace, then - [ ] or - [x]
        checkbox_re = re.compile(r'^(\s*)- \[([ xX])\]\s*(.*)')
        # Regex for annotation space directive with optional line count
        space_re = re.compile(r'^\s*<!--\s*space(?::(\d+))?\s*-->\s*$')
        # Regex for pagebreak directive
        pagebreak_re = re.compile(r'^\s*<!--\s*pagebreak\s*-->\s*$')
        # Regex for plain list items (non-checkbox)
        bullet_re = re.compile(r'^(\s*)[-*]\s+(.*)')
        
        while i < len(lines):
            raw_line = lines[i]
            line = raw_line.strip()
            
            # Empty lines — skip
            if not line:
                i += 1
                continue
            
            # Block quotes — skip
            if line.startswith('>'):
                i += 1
                continue
            
            # Pagebreak directive
            if pagebreak_re.match(line):
                story.append(PageBreak())
                i += 1
                continue
            
            # Annotation space directive
            space_match = space_re.match(line)
            if space_match:
                num_lines = int(space_match.group(1)) if space_match.group(1) else 4
                story.append(self._build_ruled_space(available_width, num_lines))
                i += 1
                continue
            
            # Horizontal rule — render as a thin line with spacing
            if line == '---' or line == '***' or line == '___':
                story.append(Spacer(1, 8))
                story.append(self._build_ruled_space(available_width, 1, 1))
                story.append(Spacer(1, 8))
                i += 1
                continue
            
            # Headings
            if line.startswith('#### '):
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line[5:])
                story.append(Paragraph(text, h4_style))
                i += 1
                continue
            if line.startswith('### '):
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line[4:])
                story.append(Paragraph(text, h3_style))
                i += 1
                continue
            if line.startswith('## '):
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line[3:])
                story.append(Paragraph(text, h2_style))
                i += 1
                continue
            if line.startswith('# '):
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line[2:])
                story.append(Paragraph(text, title_style))
                i += 1
                continue
            
            # Checkbox items
            cb_match = checkbox_re.match(raw_line)
            if cb_match:
                indent = len(cb_match.group(1))
                checked = cb_match.group(2) in ('x', 'X')
                text = cb_match.group(3)
                
                # Apply bold/formatting
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
                
                # Checkbox symbol
                box = '☑' if checked else '☐'
                
                # Pick style based on indentation depth
                if indent >= 4:
                    style = checkbox_style_l2
                elif indent >= 2:
                    style = checkbox_style_l1
                else:
                    style = checkbox_style
                
                story.append(Paragraph(f'{box}  {text}', style))
                i += 1
                continue
            
            # Plain list items (non-checkbox)
            bl_match = bullet_re.match(raw_line)
            if bl_match:
                indent = len(bl_match.group(1))
                text = bl_match.group(2)
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
                
                style = bullet_style_l1 if indent >= 2 else bullet_style
                story.append(Paragraph(f'•  {text}', style))
                i += 1
                continue
            
            # Tables
            if line.startswith('|'):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i])
                    i += 1
                i -= 1
                rows = self._parse_markdown_table(table_lines)
                if rows:
                    num_cols = len(rows[0])
                    t = Table(rows, colWidths=[available_width/num_cols]*num_cols)
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 10),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 10))
                i += 1
                continue
            
            # Regular paragraph text
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', line)
            story.append(Paragraph(line, normal_style))
            i += 1
        
        doc.build(story)
        return pdf_path

    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    def on_load(self) -> None:
        features = []
        if IMAGE_SUPPORT:
            features.append("image")
        if REPORTLAB_AVAILABLE:
            features.append("pdf")
        if PYMUPDF_AVAILABLE:
            features.append("annotations")
        logger.info(f"Supernote plugin v1.0.0 loaded ({', '.join(features)})")

    def on_unload(self) -> None:
        logger.info("Supernote plugin unloaded")
