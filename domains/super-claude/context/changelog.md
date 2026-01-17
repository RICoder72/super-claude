# Changelog

## 2026-01-17

### Session 6: Code Audit & Refactoring

**What**: Performed comprehensive code audit and addressed key findings.

**Audit Report**: Created `context/audit-2026-01-17.md` covering:
- Inefficiencies (monolithic server.py, sync path resolution)
- Code duplication (shell helpers, path constants, JSON handling)
- Security issues (Docker socket access, in-memory auth codes, rate limiting)
- Architectural concerns (plugin registration, storage manager coupling)

**Refactoring completed**:

1. **Created shared modules**:
   - `shared/config.py` — centralized constants (SUPER_CLAUDE_ROOT, DOMAINS_DIR, etc.)
   - `shared/shell.py` — unified shell execution with safety guards

2. **Added command blocklist to shell execution**:
   - Blocks dangerous patterns: `rm -rf /`, `mkfs`, `dd of=/`, fork bombs
   - Protects critical containers from accidental stop/remove
   - Logged warnings when commands are blocked

3. **Updated server.py**:
   - Removed duplicate `SUPER_CLAUDE_ROOT` definition
   - Now imports from shared modules (with fallback)
   - Shell execution routed through shared module with safety checks

4. **Updated ops/server.py**:
   - Now uses shared modules for constants and shell execution
   - Passes `check_blocked=False` for ops commands (trusted context)

5. **Updated Dockerfiles**:
   - Both now copy `shared/` directory
   - Both configure git safe.directory for /data
   - Enables git commands from within containers

**Git improvements**:
- Can now run git commands from super-claude container
- Added safe.directory config to both Dockerfiles
- No more "dubious ownership" errors

**Files changed**:
- `shared/config.py` (new)
- `shared/shell.py` (new)
- `mcps/super-claude/server.py`
- `mcps/super-claude/Dockerfile`
- `mcps/ops/server.py`
- `mcps/ops/Dockerfile`

**Next steps from audit**:
- Split server.py into modules (tools/, helpers/)
- Fix supernote plugin → storage_manager coupling
- Add rate limiting to auth service
- Implement cookie-based auth for published files

---

### Session 5: Published File Auth Fix

**What**: Fixed 403 errors when accessing published files via browser.

**Problem**: Published file URLs (e.g., `zanni.synology.me/super-claude-output/file.png`) returned 403 Forbidden because nginx required bearer token auth for the entire `/super-claude-output/` location. Browsers don't send bearer tokens on link clicks.

**Solution**: Split nginx config into two location blocks:
- `location = /super-claude-output/` (exact match) — directory listing requires auth
- `location /super-claude-output/` (prefix match) — direct file access is public

**Rationale**: URLs are unguessable (you only get them from Claude), content is user-generated, and this is personal infrastructure. Acceptable security tradeoff for immediate usability. Future: cookie-based auth for proper browser sessions.

**Changes**:
- Updated `router/nginx-auth.conf`:
  - Split `/super-claude-output/` into two location blocks
  - Added MIME types for images (png, jpg, gif) and PDF
  - Directory listing still protected, direct file access public
- Updated `domains/super-claude/context/todo.md`:
  - Added "User Profile" item — global `profile.md` for user context
  - Marked basic published file access as complete
  - Added future item: cookie-based auth with browser login flow

**Result**: `https://zanni.synology.me/super-claude-output/somefile.png` now loads in browser without auth. Enables sharing Supernote images without burning Claude's vision token quota.

---

### Session 4: Supernote Image Reading Tools

**What**: Added tools for Claude to read Supernote pages via vision, fixing conversation cutoffs caused by base64 text transfer.

**Problem discovered**: Previous sessions were getting cut off mid-processing when reading notes. Root cause: transferring images via base64 text through shell commands was hitting response limits (hundreds of KB per image × multiple pages = megabytes of text in tool responses).

**Solution**: Use MCP's native image content type instead of base64 text.

