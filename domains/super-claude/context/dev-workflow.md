# Super Claude Development Workflow

## Quick Reference

| Task | Command |
|------|---------|
| Quick sync during dev | `./scripts/dev-sync.sh super-claude` |
| Full rebuild | `./scripts/rebuild-super-claude.sh` |
| Rebuild ops | `./scripts/rebuild-ops.sh` |
| Rebuild both | `./scripts/rebuild-all.sh` |

Or use MCP tools: `rebuild_ops()` from super-claude, `rebuild_super_claude()` from ops.

## Key Concepts

**Code is COPIED into containers at build time.** The running container's `/app/` is separate from `/data/mcps/super-claude/`. Changes to source files don't appear until you sync or rebuild.

**Development workflow:**
1. Edit files in `/data/mcps/super-claude/`
2. Quick test: `./scripts/dev-sync.sh super-claude` (copies files, restarts)
3. New Claude chat to reconnect
4. When done: `git commit` then `./scripts/rebuild-super-claude.sh`

**Mutual administration:** Each MCP can rebuild the other - you're never locked out.

## File Locations

```
/data/
├── mcps/super-claude/     # Main MCP source (git tracked)
├── mcps/ops/              # Ops MCP source (git tracked)
├── shared/                # Shared modules (copied to both)
├── scripts/               # Build scripts (see README.md there)
├── config/                # .env, tokens (secrets not in git)
└── domains/               # Domain data and context
```

## Dynamic Plugin System

Plugins load at runtime via `DynamicPluginLoader`. No rebuild needed for plugin changes:
- `plugin_reload("supernote")` - hot reload after editing
- `plugin_reload_changed()` - auto-detect and reload modified plugins
- `plugin_load/unload` - add/remove plugins mid-session

For full documentation: `build_help()` tool or `cat /data/scripts/README.md`
