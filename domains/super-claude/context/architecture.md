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

## Core Infrastructure vs Services

Super Claude has two distinct layers:

### Infrastructure Layer (Core)

Internal plumbing that makes Super Claude work. Not exposed as tools.

```
/app/core/
├── secrets/           # Infrastructure secrets (OAuth tokens, API keys)
│   ├── interface.py   # SecretsBackend ABC
│   ├── manager.py     # Singleton manager
│   └── backends/      # 1Password, Bitwarden, local encrypted
└── ...
```

### Services Layer (User-Facing)

Account-based capabilities exposed as MCP tools. Users configure named accounts.

```
/app/services/
├── storage/     # Cloud file storage
├── mail/        # Email operations  
├── calendar/    # Calendar operations
└── secrets/     # User credential management (NOT infrastructure)
```

## Core Services

Super Claude provides **Core Services** that abstract common capabilities. Users configure **Accounts** that connect services to platforms via **Adapters**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Core Services                                    │
├───────────────┬───────────────┬───────────────┬─────────────────────────────┤
│   Storage     │     Mail      │   Calendar    │         Secrets             │
│   Service     │    Service    │    Service    │         Service             │
├───────────────┼───────────────┼───────────────┼─────────────────────────────┤
│ StorageAdapter│  MailAdapter  │CalendarAdapter│      SecretsAdapter         │
│    (ABC)      │     (ABC)     │     (ABC)     │          (ABC)              │
├───────────────┼───────────────┼───────────────┼─────────────────────────────┤
│  Adapters:    │  Adapters:    │   Adapters:   │       Adapters:             │
│  • GDrive     │  • Gmail      │   • GCal      │       • 1Password           │
│  • OneDrive   │  • Outlook    │   • OutlookCal│       • Bitwarden           │
│  • Dropbox    │  • IMAP       │   • CalDAV    │       • LastPass            │
└───────────────┴───────────────┴───────────────┴─────────────────────────────┘
```

**Terminology:**
- **Service** = A capability Super Claude provides (Storage, Mail, Calendar, Secrets)
- **Adapter** = Platform-specific implementation of a service interface (GmailAdapter)
- **Account** = User's configured instance of an adapter ("work-gmail", "personal-drive")

**File structure:**
```
/app/services/
├── __init__.py
├── storage/
│   ├── interface.py     # StorageAdapter ABC, StorageAccount, FileInfo
│   ├── manager.py       # StorageManager
│   └── adapters/
│       └── gdrive.py    # GDriveAdapter
├── mail/
│   ├── interface.py     # MailAdapter ABC, MailAccount, Message, etc.
│   ├── manager.py       # MailManager
│   └── adapters/
│       └── gmail.py     # GmailAdapter
├── calendar/
│   ├── interface.py     # CalendarAdapter ABC, CalendarAccount, Event
│   ├── manager.py       # CalendarManager
│   └── adapters/
│       └── gcal.py      # GCalAdapter
└── secrets/
    ├── interface.py     # SecretsAdapter ABC, SecretItem
    ├── manager.py       # SecretsManager
    └── adapters/
        └── onepassword.py  # Uses core/secrets for its own auth
