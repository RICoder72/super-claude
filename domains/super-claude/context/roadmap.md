# Super Claude Roadmap

## Current: v0.5.0 - Natural Invocation + OAuth
✅ Auth MCP (1Password integration)
✅ Filesystem tools (sandboxed to /data)
✅ Shell execution
✅ Docker management
✅ Domain structure created
✅ Ops container with mutual rebuild
✅ Git integration working
✅ Path-based routing via nginx
✅ Context system (context_load, context_get, context_update, context_list)
✅ OAuth authentication (authorization_code + PKCE)
✅ Token expiry tracking with warnings
✅ Natural domain invocation via keywords (session_start)
✅ Externalized domain config (descriptions + triggers in JSON)

## Next: v0.6.0 - Smarter Context
- [ ] Domain creation prompt: Offer to create a domain when none detected
- [ ] Cross-domain search: `context_search` tool to find relevant info across all domains
- [ ] Domain templates: Streamline new domain creation with scaffolding

## Planned: v0.7.0 - Resilience & Guardrails
- [ ] Guardrails: Prevent shell_exec from stopping critical containers
- [ ] Self-recovery: Watchdog to restart router without SSH
- [ ] Cloudflare: Complete setup for ricoder.me as backup path

---

## Major Initiative: Home Assistant Voice Pipeline Integration

**Goal**: Talk to Claude from anywhere in the house via distributed microphones.

**Why this is exciting**: Transforms Super Claude from a text interface into an ambient presence. Ask about projects while cooking, get briefings while getting dressed, capture ideas hands-free.

### Architecture
```
[ESP32-S3 Satellites] → [Wake word: "Hey Claude"]
         ↓
[Wyoming Protocol → Home Assistant]
         ↓
[Speech-to-text: Whisper (local) or cloud]
         ↓
[HA Assist Pipeline → Custom Conversation Agent]
         ↓
[Super Claude MCP endpoint (new: /assist or /voice)]
         ↓
[Text-to-speech: Piper (local) or cloud]
         ↓
[Response to satellites/speakers]
```

### Hardware Needed
- ESP32-S3 satellite devices (~$13-30 each) OR repurposed smart speakers
- Target: 4-6 units for whole-house coverage
- Optional: dedicated speakers at each point, or route to existing Sonos/Alexa

### Implementation Checklist
- [ ] Research HA Assist custom conversation agent API
- [ ] Create Super Claude endpoint for voice requests (simpler response format)
- [ ] Set up Wyoming protocol integration
- [ ] Configure wake word detection (openWakeWord)
- [ ] Set up local STT (Whisper via faster-whisper)
- [ ] Set up local TTS (Piper)
- [ ] Build/buy first satellite device for testing
- [ ] Test end-to-end flow
- [ ] Scale to multiple rooms

### References
- Home Assistant Assist: https://www.home-assistant.io/voice_control/
- Wyoming Protocol: https://github.com/rhasspy/wyoming
- ESP32 satellites: ESPHome voice assistant configs
- openWakeWord: https://github.com/dscripka/openWakeWord

---

## Major Initiative: Open Source Release (v1.0)

Goal: Make Super Claude available for others to deploy locally or in the cloud.

### Documentation
- [ ] README.md - Project overview, what it does, why it exists
- [ ] Quick start guide - Get running in 15 minutes
- [ ] Deployment options doc:
  - [ ] Local (Docker on any machine)
  - [ ] Synology NAS (current approach)
  - [ ] Cloud (VPS, AWS, etc.)
- [ ] Configuration reference - All env vars, config files explained
- [ ] Domain authoring guide - How to create effective domains

### Code Cleanup
- [ ] Remove/redact personal data from sample domains
- [ ] Create example domains (starter set):
  - [ ] `_template` (already exists, review)
  - [ ] `projects` (generic task tracking)
  - [ ] `notes` (simple knowledge base example)
- [ ] Review hardcoded paths/URLs
- [ ] Add LICENSE file (PolyForm Noncommercial or similar - permissive but no commercial use)
- [ ] Git config persistence (survives rebuild)

### Deployment Flexibility
- [ ] Local-only mode (no auth required, no SSL) for development
- [ ] Environment-based config (local vs cloud)
- [ ] docker-compose.yml for easy single-command deploy
- [ ] Optional: Helm chart for Kubernetes

### Testing
- [ ] Basic test suite for core tools
- [ ] Verify clean install from README instructions

---

## Future Ideas
- [ ] Synology DSM as IDP: Research using DSM for SSO to protect published outputs (/super-claude-output/)
- [ ] Scheduled tasks (via ops container)
- [ ] Web dashboard for status
- [ ] Integration with external APIs (Jira, etc.)
- [ ] MSF domain migration
- [ ] GRC domain setup
- [ ] Projects domain enhancement

### Claude-Assisted Setup
- [ ] Create SETUP.md with structured instructions for Claude Code
- [ ] User experience: clone repo → run `claude` → paste "Read SETUP.md and deploy Super Claude"
- [ ] Claude handles: environment detection, config questions, Docker setup, verification
- [ ] Self-documenting: the setup instructions ARE the automation
