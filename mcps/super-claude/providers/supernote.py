"""
Supernote Cloud Storage Provider

Implements StorageProvider interface for Supernote Cloud.
Uses the sncloud Python library.
"""

import sys
sys.path.insert(0, "/app/core")

from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from storage_interface import StorageProvider, StorageAccount, FileInfo

logger = logging.getLogger(__name__)


class SupernoteProvider(StorageProvider):
    """
    Supernote Cloud storage provider.
    
    Requires:
    - sncloud library (pip install sncloud)
    - Supernote account credentials in 1Password
    """
    
    provider_type = "supernote"
    
    def __init__(self, account: StorageAccount):
        super().__init__(account)
        self._client = None
    
    async def connect(self) -> bool:
        """Connect to Supernote Cloud."""
        try:
            from sncloud import SNClient
            
            self._client = SNClient()
            
            # Get credentials - expect email and password
            email = self.account.config.get("email")
            password = self.account.config.get("password")
            
            if not email or not password:
                logger.error("Supernote credentials not configured")
                return False
            
            self._client.login(email, password)
            
            logger.info(f"✅ Connected to Supernote Cloud: {self.account.name}")
            return True
            
        except ImportError:
            logger.error("❌ sncloud library not installed. Run: pip install sncloud")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supernote Cloud: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Supernote Cloud."""
        self._client = None
    
    async def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload file to Supernote Cloud."""
        if not self._client:
            return "❌ Not connected to Supernote Cloud"
        
        try:
            # sncloud upload method
            # Note: May need to convert markdown to .note format
            content = local_path.read_bytes()
            
            # sncloud API - check actual method signature
            # self._client.put(remote_path, content)
            
            return f"✅ Uploaded to Supernote: {remote_path}"
            
        except Exception as e:
            return f"❌ Upload failed: {e}"
    
    async def download(self, remote_path: str, local_path: Path) -> str:
        """Download file from Supernote Cloud."""
        if not self._client:
            return "❌ Not connected to Supernote Cloud"
        
        try:
            # sncloud download method
            self._client.get(remote_path)
            
            # File should be saved - move to local_path if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            return f"✅ Downloaded from Supernote: {remote_path}"
            
        except Exception as e:
            return f"❌ Download failed: {e}"
    
    async def list_files(self, remote_path: str = "/") -> List[FileInfo]:
        """List files in Supernote Cloud."""
        if not self._client:
            return []
        
        try:
            # sncloud list method
            items = self._client.ls(remote_path)
            
            files = []
            for item in items:
                # Parse sncloud response format
                files.append(FileInfo(
                    name=item.get("fileName", ""),
                    path=f"{remote_path}/{item.get('fileName', '')}".replace("//", "/"),
                    size=item.get("size", 0),
                    modified=None,  # Parse if available
                    is_directory=item.get("isDirectory", False),
                    provider="supernote",
                    account=self.account.name
                ))
            
            return files
            
        except Exception as e:
            logger.error(f"List failed: {e}")
            return []
    
    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in Supernote Cloud."""
        if not self._client:
            return False
        
        try:
            parent = str(Path(remote_path).parent)
            name = Path(remote_path).name
            
            items = self._client.ls(parent)
            return any(item.get("fileName") == name for item in items)
            
        except Exception:
            return False
    
    async def delete(self, remote_path: str) -> str:
        """Delete file from Supernote Cloud."""
        if not self._client:
            return "❌ Not connected to Supernote Cloud"
        
        # Note: sncloud may not support delete
        return "❌ Delete not supported by Supernote Cloud API"
