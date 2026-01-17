"""
Google Drive Storage Provider

Implements StorageProvider interface for Google Drive.
"""

import sys
sys.path.insert(0, "/app/core")

from pathlib import Path
from typing import List, Optional
from datetime import datetime
import json
import logging

from storage_interface import StorageProvider, StorageAccount, FileInfo

logger = logging.getLogger(__name__)


class GoogleDriveProvider(StorageProvider):
    """
    Google Drive storage provider.
    
    Requires:
    - google-api-python-client
    - google-auth-oauthlib
    - Credentials stored in 1Password
    """
    
    provider_type = "gdrive"
    
    def __init__(self, account: StorageAccount):
        super().__init__(account)
        self._service = None
        self._root_folder_id = None
    
    async def connect(self) -> bool:
        """Connect to Google Drive API."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            # Get credentials from 1Password
            # Expected format: JSON with token info
            # For now, placeholder - actual implementation would call auth_get
            creds_json = self.account.config.get("credentials_json")
            if not creds_json:
                logger.error("No credentials configured for Google Drive")
                return False
            
            creds_data = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
            creds = Credentials.from_authorized_user_info(creds_data)
            
            self._service = build('drive', 'v3', credentials=creds)
            
            # Get or create root folder if specified
            root_path = self.account.config.get("root_path", "/SuperClaude")
            if root_path and root_path != "/":
                self._root_folder_id = await self._ensure_folder(root_path)
            
            logger.info(f"✅ Connected to Google Drive: {self.account.name}")
            return True
            
        except ImportError:
            logger.error("❌ Google API libraries not installed")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Google Drive: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Google Drive."""
        self._service = None
        self._root_folder_id = None
    
    async def _ensure_folder(self, path: str) -> Optional[str]:
        """Ensure folder exists, create if needed. Returns folder ID."""
        if not self._service:
            return None
        
        parts = [p for p in path.split("/") if p]
        parent_id = "root"
        
        for part in parts:
            # Search for folder
            query = f"name='{part}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self._service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                parent_id = files[0]['id']
            else:
                # Create folder
                metadata = {
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self._service.files().create(body=metadata, fields='id').execute()
                parent_id = folder['id']
        
        return parent_id
    
    def _get_parent_id(self, remote_path: str) -> str:
        """Get parent folder ID for a path."""
        if self._root_folder_id:
            return self._root_folder_id
        return "root"
    
    async def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload file to Google Drive."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_name = Path(remote_path).name
            parent_id = self._get_parent_id(remote_path)
            
            # Check if file exists
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            existing = results.get('files', [])
            
            media = MediaFileUpload(str(local_path), resumable=True)
            
            if existing:
                # Update existing
                file_id = existing[0]['id']
                self._service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                return f"✅ Updated: {remote_path}"
            else:
                # Create new
                metadata = {
                    'name': file_name,
                    'parents': [parent_id]
                }
                self._service.files().create(
                    body=metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                return f"✅ Uploaded: {remote_path}"
                
        except Exception as e:
            return f"❌ Upload failed: {e}"
    
    async def download(self, remote_path: str, local_path: Path) -> str:
        """Download file from Google Drive."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io
            
            file_name = Path(remote_path).name
            parent_id = self._get_parent_id(remote_path)
            
            # Find file
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                return f"❌ File not found: {remote_path}"
            
            file_id = files[0]['id']
            request = self._service.files().get_media(fileId=file_id)
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return f"✅ Downloaded: {remote_path} → {local_path}"
            
        except Exception as e:
            return f"❌ Download failed: {e}"
    
    async def list_files(self, remote_path: str = "/") -> List[FileInfo]:
        """List files in Google Drive folder."""
        if not self._service:
            return []
        
        try:
            parent_id = self._get_parent_id(remote_path)
            
            query = f"'{parent_id}' in parents and trashed=false"
            results = self._service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime, mimeType)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                is_dir = item['mimeType'] == 'application/vnd.google-apps.folder'
                modified = None
                if 'modifiedTime' in item:
                    modified = datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00'))
                
                files.append(FileInfo(
                    name=item['name'],
                    path=f"{remote_path}/{item['name']}".replace("//", "/"),
                    size=int(item.get('size', 0)),
                    modified=modified,
                    is_directory=is_dir,
                    provider="gdrive",
                    account=self.account.name
                ))
            
            return files
            
        except Exception as e:
            logger.error(f"List failed: {e}")
            return []
    
    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in Google Drive."""
        if not self._service:
            return False
        
        try:
            file_name = Path(remote_path).name
            parent_id = self._get_parent_id(remote_path)
            
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            
            return len(results.get('files', [])) > 0
            
        except Exception:
            return False
    
    async def delete(self, remote_path: str) -> str:
        """Delete file from Google Drive."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            file_name = Path(remote_path).name
            parent_id = self._get_parent_id(remote_path)
            
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                return f"❌ File not found: {remote_path}"
            
            self._service.files().delete(fileId=files[0]['id']).execute()
            return f"✅ Deleted: {remote_path}"
            
        except Exception as e:
            return f"❌ Delete failed: {e}"
