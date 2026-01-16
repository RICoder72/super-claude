# File Structure

What's in each folder and why.

```
/volume1/docker/super-claude/     (host)
/data/                            (inside container)
│
├── mcps/
│   └── super-claude/
│       ├── server.py             # The MCP server - all tools defined here
│       ├── Dockerfile            # Container build instructions
│       └── pyproject.toml        # Python dependencies
│
├── shared/
│   └── op_client.py              # 1Password helper, shared across MCPs
│
├── config/
│   └── .env                      # Environment variables (1Password token)
│
├── domains/
│   ├── super-claude/             # Meta domain - this infrastructure
│   │   ├── super-claude.md       # Architecture, tools, overview
│   │   ├── state.json            # Version, deploy status
│   │   └── context/
│   │       ├── why.md            # Origin story, design principles
│   │       ├── setup-guide.md    # Deployment from scratch
│   │       ├── operations.md     # Day-to-day ops, troubleshooting
│   │       ├── domain-philosophy.md  # How to think about domains
│   │       ├── file-structure.md # This file
│   │       ├── roadmap.md        # Planned features
│   │       ├── decisions.md      # Architecture decision records
│   │       └── changelog.md      # What changed when
│   │
│   ├── projects/                 # Project tracking domain
│   │   ├── projects.md           # Active projects
│   │   ├── state.json            # Current focus
│   │   └── context/
│   │       ├── ideas.md          # Backlog/someday
│   │       └── completed.md      # Archive
│   │
│   └── {other domains}/          # MSF, GRC, etc.
│
└── outputs/                      # Web-accessible published files
```

## Key Files Explained

### server.py
The heart of Super Claude. Defines all MCP tools:
- Health: `ping`
- Session: `session_start`
- Auth: `auth_get`, `auth_get_ref`, `auth_set`
- Filesystem: `fs_list`, `fs_read`, `fs_write`, `fs_delete`, `fs_mkdir`, `fs_rmdir`, `fs_move`, `fs_copy`, `fs_append`
- Shell: `shell_exec`
- Docker: `docker_ps`, `docker_logs`, `docker_restart`, `docker_stop`, `docker_start`
- Context: `context_load`, `context_get`, `context_update`, `context_list`
- Publish: `publish`, `publish_list`, `unpublish`
- Token: `token_status`, `token_record`
- Ops: `rebuild_ops`

When you add a tool, add it here.

### op_client.py
Shared 1Password integration. Uses the Python SDK for secret management. Any MCP can import this.
- **Read secrets**: `get_secret()`, `get_secret_by_ref()` 
- **Create secrets**: `create_item()` - stores new API keys, tokens, credentials

### .env
Contains `OP_SERVICE_ACCOUNT_TOKEN`. Never commit this to git. The deploy command uses `--env-file` to inject it.

### Domain Files
Each domain follows the same pattern:
- `{name}.md` - Main context, always loaded
- `state.json` - Lightweight state
- `context/` - Reference files, loaded on demand

## What Goes Where

| Content | Location |
|---------|----------|
| New MCP tool | `mcps/super-claude/server.py` |
| Shared Python code | `shared/` |
| Secrets/tokens | `config/.env` + 1Password |
| Domain knowledge | `domains/{name}/` |
| Published files | `outputs/` |

## Git Strategy (Planned)

```
# Public repo (open source)
super-claude/
├── mcps/
├── shared/
├── domains/_template/    # Example only
└── README.md

# Private repo (your data)  
super-claude-domains/
├── msf/
├── grc/
├── projects/
└── super-claude/
```

The `.gitignore` in the main repo will exclude `domains/*` except `_template/`.
