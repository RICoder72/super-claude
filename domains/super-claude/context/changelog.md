# Changelog

## 2026-01-11

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

## 2024-12-26

### Session: Tracer Bullet
- Built minimal MCP server (ping + echo tools)
- Deployed to Synology via Docker
- Configured reverse proxy + SSL
- Set up port forwarding through Ubiquiti
- Connected as custom connector in Claude
- Successfully called ping tool from Claude mobile
- **Result**: Full path proven working


## 2026-01-11: Domain Awareness Enhancement

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