**Changes** (v0.5.0):
- Added `supernote_read_note(domain, note_stem)` - returns all pages as MCP ImageContent
- Added `supernote_read_page(domain, note_stem, page)` - returns single page as ImageContent  
- Added `supernote_list_notes(domain)` - lists available notes with page counts
- Integrated `supernote-tool convert` into `supernote_pull` (was manual before)
- Added `processed/` directory to plugin structure (for future use)

**Technical details**:
- FastMCP provides `Image` helper class at `fastmcp.utilities.types.Image`
- Returning `Image(path="/path/to/file.png")` gets converted to `ImageContent` automatically
- Images go through MCP's native image handling, not text context
- This is much more efficient than base64 text transfer

**Workflow now**:
```
1. supernote_pull(domain)     → Downloads and converts to PNG
2. supernote_list_notes(domain) → Shows available notes
3. supernote_read_note(domain, stem) → Claude sees images via vision
4. Claude extracts and processes content
```

**Note**: New tools require a new conversation to appear in tool list (client-side schema caching). Tested via Python direct calls - all working.

---

### Session 3: Supernote Conversion & Path Fixes

**What**: Completed Supernote plugin with .note → PNG conversion and fixed path handling for non-root sync folders.

**Bug fixed**: Plugin assumed Supernote synced to cloud storage root, but Matthew's syncs to `/Supernote/Note/...` and `/Supernote/Document/...`. Added `base_path` config option.

**Changes**:
- **v0.3.0**: Added `base_path` config for non-root Supernote sync folders
  - Setup now accepts optional `base_path` parameter (e.g., "/Supernote")
  - All remote path calculations now include base_path prefix
  - Status output shows full remote paths for clarity
- **v0.4.0**: Integrated supernote-tool for .note → PNG/PDF conversion
  - `pip install supernotelib` provides `supernote-tool` CLI
  - `_convert_note()` method wraps CLI for programmatic conversion
  - `supernote_pull()` now auto-converts downloaded notes
  - Supports png, pdf, svg, txt output formats
  - Multi-page notes create numbered files (e.g., `note_0.png`, `note_1.png`)

**Testing**:
- Successfully pulled 4 notes from Google Drive `/Supernote/Note/Burrillville Technology/`
- Converted to 11 PNG pages total
- Verified image quality - handwriting renders cleanly and is readable by Claude

**Plugin hot reload issue discovered**:
- `plugin_reload()` updates Python code but module caching prevents full reload
- MCP tool schema also cached in client conversation
- Workaround: Server restart required for plugin code changes
- Added to TODO for future fix

**Infrastructure note**: 
- Published files at zanni.synology.me/super-claude-output require auth (403)
- Workaround: base64 encode on Super Claude, decode in Claude.ai container, present_files
- Added to TODO: proper publishing auth or in-chat file delivery

**Result**: Full Supernote → Claude pipeline working:
```
Supernote device → Google Drive sync → supernote_pull → .note files
→ supernote-tool convert → PNG images → Claude can read handwriting
```

---

### Session 2: Supernote Plugin Implementation

**What**: Built Supernote sync plugin that uses the storage abstraction layer to sync files between domains and Supernote devices.

**Key insight**: Supernote's cloud SDKs are broken due to security changes. Instead of talking to Supernote directly, we sync via whatever cloud storage the Supernote device syncs to (e.g., Google Drive). The plugin is thin — it just orchestrates sync using Super Claude's existing storage tools.

**Architecture**:
```
Supernote Device → (auto-sync) → Cloud Storage ← (storage_* tools) ← Super Claude
```

**Changes**:
- Rewrote `plugins/supernote.py` (v0.2.0) to use storage abstraction instead of sncloud SDK
- Added 5 MCP tools:
  - `supernote_setup(domain, account, subfolder)` - configure sync for a domain
  - `supernote_status(domain)` - show config and file counts
  - `supernote_list_remote(domain, path_type)` - list files on cloud
  - `supernote_pull(domain)` - download .note files
  - `supernote_push(domain)` - upload documents
