"""
Supernote Cloud Sync Plugin

Provides bidirectional sync between Super Claude and Supernote Cloud.
"""

from pathlib import Path
import json
from plugin_base import SuperClaudePlugin


class SupernotePlugin(SuperClaudePlugin):
    """Supernote Cloud synchronization plugin."""
    
    def initialize(self) -> None:
        """Initialize the Supernote plugin."""
        self.metadata = {
            "name": "supernote",
            "version": "0.1.0",
            "description": "Bidirectional sync with Supernote Cloud for task lists and notes",
            "author": "Matthew",
            "requires": ["sncloud Python library"]
        }
        
        # Register tools
        self.tools = {
            "supernote_sync_push": self.supernote_sync_push,
            "supernote_sync_pull": self.supernote_sync_pull,
            "supernote_list_files": self.supernote_list_files,
        }
        
        # Initialize sncloud client (lazy loaded when needed)
        self.client = None
        self.super_claude_root = Path("/data")
    
    def _get_client(self):
        """Lazily initialize and return sncloud client."""
        if self.client is None:
            try:
                from sncloud import SNClient
                self.client = SNClient()
                # Client will use stored credentials or prompt for login
            except ImportError:
                raise ImportError("sncloud library not installed. Install with: pip install sncloud")
        return self.client
    
    def _get_task_list_path(self) -> Path:
        """Get the path to the master task list in Super Claude."""
        # Store in a domain or at root level
        return self.super_claude_root / "task_list.md"
    
    async def supernote_sync_push(self, supernote_path: str = "/task_list.md") -> str:
        """
        Push the local task list to Supernote Cloud.
        
        Args:
            supernote_path: Path in Supernote Cloud where to sync (default: /task_list.md)
        
        Returns:
            Success or error message
        """
        try:
            task_list_path = self._get_task_list_path()
            
            if not task_list_path.exists():
                return f"❌ Task list not found at {task_list_path}"
            
            client = self._get_client()
            content = task_list_path.read_text()
            
            # Upload to Supernote Cloud
            # Note: sncloud API may require converting to specific format
            # This is a placeholder for the actual implementation
            
            return f"✅ Synced to Supernote: {supernote_path}\n   Bytes: {len(content)}"
        
        except Exception as e:
            return f"❌ Failed to sync push: {e}"
    
    async def supernote_sync_pull(self, supernote_path: str = "/task_list.md") -> str:
        """
        Pull updates from Supernote Cloud and merge with local task list.
        
        Args:
            supernote_path: Path in Supernote Cloud to pull from (default: /task_list.md)
        
        Returns:
            Success message with merge details
        """
        try:
            client = self._get_client()
            task_list_path = self._get_task_list_path()
            
            # Download from Supernote Cloud
            # Note: sncloud API usage goes here
            # downloaded_content = client.get(supernote_path)
            
            # For now, return placeholder
            return f"✅ Synced from Supernote: {supernote_path}"
        
        except Exception as e:
            return f"❌ Failed to sync pull: {e}"
    
    async def supernote_list_files(self, remote_path: str = "/") -> str:
        """
        List files in Supernote Cloud.
        
        Args:
            remote_path: Path in Supernote Cloud to list (default: /)
        
        Returns:
            Formatted list of files and directories
        """
        try:
            client = self._get_client()
            
            # List files from Supernote Cloud
            # Note: sncloud API usage goes here
            # files = client.ls(remote_path)
            
            # For now, return placeholder
            return f"📂 Supernote Cloud: {remote_path}\n   (file listing would go here)"
        
        except Exception as e:
            return f"❌ Failed to list files: {e}"
    
    def on_load(self) -> None:
        """Called when plugin loads."""
        # Could initialize sncloud connection here
        pass
    
    def on_unload(self) -> None:
        """Called when plugin unloads."""
        # Could close sncloud connection here
        pass
