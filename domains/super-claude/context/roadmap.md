# Super Claude Roadmap

## Current: v0.1.0 - Foundation
✅ Auth MCP (1Password integration)
✅ Filesystem tools (sandboxed to /data)
✅ Shell execution
✅ Docker management
✅ Domain structure created

## Next: v0.2.0 - Context System
- [ ] `context_load` tool - Load domain.md when switching domains
- [ ] `context_get` tool - Pull specific context files on demand
- [ ] `context_update` tool - Update state.json and domain files
- [ ] Domain switching UX ("let's work on MSF")

## Planned: v0.3.0 - Ops Container
- [ ] Create `super-claude-ops` container
- [ ] Ability to rebuild super-claude from ops
- [ ] Mutual restart capability
- [ ] Health checks and monitoring

## Planned: v0.4.0 - Git Integration
- [ ] Git init in super-claude root
- [ ] Auto-commit on significant changes
- [ ] Push to GitHub (public repo for framework)
- [ ] Separate private repo for domains

## Future Ideas
- [ ] Scheduled tasks (via ops container)
- [ ] Backup automation
- [ ] Multi-user support (probably never needed)
- [ ] Web dashboard for status (overkill?)
- [ ] Integration with external APIs (Jira, etc.)

## Domain-Specific Roadmap
- [ ] MSF domain migration
- [ ] GRC domain setup
- [ ] Projects domain (meta task tracking)
