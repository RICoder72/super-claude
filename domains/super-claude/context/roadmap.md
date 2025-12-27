# Super Claude Roadmap

## Current: v0.3.1 - Post-Foundation
✅ Auth MCP (1Password integration)
✅ Filesystem tools (sandboxed to /data)
✅ Shell execution
✅ Docker management
✅ Domain structure created
✅ Ops container with mutual rebuild
✅ Git integration working
✅ Path-based routing via nginx

## Next: v0.4.0 - Context System
- [ ] `context_load` tool - Load domain.md when switching domains
- [ ] `context_get` tool - Pull specific context files on demand
- [ ] `context_update` tool - Update state.json and domain files
- [ ] Domain switching UX ("let's work on MSF")

## Planned: v0.5.0 - Git Workflow
- [ ] Auto-commit on significant changes
- [ ] Push to GitHub (public repo for framework)
- [ ] Separate private repo for domains
- [ ] Backup automation

## Future Ideas
- [ ] Scheduled tasks (via ops container)
- [ ] Multi-user support (probably never needed)
- [ ] Web dashboard for status (overkill?)
- [ ] Integration with external APIs (Jira, etc.)

## Domain-Specific Roadmap
- [ ] MSF domain migration
- [ ] GRC domain setup
- [ ] Projects domain (meta task tracking)
