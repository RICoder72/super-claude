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
| `context_load` | Load a domain's main markdown file |
| `context_get` | Get specific file from domain's context/ folder |
| `context_update` | Update key-value in domain's state.json |

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

## Plugin System

Plugins extend Super Claude with additional capabilities. Located in `/data/mcps/super-claude/plugins/`.

### op_auth (1Password)
| Tool | Description |
|------|-------------|
| `auth_get` | Retrieve secret from 1Password by item name |
| `auth_get_ref` | Retrieve secret using full 1Password reference URI |
| `auth_set` | Create new item in 1Password |

### storage (Cloud Storage Abstraction)
| Tool | Description |
|------|-------------|
| `storage_list_accounts` | Show configured storage accounts |
| `storage_add_account` | Add new storage account |
| `storage_remove_account` | Remove storage account |
| `storage_list_files` | List files in account |
| `storage_download` | Download file from cloud |
| `storage_upload` | Upload file to cloud |

**Supported providers**: Google Drive (active), OneDrive (planned), Dropbox (planned)

**Account system**: Named accounts (e.g., "personal", "work") abstract away provider details. Plugins reference accounts by name.

### supernote (Domain Sync)

Syncs files between Super Claude domains and Supernote devices via cloud storage. Does NOT talk to Supernote directly — uses the storage abstraction layer to sync with whatever cloud provider the Supernote device syncs to.

| Tool | Description |
|------|-------------|
| `supernote_setup` | Configure sync for a domain (account, subfolder, options) |
| `supernote_status` | Show sync config and local file counts |
| `supernote_list_remote` | List files in remote Note/ or Document/ folder |
| `supernote_pull` | Download .note files from cloud to domain |
| `supernote_push` | Upload documents from domain to cloud |

**Architecture**:
```
Supernote Device → (auto-sync) → Cloud Storage ← (storage_* tools) ← Super Claude
```

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

**Local folder structure**:
```
domains/{name}/plugins/supernote/
├── config.json    # Sync configuration
├── notes/         # .note files pulled from device
├── documents/     # Files to push to device
└── converted/     # PDF/PNG conversions (local only)
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
