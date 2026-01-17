# Super Claude Todo

## In Progress

**Supernote Plugin**
- [x] Plugin architecture using storage abstraction (not direct Supernote API)
- [x] Per-domain config in `plugins/supernote/config.json`
- [x] Setup tool with account + subfolder configuration
- [x] Pull/push/list tools implemented
- [x] Local folder structure (notes/, documents/, converted/)
- [ ] .note → PDF/PNG conversion (needs parser library research)
- [ ] Test with actual Supernote folder structure on Google Drive

---

## Next Up

### Supernote Polish
- [ ] **Note conversion**: Research supernote-tool or similar for .note → PDF/PNG
- [ ] **Sync status tracking**: Track which files have been synced, detect changes
- [ ] **Selective sync**: Allow syncing specific files, not just all

### Domain System Improvements
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

---

## Completed

Moved to changelog.md after completion.
