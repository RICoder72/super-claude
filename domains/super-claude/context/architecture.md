# Super Claude Architecture

## System Overview

```
┌─────────────────────────────────────────────────────┐
│  Claude Interfaces                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Mobile   │  │ Web      │  │ Code     │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
└───────┼─────────────┼─────────────┼────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │ (MCP over HTTPS)
                      ▼
        ┌─────────────────────────────┐
        │  nginx router (:8080)       │
        │  ├── /mcp → super-claude    │
        │  ├── /ops → super-claude-ops│
        │  └── /auth → auth-service   │
        └─────────────┬───────────────┘
                      │
        ┌─────────────┼───────────────┐
        │             │               │
        ▼             ▼               ▼
   ┌─────────┐  ┌──────────┐   ┌───────────┐
   │ super-  │  │ super-   │   │ auth-     │
   │ claude  │  │ claude-  │   │ service   │
   │ (:8000) │  │ ops      │   │ (:8002)   │
   │         │  │ (:8001)  │   │           │
   └────┬────┘  └────┬─────┘   └───────────┘
        │            │
        └─────┬──────┘
              │
              ▼
        ┌─────────────────────────────┐
        │  /data (mounted volume)     │
        │  ├── mcps/                  │
        │  ├── domains/               │
        │  ├── config/                │
        │  └── outputs/               │
        └─────────────────────────────┘
```

## Container Responsibilities

| Container | Port | Purpose |
|-----------|------|---------|
| super-claude-router | 8080 | nginx reverse proxy, SSL termination, path routing |
| super-claude | 8000 | Main MCP server with all tools |
| super-claude-ops | 8001 | Administration, can rebuild super-claude |
| super-claude-auth | 8002 | OAuth token generation/validation |

**Network**: All containers on `super-claude_super-claude-net` bridge network.

## Storage Abstraction

```
MCP Tools (abstract)     →  storage_list_files("personal", "/path")
        ↓
Storage Manager          →  routes by account name
        ↓
Providers                →  gdrive, onedrive, dropbox
```

Accounts stored in `/data/config/storage_accounts.json`. Credentials referenced via 1Password.

## Supernote Sync Architecture

Supernote sync uses the storage abstraction layer rather than talking to Supernote directly (their cloud SDKs are broken). The plugin syncs via whatever cloud storage the Supernote device syncs to.

```
Supernote Device                     Super Claude Domain
      │                                   │
      │ (device auto-sync)                │ plugins/supernote/
      ▼                                   │   ├── config.json
┌─────────────────────────────────────────│   ├── notes/
│       Cloud Storage (e.g., GDrive)      │   ├── documents/
│  /Note/{subfolder}/     ←──────pull─────│   └── converted/
│  /Document/{subfolder}/ ←──────push─────│
└─────────────────────────────────────────┘
```

---

## Architecture Decision Records

### ADR-001: Single MCP vs Multiple
**Date**: 2024-12-27 | **Status**: Decided

**Context**: Should we have separate MCPs for auth, filesystem, docker, etc.?

**Decision**: Single MCP (`super-claude`) with all tools.

**Rationale**:
- Simpler connector management (one URL)
- Shared code/state between tools
- Can always split later if needed
- Auth MCP was separate initially, merged it in

---

### ADR-002: Filesystem Sandboxing
**Date**: 2024-12-27 | **Status**: Decided

**Context**: Should Claude have full NAS access or be sandboxed?

**Decision**: Sandbox to `/volume1/docker/super-claude` (mounted as `/data`).

**Rationale**:
- Safety: Can't accidentally delete system files
- Open source friendly: Clear boundary for personal data
- Still has full access within sandbox
- Can always expand later if needed

---

### ADR-003: Domain Structure
**Date**: 2024-12-27 | **Status**: Decided

**Context**: How should domain knowledge be organized?

**Decision**: 
```
domains/{name}/
├── {name}.md      # Always loaded, core context
├── state.json     # Session state, lightweight
└── context/       # Reference files, loaded on demand
```

**Rationale**:
- Main file is the "brain" - player profile, interaction patterns
- state.json is minimal, changes often
- context/ files are stable reference, pulled as needed
- Keeps token usage low (don't load everything every time)

---

### ADR-004: Mutual Administration
**Date**: 2024-12-27 | **Status**: Decided

**Context**: Super-claude can't rebuild itself (would kill the process).

**Decision**: Create separate `super-claude-ops` container that can rebuild super-claude, and vice versa.

**Rationale**:
- Mutual administration capability
- Natural guardrail against self-destruction
- Ops can handle scheduled tasks, backups
- Two containers watching each other

---

### ADR-005: Git Strategy
**Date**: 2024-12-27 | **Status**: Decided

**Context**: How to version control and potentially open source?

**Decision**: 
- Public repo: `super-claude` (framework, template domain, super-claude domain)
- Private data: Personal domains excluded via .gitignore

**Rationale**:
- Framework is useful to others
- Personal game data, work stuff stays private
- Clean separation via .gitignore patterns

---

### ADR-006: Plugin System
**Date**: 2026-01-16 | **Status**: Decided

**Context**: How to extend Super Claude with optional capabilities?

**Decision**: Plugin directory (`/data/mcps/super-claude/plugins/`) with auto-discovery.

**Rationale**:
- Keeps core MCP lean
- Plugins can have their own dependencies
- Easy to enable/disable capabilities
- Plugin tools appear alongside core tools

---

### ADR-007: Documentation Structure
**Date**: 2026-01-17 | **Status**: Decided

**Context**: How to maintain development records?

**Decision**: Four canonical files in `context/`:
- `features.md` - What Super Claude does
- `changelog.md` - Session summaries, what changed
- `todo.md` - Prioritized backlog
- `architecture.md` - System design, ADRs

**Rationale**:
- Single source of truth for each concern
- All tracked in git
- Updated at session wrap-up
- state.json stays minimal (runtime state only)

---

### ADR-008: Per-Domain Plugin Directories
**Date**: 2026-01-17 | **Status**: Decided

**Context**: Where should plugins store per-domain configuration and data?

**Decision**: Each domain can have a `plugins/` subdirectory with plugin-specific folders:
```
domains/{name}/
├── {name}.md
├── state.json
├── context/
└── plugins/
    └── {plugin-name}/
        ├── config.json    # Plugin configuration for this domain
        └── ...            # Plugin-specific files
```

**Example** (supernote):
```
domains/burrillville/plugins/supernote/
├── config.json    # account, subfolder, sync settings
├── notes/         # .note files pulled from device
├── documents/     # files to push to device
└── converted/     # local conversions (not synced)
```

**Rationale**:
- Clean separation between plugin code and plugin data
- Each domain can have different plugin configurations
- Plugin data lives with the domain it belongs to
- Easy to see what plugins a domain uses
- Plugins don't pollute the domain's main directory structure

---

## Infrastructure

- **Host**: Synology RS1221+ with UPS
- **Network**: Ubiquiti, DDNS via zanni.synology.me
- **Auth**: 1Password service account + OAuth/JWT
- **Docker network**: super-claude_super-claude-net