- Removed `providers/supernote_provider.py` (no longer needed)
- Updated `providers/__init__.py` to remove supernote provider
- Updated `server.py`:
  - Removed supernote provider registration
  - Added supernote tool wrappers to expose plugin tools via MCP
- Established per-domain plugin directory convention:
  ```
  domains/{name}/plugins/supernote/
  ├── config.json    # account, subfolder, sync settings
  ├── notes/         # .note files pulled from device
  ├── documents/     # files to push to device
  └── converted/     # PDF/PNG conversions (local only)
  ```

**Setup flow**: When configuring supernote for a domain, Claude asks for:
1. Storage account name (or offers to create one)
2. Subfolder name used on device

**Still TODO**:
- .note → PDF/PNG conversion (needs parser library)
- Test with actual Supernote folder structure

---

### Session 1: Documentation Restructure

**What**: Consolidated scattered development records into four canonical files with clear purposes.

**Problem**: Documentation was duplicated and scattered:
- `recentChanges` in state.json duplicated changelog.md
- Backlog items split between state.json and roadmap.md
- `planned_features` in state.json overlapped with roadmap.md
- roadmap.md mixed todo items with architecture diagrams

**Solution**: Four canonical files in `context/`:

| File | Purpose |
|------|---------|
| `features.md` | What Super Claude does — tools, capabilities, integrations |
| `changelog.md` | Session summaries — what changed and why |
| `todo.md` | Prioritized backlog — what to work on next |
| `architecture.md` | System design — ADRs, diagrams, infrastructure |

**Changes**:
- Created `features.md` — extracted from super-claude.md and scattered docs
- Created `todo.md` — consolidated from state.json backlog + planned_features + roadmap.md
- Created `architecture.md` — expanded decisions.md with diagrams from roadmap.md, added ADR-006 (plugins) and ADR-007 (documentation structure)
- Deleted `roadmap.md` (content migrated to todo.md and architecture.md)
- Deleted `decisions.md` (content migrated to architecture.md)
- Cleaned up `state.json` — removed redundant fields (backlog, planned_features, recentChanges, notes), kept only runtime state
- Updated `super-claude.md` — new session wrap-up protocol, updated pointers table

**Session wrap-up protocol** now requires updating the four canonical files at end of session, then committing to git.

**Result**: Single source of truth for each concern. All development docs tracked in git.

---

## 2026-01-16

### Session: Abstract Storage Layer

**What**: Built provider-agnostic cloud storage system so plugins can access any storage account without knowing the underlying service.

**Architecture**:
```
MCP Tools (abstract)     →  storage_list_files("personal", "/path")
        ↓
Storage Manager          →  routes by account name
        ↓
Providers                →  gdrive, (future: dropbox, onedrive)
```

**Changes**:
- Created storage abstraction layer:
  - `core/storage_interface.py` - defines StorageProvider contract
  - `core/storage_manager.py` - routes requests to correct provider
  - `providers/gdrive.py` - Google Drive implementation
- Added MCP tools:
  - `storage_list_accounts` - show configured accounts
  - `storage_list_files(account, path)` - list files
  - `storage_download(account, remote, local)` - download file
  - `storage_upload(account, local, remote)` - upload file
  - `storage_add_account` / `storage_remove_account` - manage accounts
- Completed Google Drive OAuth flow, token stored at `/data/config/gdrive_token.json`
- Added google-api-python-client to pyproject.toml dependencies
- Removed redundant `plugins/gdrive.py` (was bypassing abstraction)
- Created `context/storage-architecture.md` documentation

**Configuration**:
- Accounts stored in `/data/config/storage_accounts.json`
- Credentials referenced via 1Password (`credentials_ref`)
- First account configured: `personal` (gdrive)

**Result**: `storage_list_files("personal", "/")` returns Google Drive root listing. Plugins can now use storage without knowing provider details.

---

## 2026-01-11

### Session: Domain Awareness Enhancement

