"""
Google Drive Storage Adapter

Implements StorageAdapter interface for Google Drive.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
import logging

from ..interface import StorageAdapter, StorageAccount, FileInfo, FilePage

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_PATH = Path("/data/config/gdrive_token.json")


class GDriveAdapter(StorageAdapter):
    """Google Drive storage adapter."""
    
    adapter_type = "gdrive"
    
    def __init__(self, account: StorageAccount):
        super().__init__(account)
        self._service = None
        
        # Get token path from account config, with fallback to default
        self._token_path = Path(account.config.get("token_path", str(DEFAULT_TOKEN_PATH)))
    
    async def connect(self) -> bool:
        """Connect to Google Drive API."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            creds = None
            
            if self._token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(self._token_path))
                    logger.info("Loaded credentials from token file")
                except Exception as e:
                    logger.warning(f"Failed to load token file: {e}")
            
            if not creds:
                logger.error("No credentials available. Complete OAuth flow first.")
                return False
            
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self._token_path, 'w') as f:
                    f.write(creds.to_json())
                logger.info("Token refreshed and saved")
            
            self._service = build('drive', 'v3', credentials=creds)
            self._service.about().get(fields="user").execute()
            
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
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path like '/Supernote/Note' to a folder ID."""
        if not path or path == "/":
            return "root"
        
        if not path.startswith("/"):
            return path
        
        parts = [p for p in path.split("/") if p]
        current_id = "root"
        
        for part in parts:
            query = f"name='{part}' and '{current_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self._service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if not files:
                raise ValueError(f"Folder not found: {part} in path {path}")
            current_id = files[0]['id']
        
        return current_id
    
    async def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload file to Google Drive."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_name = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            
            try:
                parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            except ValueError:
                parent_id = "root"
            
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            existing = results.get('files', [])
            
            media = MediaFileUpload(str(local_path), resumable=True)
            
            if existing:
                file_id = existing[0]['id']
                self._service.files().update(fileId=file_id, media_body=media).execute()
                return f"✅ Updated: {remote_path}"
            else:
                metadata = {'name': file_name, 'parents': [parent_id]}
                self._service.files().create(body=metadata, media_body=media, fields='id').execute()
                return f"✅ Uploaded: {remote_path}"
                
        except Exception as e:
            return f"❌ Upload failed: {e}"
    
    async def download(self, remote_path: str, local_path: Path) -> str:
        """Download file from Google Drive."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            from googleapiclient.http import MediaIoBaseDownload
            
            file_name = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            
            try:
                parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            except ValueError:
                return f"❌ Path not found: {remote_path}"
            
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
    
    async def list_files(self, remote_path: str = "/", limit: int = 100, cursor: Optional[str] = None) -> FilePage:
        """List files in Google Drive folder."""
        if not self._service:
            return FilePage(files=[])
        
        try:
            parent_id = self._resolve_path(remote_path)
            
            query = f"'{parent_id}' in parents and trashed=false"
            request_params = {
                "q": query,
                "fields": "nextPageToken, files(id, name, size, modifiedTime, mimeType)",
                "orderBy": "name",
                "pageSize": min(limit, 1000)
            }
            if cursor:
                request_params["pageToken"] = cursor
            
            results = self._service.files().list(**request_params).execute()
            
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
                    mime_type=item.get('mimeType'),
                    id=item.get('id'),
                    provider="gdrive",
                    account=self.account.name
                ))
            
            return FilePage(
                files=files,
                next_cursor=results.get('nextPageToken')
            )
            
        except Exception as e:
            logger.error(f"List failed: {e}")
            return FilePage(files=[])
    
    async def exists(self, remote_path: str) -> bool:
        """Check if file exists in Google Drive."""
        if not self._service:
            return False
        
        try:
            file_name = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            
            try:
                parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            except ValueError:
                return False
            
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
            parent_path = str(Path(remote_path).parent)
            
            try:
                parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            except ValueError:
                return f"❌ Path not found: {remote_path}"
            
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                return f"❌ File not found: {remote_path}"
            
            self._service.files().delete(fileId=files[0]['id']).execute()
            return f"✅ Deleted: {remote_path}"
            
        except Exception as e:
            return f"❌ Delete failed: {e}"
    
    async def move(self, source_path: str, dest_path: str) -> str:
        """Move or rename a file."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            # Find source file
            source_name = Path(source_path).name
            source_parent = str(Path(source_path).parent)
            source_parent_id = self._resolve_path(source_parent) if source_parent != "." else "root"
            
            query = f"name='{source_name}' and '{source_parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                return f"❌ Source not found: {source_path}"
            
            file_id = files[0]['id']
            dest_name = Path(dest_path).name
            dest_parent = str(Path(dest_path).parent)
            dest_parent_id = self._resolve_path(dest_parent) if dest_parent != "." else "root"
            
            # Update file
            self._service.files().update(
                fileId=file_id,
                body={'name': dest_name},
                addParents=dest_parent_id,
                removeParents=source_parent_id,
                fields='id'
            ).execute()
            
            return f"✅ Moved: {source_path} → {dest_path}"
            
        except Exception as e:
            return f"❌ Move failed: {e}"
    
    async def copy(self, source_path: str, dest_path: str) -> str:
        """Copy a file."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            source_name = Path(source_path).name
            source_parent = str(Path(source_path).parent)
            source_parent_id = self._resolve_path(source_parent) if source_parent != "." else "root"
            
            query = f"name='{source_name}' and '{source_parent_id}' in parents and trashed=false"
            results = self._service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                return f"❌ Source not found: {source_path}"
            
            file_id = files[0]['id']
            dest_name = Path(dest_path).name
            dest_parent = str(Path(dest_path).parent)
            dest_parent_id = self._resolve_path(dest_parent) if dest_parent != "." else "root"
            
            self._service.files().copy(
                fileId=file_id,
                body={'name': dest_name, 'parents': [dest_parent_id]}
            ).execute()
            
            return f"✅ Copied: {source_path} → {dest_path}"
            
        except Exception as e:
            return f"❌ Copy failed: {e}"
    
    async def mkdir(self, remote_path: str) -> str:
        """Create a directory."""
        if not self._service:
            return "❌ Not connected to Google Drive"
        
        try:
            folder_name = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            self._service.files().create(body=metadata, fields='id').execute()
            
            return f"✅ Created folder: {remote_path}"
            
        except Exception as e:
            return f"❌ mkdir failed: {e}"
    
    async def rmdir(self, remote_path: str, recursive: bool = False) -> str:
        """Remove a directory."""
        # For Google Drive, delete works the same for files and folders
        return await self.delete(remote_path)
    
    async def get_info(self, remote_path: str) -> Optional[FileInfo]:
        """Get info about a specific file."""
        if not self._service:
            return None
        
        try:
            file_name = Path(remote_path).name
            parent_path = str(Path(remote_path).parent)
            parent_id = self._resolve_path(parent_path) if parent_path != "." else "root"
            
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self._service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime, mimeType)"
            ).execute()
            files = results.get('files', [])
            
            if not files:
                return None
            
            item = files[0]
            is_dir = item['mimeType'] == 'application/vnd.google-apps.folder'
            modified = None
            if 'modifiedTime' in item:
                modified = datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00'))
            
            return FileInfo(
                name=item['name'],
                path=remote_path,
                size=int(item.get('size', 0)),
                modified=modified,
                is_directory=is_dir,
                mime_type=item.get('mimeType'),
                id=item.get('id'),
                provider="gdrive",
                account=self.account.name
            )
            
        except Exception:
            return None
