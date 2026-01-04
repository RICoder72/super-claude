# Changelog

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

## 2024-12-26

### Session: Tracer Bullet
- Built minimal MCP server (ping + echo tools)
- Deployed to Synology via Docker
- Configured reverse proxy + SSL
- Set up port forwarding through Ubiquiti
- Connected as custom connector in Claude
- Successfully called ping tool from Claude mobile
- **Result**: Full path proven working


### Session: Ops MCP & Path-Based Routing
- Created super-claude-ops MCP for mutual administration
- Added nginx router for path-based routing (/mcp, /ops)
- Created docker-compose.yml for unified deployment
- Both MCPs now accessible on port 443
- Ops can rebuild super-claude, super-claude can rebuild ops
- Added backup/restore and git tools to ops
- Pushed all changes to GitHub


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
