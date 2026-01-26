# Super Claude Build & Deployment Scripts

## Quick Reference

| Script | Purpose |
|--------|---------|
| `rebuild-super-claude.sh` | Full rebuild of main MCP container |
| `rebuild-ops.sh` | Full rebuild of ops MCP container |
| `rebuild-all.sh` | Rebuild both containers |
| `dev-sync.sh` | Quick sync files during development (no rebuild) |

## How Docker Containers Work

Each container is built from a **Dockerfile** that specifies:
1. Base image (Python 3.12)
2. System dependencies (Docker CLI, git)
3. Python packages
4. Source code to copy in

**Key insight**: Code is copied INTO the image at build time. The running container has its own `/app/` directory that's separate from your `/data/` source files.

```
/data/mcps/super-claude/     Your source code (git tracked)
        │
        │  docker build (COPY command)
        │
        ▼
Container /app/              Copy of code inside container
```

## Development Workflow

### Option 1: Quick Iteration (Recommended for active development)

When you're actively editing code:

```bash
# Edit files in /data/mcps/super-claude/
# Then sync without full rebuild:
./scripts/dev-sync.sh super-claude

# Start new Claude chat to reconnect
```

**Pros**: Fast (seconds vs minutes)
**Cons**: Changes lost on container restart, dependencies not updated

### Option 2: Full Rebuild (For finalizing changes)

When changes are done or you've added new dependencies:

```bash
./scripts/rebuild-super-claude.sh

# Or rebuild everything:
./scripts/rebuild-all.sh

# Use --no-cache if something's stuck:
./scripts/rebuild-super-claude.sh --no-cache
```

**Pros**: Clean, repeatable, persists across restarts
**Cons**: Takes 1-2 minutes

### Option 3: From Claude (MCP Tools)

You can also rebuild from within a Claude conversation:

```
# From super-claude, rebuild ops:
rebuild_ops()

# From super-claude-ops, rebuild main:
rebuild_super_claude()
```

## Mutual Administration

The two MCP containers can rebuild each other:

```
super-claude  ──rebuild_ops()──►  super-claude-ops
      ▲                                  │
      └────rebuild_super_claude()────────┘
```

This means you're never locked out - if one container breaks, use the other to rebuild it.

## File Locations

```
/data/
├── mcps/
│   ├── super-claude/
│   │   ├── Dockerfile        # Build instructions
│   │   ├── server.py         # Main MCP server
│   │   ├── plugins/          # Plugin system
│   │   ├── core/             # Storage, etc.
│   │   └── services/         # Mail, calendar, etc.
│   │
│   └── ops/
│       ├── Dockerfile        # Build instructions
│       └── server.py         # Ops MCP server
│
├── shared/                   # Shared modules (copied to both)
├── scripts/                  # Build/deploy scripts
├── config/                   # .env and tokens
└── domains/                  # Your domain data
```

## Docker Compose (Alternative)

There's also a `docker-compose.yml` for running everything through nginx:

```bash
cd /data
docker-compose up -d --build           # Build and start all
docker-compose up -d --build super-claude  # Rebuild just one
docker-compose logs -f super-claude    # Watch logs
```

This routes everything through nginx on port 8080:
- `http://localhost:8080/mcp` → super-claude
- `http://localhost:8080/ops` → super-claude-ops

The shell scripts expose ports directly (8000, 8001) which is simpler for development.

## Troubleshooting

### Container won't start
```bash
docker logs super-claude  # Check for errors
./scripts/rebuild-super-claude.sh --no-cache  # Clean rebuild
```

### Changes not showing up
```bash
# Make sure you synced or rebuilt:
./scripts/dev-sync.sh super-claude

# Check what's actually in the container:
docker exec super-claude cat /app/server.py | head -20
```

### Need to see what's running
```bash
docker ps                           # Running containers
docker exec super-claude ls /app/   # Files in container
```
