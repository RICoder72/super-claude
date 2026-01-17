# Google Drive Setup

## Status: ✅ Complete

Google Drive is configured and working through the abstract storage layer.

- **Account name**: `personal`
- **Provider**: gdrive  
- **Token file**: `/data/config/gdrive_token.json`
- **Credentials**: Stored in 1Password as "Google Drive OAuth - Personal"

## Usage

Use the abstract storage tools (not provider-specific):

```
# List accounts
storage_list_accounts()

# List files
storage_list_files(account="personal", path="/")
storage_list_files(account="personal", path="/Supernote/Note")

# Download
storage_download(account="personal", remote_path="/file.pdf", local_path="/data/downloads/file.pdf")

# Upload  
storage_upload(account="personal", local_path="/data/report.docx", remote_path="/Reports/report.docx")
```

## Adding Another Google Drive Account

If you need a second Google Drive account (e.g., work):

1. **Create new OAuth credentials** in Google Cloud Console (or reuse existing)
2. **Store in 1Password**: `Google Drive OAuth - Work`
3. **Add account**:
   ```
   storage_add_account(
       name="work",
       provider="gdrive", 
       credentials_ref="op://Key Vault/Google Drive OAuth - Work"
   )
   ```
4. **Complete OAuth flow** (one-time browser authorization)

## Token Refresh

Tokens auto-refresh when expired. The refresh token is stored in the token file and used to obtain new access tokens without user interaction.

If you see auth errors, the refresh token may have been revoked. Re-run the OAuth flow:
1. Delete `/data/config/gdrive_token.json`
2. Use auth flow to get new tokens

## First-Time Setup (Reference)

This was completed on 2026-01-16. For reference if setting up again:

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project "Super Claude"
3. Enable **Google Drive API**
4. Go to **APIs & Services** → **Credentials**
5. Configure OAuth consent screen (External, add yourself as test user)
6. Create **OAuth client ID** (Desktop app type)
7. Copy Client ID and Client Secret

### 2. Store Credentials

Credentials stored in 1Password:
- Item: "Google Drive OAuth - Personal"
- Fields: `client_id`, `client_secret`

Credentials file created at `/data/config/gdrive_credentials.json`

### 3. OAuth Flow

1. Generated authorization URL with scopes:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/drive.file`
2. User visited URL, granted access
3. Authorization code exchanged for tokens
4. Token saved to `/data/config/gdrive_token.json`

## Architecture

See `storage-architecture.md` for how Google Drive fits into the abstract storage layer.
