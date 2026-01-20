# Super Claude Features

## Core Tools

### Session Management
| Tool | Description |
|------|-------------|
| `session_start` | Initialize session with plugin/domain detection, auto-loads matching domain |
| `ping` | Health check, returns token expiry warnings if within 14 days |

### Filesystem (sandboxed to /data)
| Tool | Description |
|------|-------------|
| `fs_list` | List directory contents |
| `fs_read` | Read file contents |
| `fs_write` | Write/overwrite file |
| `fs_append` | Append to file |
| `fs_delete` | Delete file |
| `fs_mkdir` | Create directory |
| `fs_rmdir` | Remove directory |
| `fs_move` | Move/rename file or directory |
| `fs_copy` | Copy file or directory |

### Shell & Docker
| Tool | Description |
|------|-------------|
| `shell_exec` | Execute bash commands in container |
| `docker_ps` | List containers |
| `docker_logs` | Get container logs |
| `docker_start` | Start stopped container |
| `docker_stop` | Stop running container |
| `docker_restart` | Restart container |

### Context System
| Tool | Description |
|------|-------------|
| `context_list` | Show all domains with descriptions and trigger keywords |
| `context_load` | Load a domain's main markdown file + INSTRUCTIONS.md if present |
| `context_get` | Get specific file from domain's context/ folder |
| `context_update` | Update key-value in domain's state.json |
| `instructions_get` | Get instructions for a domain (or global if empty string) |
| `instructions_set` | Set instructions for a domain (or global if empty string) |

**Instructions auto-loading:**
- `session_start()` loads global `/data/INSTRUCTIONS.md`
- `context_load(domain)` loads `domains/{domain}/INSTRUCTIONS.md` if it exists

### Publishing
| Tool | Description |
|------|-------------|
| `publish` | Copy file to web-accessible outputs directory |
| `publish_list` | List published files |
| `unpublish` | Remove published file |

### Token Management
| Tool | Description |
|------|-------------|
| `token_status` | Check OAuth token expiration |
| `token_record` | Record new token after generation |

---

## Core Services

Core Services provide platform-agnostic access to external capabilities. Each service defines an interface (ABC), and adapters implement that interface for specific platforms. Users configure named accounts that reference adapters and credentials.

See [architecture.md](architecture.md) for the full Core Services architecture.

### Storage Service

Cloud storage abstraction for file operations.

| Tool | Description |
|------|-------------|
| `storage_list_accounts` | Show configured storage accounts |
| `storage_add_account` | Add new storage account |
| `storage_remove_account` | Remove storage account |
| `storage_list_files` | List files in account |
| `storage_download` | Download file from cloud |
| `storage_upload` | Upload file to cloud |

**Adapters:** GDrive (active), OneDrive (planned), Dropbox (planned)

**Interface:** `StorageAdapter` ABC with: `connect`, `disconnect`, `upload`, `download`, `list_files`, `exists`, `delete`, `mkdir`, `get_info`

### Mail Service

Email operations across providers.

| Tool | Description |
|------|-------------|
| `mail_list_accounts` | Show configured mail accounts |
| `mail_add_account` | Add new mail account |
| `mail_remove_account` | Remove mail account |
| `mail_list_folders` | List mailbox folders |
| `mail_list_messages` | List messages in folder (with filters) |
| `mail_get_message` | Get full message with body/attachments |
| `mail_send` | Send new message |
| `mail_reply` | Reply to message |
| `mail_forward` | Forward message |
| `mail_move` | Move message to folder |
| `mail_delete` | Delete message |
| `mail_search` | Search messages |

**Adapters:** Gmail (planned), Outlook (planned), IMAP (planned)

**Interface:** `MailAdapter` ABC with: `connect`, `disconnect`, `list_folders`, `list_messages`, `get_message`, `send`, `reply`, `forward`, `move`, `delete`, `search`

### Calendar Service

Calendar operations across providers.

| Tool | Description |
|------|-------------|
| `calendar_list_accounts` | Show configured calendar accounts |
| `calendar_add_account` | Add new calendar account |
| `calendar_remove_account` | Remove calendar account |
| `calendar_list_calendars` | List available calendars |
| `calendar_list_events` | List events (with date range) |
| `calendar_get_event` | Get full event details |
| `calendar_create_event` | Create new event |
| `calendar_update_event` | Update existing event |
| `calendar_delete_event` | Delete event |
| `calendar_find_free_time` | Find available time slots |

**Adapters:** GCal (planned), OutlookCal (planned), CalDAV (planned)

**Interface:** `CalendarAdapter` ABC with: `connect`, `disconnect`, `list_calendars`, `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`, `find_free_time`

---

## Plugin System

Plugins extend Super Claude with additional capabilities. Located in `/data/mcps/super-claude/plugins/`.

### op_auth (1Password)
| Tool | Description |
|------|-------------|
| `auth_get` | Retrieve secret from 1Password by item name |
| `auth_get_ref` | Retrieve secret using full 1Password reference URI |
| `auth_set` | Create new item in 1Password |

### supernote (Domain Sync)

Syncs files between Super Claude domains and Supernote devices via cloud storage. Uses the Storage Service rather than talking to Supernote directly.

| Tool | Description |
|------|-------------|
| `supernote_setup` | Configure sync for a domain (account, subfolder, options) |
| `supernote_status` | Show sync config and local file counts |
| `supernote_list_remote` | List files in remote Note/ or Document/ folder |
| `supernote_list_notes` | List available notes with page counts |
| `supernote_read_note` | Read all pages of a note as images |
| `supernote_read_page` | Read single page of a note as image |
| `supernote_pull` | Download .note files from cloud to domain |
| `supernote_push` | Upload documents from domain to cloud |

**Per-domain config** (`domains/{name}/plugins/supernote/config.json`):
```json
{
  "account": "personal",
  "subfolder": "burrillville",
  "sync_notes": true,
  "sync_documents": true,
  "convert_to": ["pdf", "png"]
}
```

---

## Domain System

Domains are isolated knowledge contexts. Each contains:

```
domains/{name}/
├── {name}.md      # Always loaded - personality, goals, interaction style
├── state.json     # Session state - lightweight, changes often
├── context/       # Reference files - loaded on demand
└── plugins/       # Per-domain plugin data (e.g., supernote sync)
```

**Trigger keywords**: Domains define keywords in `config/domain_triggers.json`. When `session_start` sees matching keywords, it auto-loads the domain.

**Current domains**: Run `context_list` to see all available domains with their triggers.

---

## Authentication

- **OAuth 2.0** with authorization_code + PKCE flow
- **JWT tokens** with 180-day expiry
- Credentials stored in 1Password
- Token status visible via `token_status` or in `ping` warnings

---

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `https://zanni.synology.me/mcp` | Main Super Claude MCP |
| `https://zanni.synology.me/ops` | Ops container for mutual administration |

---

## Integration Points

- **Claude.ai**: Custom MCP connector with OAuth
- **Claude Code**: JWT bearer token authentication
- **Claude Mobile**: Same as web, works via MCP connector
