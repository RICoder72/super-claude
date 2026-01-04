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

## Next: v0.6.0 - Resilience & Guardrails
- [ ] Guardrails: Prevent shell_exec from stopping critical containers
- [ ] Self-recovery: Watchdog to restart router without SSH
- [ ] Cloudflare: Complete setup for ricoder.me as backup path

## Planned: v0.7.0 - More Domains
- [ ] MSF domain migration
- [ ] GRC domain setup
- [ ] Projects domain enhancement

## Future Ideas
- [ ] Scheduled tasks (via ops container)
- [ ] Web dashboard for status
- [ ] Integration with external APIs (Jira, etc.)
- [ ] Hands-free voice interface (wake word triggering)
