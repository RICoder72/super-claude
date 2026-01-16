# Claude Code Setup

Connect Claude Code to Super Claude MCP for infrastructure access from the terminal.

## Quick Setup

Run this command in your terminal:

```bash
claude mcp add --transport http super-claude https://zanni.synology.me/mcp \
  --header "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdXBlci1jbGF1ZGUtY2xpZW50Iiwic2NvcGUiOiJyZWFkIHdyaXRlIGFkbWluIiwiaXNzIjoic3VwZXItY2xhdWRlIiwiYXVkIjoic3VwZXItY2xhdWRlLW1jcCIsImlhdCI6MTc2ODE2NzA1NiwianRpIjoiMjdjODA3NzAtZmRiYy00MTVlLWFmMDUtYjQ4YzI5NzQ2ZDc2IiwiZXhwIjoxNzgzNzE5MDU2fQ.wbIfljabzZU-jDifyMRZzB3KOFvLeEKvdjYLLUdoieA"
```

**Token Info:**
- Subject: super-claude-client
- Scope: read write admin
- Issued: 2026-01-11
- Expires: 2026-07-10 (180 days)

## Verify Connection

After adding, test the connection:

```bash
claude mcp list
# Should show super-claude as connected

# Or start Claude Code and try:
# "Use Super Claude to ping"
```

## Available Tools

Once connected, Claude Code has access to all Super Claude tools:
- `ping` - Health check
- `fs_list`, `fs_read`, `fs_write` - File operations
- `shell_exec` - Run commands
- `docker_ps`, `docker_logs`, `docker_restart` - Container management
- `context_load`, `context_get`, `context_update` - Domain context
- `auth_get`, `auth_set` - 1Password secrets
- `publish`, `unpublish` - Web-accessible files

## Token Regeneration

When the token expires, generate a new one:

**Option 1: From Claude.ai (with Super Claude connected)**
Ask me to generate a new Claude Code token.

**Option 2: From Synology SSH**
```bash
cd /volume1/docker/super-claude/auth-service
node jwt-utils.js generate claude-code 'read,write,admin' 180d
```

Then update Claude Code:
```bash
claude mcp remove super-claude
claude mcp add --transport http super-claude https://zanni.synology.me/mcp \
  --header "Authorization: Bearer NEW_TOKEN_HERE"
```

## Scope Options

You can configure where the MCP is available:

```bash
# Available only to you in current project (default)
claude mcp add --scope local ...

# Available only to you, all projects
claude mcp add --scope user ...

# Shared with project team via .mcp.json
claude mcp add --scope project ...
```

## Troubleshooting

**"Connection refused"**
- Check if containers are running: `docker ps` on Synology
- Verify DDNS is working: `ping zanni.synology.me`

**"401 Unauthorized"**
- Token may be expired, regenerate it
- Check token was copied correctly (no extra spaces)

**"Connection closed"**
- The MCP server may have restarted
- Try: `claude mcp remove super-claude` then re-add
