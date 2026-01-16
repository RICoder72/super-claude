# Operations Guide

Day-to-day operations, quirks, and troubleshooting.

## Connector Management

### Refreshing Tools

When you deploy new tools or update existing ones, Claude doesn't automatically see them. To refresh:

1. Click `...` next to your connector in Claude
2. Click "Disconnect"
3. Reconnect the connector
4. **Start a new chat** (important!)

This forces Claude to re-fetch the tool list from the MCP server.

### Tool Not Found Errors

If you get "Tool not found" after deploying:
1. Check container is running: `docker ps`
2. Check logs: `docker logs super-claude`
3. Disconnect/reconnect connector
4. Start fresh chat

### Debugging Tool List

From Synology SSH:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

This shows what tools the server is advertising.

## Container Operations

### View Logs
```bash
sudo docker logs super-claude
sudo docker logs -f super-claude  # Follow
sudo docker logs --tail 100 super-claude  # Last 100 lines
```

### Restart
```bash
sudo docker restart super-claude
```

### Rebuild After Code Changes
```bash
cd /volume1/docker/super-claude
sudo docker build -t super-claude -f mcps/super-claude/Dockerfile .
sudo docker stop super-claude
sudo docker rm super-claude
sudo docker run -d \
  --name super-claude \
  --env-file config/.env \
  -p 8000:8000 \
  -v /volume1/docker/super-claude:/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --restart unless-stopped \
  super-claude
```

## File System Notes

### Path Reference
- **Inside container**: `/data/` = `/volume1/docker/super-claude/` on host
- **All fs_* tools** use paths relative to `/data/`
- Example: `fs_read("domains/msf/msf.md")` reads `/volume1/docker/super-claude/domains/msf/msf.md`

### Sandboxing
Claude cannot access paths outside `/data/`. This is intentional:
- Safety against accidental damage
- Clear boundary for open-sourcing
- The `_validate_path()` function enforces this

### Shell Commands
`shell_exec` runs with cwd set to `/data/`, but commands execute inside the container, not on the host. This means:
- ✅ Can run Python, curl, basic Linux commands
- ✅ Can run `docker` commands (via mounted socket)
- ❌ Cannot `cd /volume1/...` (path doesn't exist in container)
- ❌ Cannot rebuild self (would kill the process)

## Self-Modification Limits

Claude CAN:
- Modify any file in `/data/` (including server.py)
- Restart other containers
- Stop/start containers
- View logs

Claude CANNOT:
- Rebuild the container it's running in
- Access files outside the sandbox
- Modify host system files

This is why we plan an ops container - mutual administration.

## Health Checks

Quick test sequence:
```
1. ping → "pong from Super Claude 🚀"
2. fs_list(".") → Shows folder structure  
3. docker_ps() → Shows running containers
4. auth_get("some-secret") → Returns secret value
```

If all four work, the system is healthy.

## 1Password Integration

Claude can both **read** and **create** secrets in 1Password:

**Read a secret:**
```
auth_get("GitHub PAT - Claude Code")
auth_get("API Key Name", "fieldname", "Vault Name")
```

**Create a secret:**
```
auth_set("New API Key", '{"credential": "the-secret-value"}')
auth_set("Full Example", '{"api_key": "xyz", "user_id": "123"}', vault="Key Vault", category="api_credential", notes="Optional notes")
```

Categories: `login`, `password`, `api_credential`, `secure_note`

## Backup

The entire super-claude folder can be backed up:
```bash
# From Synology
tar -czvf super-claude-backup-$(date +%Y%m%d).tar.gz /volume1/docker/super-claude
```

Or use Synology's Hyper Backup to back up the docker folder.

Critical files to preserve:
- `config/.env` (has your 1Password token)
- `domains/` (all your context)
- `shared/` (shared Python modules)
- `mcps/super-claude/server.py` (the actual tools)