**What**: Made domain system smarter about loading and discovering domains

**Changes**:
- Created `config/domain_triggers.json` - centralized domain metadata (descriptions + triggers)
- `session_start` now shows descriptions for all domains, making their purpose clear
- `context_load` warns when a domain has no triggers configured
- All 10 domains now have descriptions and trigger keywords

**User Preferences addition**:
```
# Domain Awareness

When working with Super Claude domains:
- If a domain lacks trigger keywords when loaded, point it out and offer to add some
- If we've been discussing a topic for several turns that doesn't match any existing domain, ask if it's something worth creating a domain for
- Don't be pushy about domain creation - one gentle offer is enough
```

**Result**: User said "I was thinking of revising my 90 day plan for my new role as director of technology" and Claude automatically loaded burrillville domain + the 90-day plan context file. Friction-free.

### Session: Bug Fixes, Documentation & Claude Code
- Fixed FunctionTool bug: decorated tools couldn't call other decorated tools
  - FastMCP wraps `@mcp.tool()` functions as FunctionTool objects
  - `session_start` calling `context_load` and `docker_*` calling `shell_exec` were failing
  - Solution: Extract `_shell_exec_impl()` and `_context_load_impl()` helper functions
  - Tools now call helpers instead of other decorated tools
- Updated documentation to include `auth_set` capability
  - Domains can now both read AND create 1Password secrets
  - Updated: super-claude.md, file-structure.md, operations.md
  - Added Quick Reference examples for auth_set
- Created Claude Code setup guide (`context/claude-code-setup.md`)
  - Generated JWT token for Claude Code access
  - Token expires 2026-07-10 (180 days)
  - Documented `claude mcp add` command with bearer token

---

## 2026-01-04

### Session: OAuth Authentication
- Added OAuth 2.0 authentication with authorization_code + PKCE flow
- Created `auth-service/` with JWT token generation and validation
- Nginx router now requires authentication for `/mcp` and `/ops` endpoints
- Claude.ai connectors use OAuth client credentials flow
- JWT secret stored in 1Password (`Super Claude JWT Secret`)
- OAuth credentials stored in 1Password (`Super Claude OAuth Credentials`)
- Added token expiry tracking:
  - `token_status()` tool shows days remaining
  - `token_record()` tool records new token info
  - `ping()` warns when token expires within 14 days
- Tokens valid for 180 days (expires 2026-07-03)
- Both Super Claude and Super Claude Ops secured with same OAuth credentials

---

## 2024-12-27

### Session: Admin Tools & Domain Structure
- Created unified `super-claude` MCP with all tools
- Merged auth MCP functionality
- Added filesystem tools (fs_list, fs_read, fs_write, fs_delete, fs_mkdir, fs_rmdir, fs_move, fs_copy, fs_append)
- Added shell_exec tool
- Added docker tools (docker_ps, docker_logs, docker_restart, docker_stop, docker_start)
- Pinned Docker API version to 1.41 for Synology compatibility
- Created domain structure: `domains/super-claude/` and `domains/projects/`
- Documented architecture decisions

### Session: Auth MCP Complete (earlier)
- Built auth MCP with 1Password integration
- Created shared op_client.py module
- Established folder structure at `/volume1/docker/super-claude/`

### Session: Ops MCP & Path-Based Routing
- Created super-claude-ops MCP for mutual administration
- Added nginx router for path-based routing (/mcp, /ops)
- Created docker-compose.yml for unified deployment
- Both MCPs now accessible on port 443
- Ops can rebuild super-claude, super-claude can rebuild ops
- Added backup/restore and git tools to ops
- Pushed all changes to GitHub

---

## 2024-12-26

### Session: Tracer Bullet
- Built minimal MCP server (ping + echo tools)
- Deployed to Synology via Docker
- Configured reverse proxy + SSL
- Set up port forwarding through Ubiquiti
- Connected as custom connector in Claude
- Successfully called ping tool from Claude mobile
- **Result**: Full path proven working