```

**Pattern for each service:**
1. **Interface** (`interface.py`) - ABC defining the contract, dataclasses for data types
2. **Manager** (`manager.py`) - Account CRUD, adapter registry, lazy instantiation, routing
3. **Adapters** (`adapters/*.py`) - Concrete implementations for each platform

Accounts stored in `/data/config/{service}_accounts.json`. Credentials referenced via infrastructure secrets.

## Domain Service Defaults

Domains can specify which accounts to use by default:

```json
// domains/burrillville/state.json
{
  "service_defaults": {
    "mail": "work-gmail",
    "storage": "personal-gdrive",
    "calendar": "work-gcal",
    "secrets": "work-passwords"
  }
}
```

Tool resolution order:
1. Explicit `account` parameter → use it
2. Domain loaded with default → use domain default
3. Global default configured → use global default
4. No default → require explicit account

## Supernote Sync Architecture

Supernote sync uses the storage service rather than talking to Supernote directly (their cloud SDKs are broken). The plugin syncs via whatever cloud storage the Supernote device syncs to.

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

### ADR-009: Core Services + Adapters Architecture
**Date**: 2026-01-17 | **Status**: Decided

**Context**: How to provide extensible platform integrations (storage, mail, calendar) that can support multiple providers?

**Decision**: Core Services architecture with:
- **Services** = Capabilities Super Claude provides (Storage, Mail, Calendar)
- **Adapters** = Platform-specific implementations (GDriveAdapter, GmailAdapter, GCalAdapter)
- **Accounts** = User-configured instances referencing an adapter and credentials

Each service follows the same pattern:
```
/app/services/{service}/
├── interface.py     # {Service}Adapter ABC + dataclasses
├── manager.py       # {Service}Manager (account CRUD, routing, lazy instantiation)
└── adapters/
    └── {platform}.py  # Concrete adapter implementations
```

**Rationale**:
- Consistent pattern across all external service integrations
- Plugins consume services without knowing platform specifics
- New platforms added by implementing adapter interface
- Account abstraction lets users name connections ("work-gmail", "personal-drive")
- Credentials stay in 1Password, referenced by account config
- Mirrors successful storage abstraction pattern, now generalized

**Migration**: Existing storage code moves from `/app/core/` and `/app/providers/` to `/app/services/storage/`. `StorageProvider` renamed to `StorageAdapter` for consistency.

---

### ADR-010: Two-Layer Secrets Architecture
**Date**: 2026-01-18 | **Status**: Decided

**Context**: Super Claude needs secrets management for two distinct purposes:
1. **Infrastructure**: OAuth tokens, API keys, service account credentials that adapters need to function
2. **User Data**: Passwords and credentials the user wants to store/retrieve as part of their work (e.g., "store the firewall login for my IT documentation")

These are fundamentally different concerns that happen to use similar technology.

**Decision**: Implement two layers:

**Layer 1: Infrastructure Secrets (Core)**
```
/app/core/secrets/
├── interface.py      # SecretsBackend ABC
├── manager.py        # SecretsManager (singleton, not account-based)
└── backends/
    ├── onepassword.py
    ├── bitwarden.py
    └── local_encrypted.py
```

- Configured at system level (`/data/config/secrets_backends.json`)
- Supports multiple backends (e.g., personal-1pw, work-1pw pointing to different vaults)
- Used internally by service adapters to retrieve their credentials
- NOT exposed as MCP tools (internal plumbing only)
- Service accounts reference which backend holds their credentials

**Layer 2: Secrets Service (User-Facing)**
```
/app/services/secrets/
├── interface.py      # SecretsAdapter ABC
├── manager.py        # SecretsManager (account-based, like mail/storage)
└── adapters/
    └── onepassword.py
```

- Account-based like other services: `work-passwords`, `personal-passwords`
- Domain-configurable defaults (domain can set `secrets: work-passwords`)
- Exposed as MCP tools: `secrets_list`, `secrets_get`, `secrets_set`, `secrets_search`
- For storing/retrieving USER data that happens to be sensitive
- Uses Layer 1 infrastructure secrets for its own authentication

**Configuration example:**

Infrastructure backends (`/data/config/secrets_backends.json`):
```json
{
  "backends": {
    "personal": {
      "adapter": "onepassword",
      "vault": "Key Vault",
      "service_account_env": "OP_SERVICE_ACCOUNT_TOKEN"
    },
    "work": {
      "adapter": "onepassword",
      "vault": "Burrillville",
      "service_account_env": "OP_WORK_SERVICE_ACCOUNT_TOKEN"
    }
  },
  "default_backend": "personal"
}
```

Service account referencing infrastructure (`/data/config/mail_accounts.json`):
```json
{
  "work-gmail": {
    "adapter": "gmail",
    "secrets_backend": "work",
    "credentials_item": "Burrillville Google Workspace"
  }
}
```

**Rationale**:
- Clear separation between plumbing and features
- Infrastructure layer is invisible to users, just works
- Service layer follows existing account-based patterns
- Open source friendly: users can choose their secret provider at both layers
- Supports complex scenarios (work vault + personal vault + legacy provider)
- The secrets service adapter uses infrastructure secrets for its own auth (turtles, but only two levels)

**Diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  (defaults: mail=work-gmail, secrets=work-passwords, ...)   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Account-Based Services                         │
│   Mail         Storage        Calendar       Secrets        │
│   ├─work       ├─personal     ├─work         ├─work-pw      │
│   └─personal   └─work         └─personal     └─personal-pw  │
└────────────────────────┬────────────────────────────────────┘
                         │ adapters call for their creds
┌────────────────────────▼────────────────────────────────────┐
│           Infrastructure Secrets (Core)                     │
│   secrets_core.get(backend, item, field)                    │
│   ├─ personal → 1Password "Key Vault"                       │
│   └─ work     → 1Password "Burrillville"                    │
└─────────────────────────────────────────────────────────────┘
```

---

### ADR-011: Domain Service Defaults
**Date**: 2026-01-18 | **Status**: Decided

**Context**: When a domain is loaded, tools shouldn't require explicit account selection for every call. The burrillville domain should "know" to use work-gmail by default.

**Decision**: Domains can specify default accounts for each service in their configuration:

```json
// domains/burrillville/state.json or config section
{
  "service_defaults": {
    "mail": "work-gmail",
    "storage": "personal-gdrive",
    "calendar": "work-gcal",
    "secrets": "work-passwords"
  }
}
```

**Tool behavior:**
1. If `account` parameter provided → use it
2. Else if domain loaded with default for this service → use domain default
3. Else if global default configured → use global default
4. Else → require explicit account (error if not provided)

**Rationale**:
- Reduces friction when working within a domain context
- Explicit account always wins (no magic override)
- Domain-less usage still works with explicit accounts
- Matches mental model: "I'm doing work stuff, use work accounts"

---

## Infrastructure

- **Host**: Synology RS1221+ with UPS
- **Network**: Ubiquiti, DDNS via zanni.synology.me
- **Auth**: 1Password service account + OAuth/JWT
- **Docker network**: super-claude_super-claude-net
