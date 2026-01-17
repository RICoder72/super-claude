# Super Claude Todo

## In Progress

**Supernote Plugin**
- [x] Plugin architecture using storage abstraction (not direct Supernote API)
- [x] Per-domain config in `plugins/supernote/config.json`
- [x] Setup tool with account + subfolder configuration
- [x] Pull/push/list tools implemented
- [x] Local folder structure (notes/, documents/, converted/)
- [x] .note → PNG conversion via supernotelib
- [x] base_path config for non-root Supernote sync folders
- [x] Note processing workflow (mark_processed moves notes to processed/)
- [ ] Test push direction (documents to Supernote)

---

## Next Up

### User Profile
- [ ] **Global user profile**: A `profile.md` or similar in Super Claude root with info about Matthew
  - Background, preferences, working style, current context
  - Loaded automatically on session_start (or available via tool)
  - Supplements Claude.ai memory with Super Claude-specific context
  - Could include: communication preferences, project context, technical background, current priorities
  - Consider: should this be editable via tool? Or just a file Claude can read?

### Plugin System Improvements
- [ ] **Hot loading**: New plugins should be detected and loaded without restart
- [ ] **Hot reloading**: Changed plugin code should take effect without restart
  - Current issue: Python module caching requires server restart
  - MCP tool schema also cached in client conversation
  - Need to invalidate `sys.modules` cache on reload
  - Consider file watcher for auto-reload during development

### Publishing / Web Output
- [x] **Basic published file access**: Direct file URLs now work without auth (2026-01-17)
  - Directory listing (`/super-claude-output/`) still requires bearer token
  - Direct file access (`/super-claude-output/myfile.png`) is public
  - URLs are unguessable; acceptable for personal infra
- [ ] **Cookie-based auth for published files**: Proper auth with browser session
  - Add OAuth login flow that sets browser cookie
  - Update nginx to accept cookie OR bearer token
  - One-time browser login, then all published URLs work seamlessly
  - Consider: shared cookie with auth-service, or separate "viewer" auth?
- [ ] **In-chat file delivery**: Way to get published files into Claude chat directly (base64? copy to claude.ai uploads?)

### Supernote Polish
- [ ] **Sync status tracking**: Track which files have been synced, detect changes
- [ ] **Selective sync**: Allow syncing specific files, not just all
- [ ] **Incremental pull**: Only download new/changed files

### Domain System Improvements
- [x] **Domain-specific instructions**: INSTRUCTIONS.md loaded with context_load (2026-01-17)
- [x] **Global instructions**: INSTRUCTIONS.md at root loaded with session_start (2026-01-17)
- [x] **instructions_get/set tools**: View and update instructions via tools (2026-01-17)
- [ ] **Cross-domain search**: `context_search` tool to find relevant info across all domains
- [ ] **Domain creation prompt**: Offer to create a domain when none detected after several turns
- [ ] **Domain templates**: Streamline new domain creation with scaffolding command
- [ ] **Reference materials convention**: Document pattern for storing artifacts in context/ folder

### Documentation
- [ ] **Chat-to-domain capture**: Ability to summarize/save chat content to relevant domain before deletion
- [ ] **Domain meta-tagging**: Categorize domains for cross-referencing (e.g., gaming+msf are both games)

---

## Backlog

### Cloud Storage Providers
- [ ] OneDrive provider
- [ ] Dropbox provider

### Reliability & Safety
- [ ] **Guardrails**: Prevent shell_exec from stopping/removing critical containers
- [ ] **Self-recovery**: Watchdog or webhook to restart router without SSH
- [ ] **Safety mode**: On-demand mode that blocks write/delete operations
  - Add permission metadata to tools (read/write/dangerous)
  - Toggle via voice command with passphrase verification
  - When active, block write/delete/dangerous ops
  - Passphrase stored securely, verified in transcript

### Infrastructure
- [ ] **Cloudflare**: Complete setup for ricoder.me as backup access path
- [ ] **1Password naming cleanup**: Review and standardize item names in Key Vault
- [ ] **Git config persistence**: Ensure git user config survives container rebuild

### Future Integrations
- [ ] Scheduled tasks (via ops container)
- [ ] Web dashboard for status
- [ ] External API integrations (Jira, etc.)

---

## Major Initiatives

### Home Assistant Voice Pipeline
**Goal**: Talk to Claude from anywhere in the house via distributed microphones.

- [ ] Research HA Assist custom conversation agent API
- [ ] Create Super Claude endpoint for voice requests (simpler response format)
- [ ] Set up Wyoming protocol integration
- [ ] Configure wake word detection (openWakeWord)
- [ ] Set up local STT (Whisper via faster-whisper)
- [ ] Set up local TTS (Piper)
- [ ] Build/buy first satellite device for testing
- [ ] Test end-to-end flow
- [ ] Scale to multiple rooms

### Open Source Release (v1.0)
**Goal**: Make Super Claude available for others to deploy.

**Documentation**
- [ ] README.md - Project overview
- [ ] Quick start guide (15-minute deploy)
- [ ] Deployment options (local, Synology, cloud)
- [ ] Configuration reference
- [ ] Domain authoring guide

**Code Cleanup**
- [ ] Remove/redact personal data from sample domains
- [ ] Create example domains (projects, notes)
- [ ] Review hardcoded paths/URLs
- [ ] Add LICENSE file (PolyForm Noncommercial)

**Deployment**
- [ ] Local-only mode (no auth, no SSL) for development
- [ ] Environment-based config
- [ ] Verify clean install from README

### Plugin Ecosystem
**Goal**: Enable community plugins and a marketplace-style approach.

- [ ] **Separate plugins repo**: Move plugins out of core super-claude repo
  - Decouple plugin versioning from core versioning
  - Enable independent plugin development/contribution
  - Requires defining stable plugin API/contract first
- [ ] **Plugin API contract**: Define stable interface plugins can rely on
  - Storage access patterns
  - Config/state conventions
  - Tool registration interface
  - Avoid plugins reaching into server internals
- [ ] **Plugin packaging**: Make plugins pip-installable packages
- [ ] **Plugin registry/discovery**: Way to find and install community plugins
- [ ] **Plugin documentation template**: Standard format for plugin READMEs

---

## Completed

Moved to changelog.md after completion.
