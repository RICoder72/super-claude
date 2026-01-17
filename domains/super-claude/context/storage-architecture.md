# Storage Architecture

Super Claude provides an abstract storage layer that allows plugins and tools to work with cloud storage without knowing or caring about the underlying provider.

## Design Principle

**Plugins should never know which cloud service they're using.** They just call:
```python
storage_list_files(account="personal", path="/Documents")
storage_download(account="personal", remote_path="/file.pdf", local_path="/data/downloads/file.pdf")
storage_upload(account="work", local_path="/data/report.docx", remote_path="/Reports/report.docx")
```

The storage manager routes to the correct provider (Google Drive, Dropbox, OneDrive, etc.) based on the account name.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  MCP Tools (Abstract Interface)                     │
│  storage_list_accounts                              │
│  storage_list_files(account, path)                  │
│  storage_download(account, remote_path, local_path) │
│  storage_upload(account, local_path, remote_path)   │
│  storage_add_account / storage_remove_account       │
└───────────────────────┬─────────────────────────────┘
                        │ routes by account name
┌───────────────────────▼─────────────────────────────┐
│  Storage Manager (/app/core/storage_manager.py)     │
│  - Loads accounts from /data/config/storage_accounts│
│  - Creates provider instances on demand             │
│  - Handles connection lifecycle & token refresh     │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐
   │ gdrive  │    │ supernote│    │ (future) │
   │ provider│    │ provider │    │ dropbox  │
   └─────────┘    └──────────┘    └──────────┘
```

## Components

### Storage Interface (`/app/core/storage_interface.py`)

Defines the contract all providers must implement:

```python
class StorageProvider(ABC):
    async def connect() -> bool
    async def disconnect() -> None
    async def upload(local_path, remote_path) -> str
    async def download(remote_path, local_path) -> str
    async def list_files(remote_path) -> List[FileInfo]
    async def exists(remote_path) -> bool
    async def delete(remote_path) -> str
```

### Storage Manager (`/app/core/storage_manager.py`)

Routes requests to the correct provider based on account name. Handles:
- Loading account config from `/data/config/storage_accounts.json`
- Registering provider types at startup
- Creating provider instances on demand
- Connection lifecycle management

### Providers (`/app/providers/`)

Each provider implements `StorageProvider` for a specific cloud service:

| Provider | File | Status |
|----------|------|--------|
| Google Drive | `gdrive.py` | ✅ Working |
| Supernote | `supernote.py` | 🔧 Placeholder |
| Dropbox | (future) | — |
| OneDrive | (future) | — |

## Account Configuration

Accounts are stored in `/data/config/storage_accounts.json`:

```json
{
  "accounts": {
    "personal": {
      "provider": "gdrive",
      "credentials_ref": "op://Key Vault/Google Drive OAuth - Personal",
      "config": {}
    },
    "work": {
      "provider": "gdrive",
      "credentials_ref": "op://Key Vault/Google Drive OAuth - Work",
      "config": {"root_path": "/Work Documents"}
    }
  }
}
```

## Adding a New Account

```
storage_add_account(
    name="personal",
    provider="gdrive",
    credentials_ref="op://Key Vault/Google Drive OAuth - Personal"
)
```

## Google Drive Setup

Google Drive uses OAuth 2.0. The token file is stored at `/data/config/gdrive_token.json`.

**First-time setup:**
1. Create OAuth credentials in Google Cloud Console
2. Store credentials in 1Password
3. Complete OAuth flow (one-time browser authorization)
4. Token is stored and auto-refreshed

See `gdrive-setup.md` for detailed setup instructions.

## Adding a New Provider

1. Create `providers/{provider}.py` implementing `StorageProvider`
2. Register in `providers/__init__.py`
3. Server auto-registers at startup

Example skeleton:

```python
from storage_interface import StorageProvider, StorageAccount, FileInfo

class DropboxProvider(StorageProvider):
    provider_type = "dropbox"
    
    async def connect(self) -> bool:
        # Initialize API client
        pass
    
    async def list_files(self, remote_path: str) -> List[FileInfo]:
        # Return file listing
        pass
    
    # ... implement other methods
```

## Why This Design?

**Separation of concerns**: Plugins focus on their domain logic (syncing Supernote files, backing up domains, etc.) without coupling to specific cloud providers.

**Easy to add providers**: New storage backends are just a Python file implementing a well-defined interface.

**Account flexibility**: Users can have multiple accounts of the same provider type (personal GDrive, work GDrive) or mix providers.

**Credential isolation**: All secrets flow through 1Password references, never hardcoded.
