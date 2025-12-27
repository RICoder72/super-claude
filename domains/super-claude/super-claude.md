# Super Claude

Personal MCP infrastructure that gives Claude persistent context, external API access, and self-modification capabilities across all interfaces (mobile, web, Claude Code).

## What This Is

A Docker-based MCP server running on Matthew's Synology NAS that provides:
- **Auth tools**: 1Password secret retrieval
- **Filesystem tools**: Read/write/manage files within the sandbox
- **Shell tools**: Execute commands
- **Docker tools**: Container management
- **Context tools**: Domain-specific knowledge loading (planned)

## Quick Reference

| Need to... | Do this |
|------------|---------|
| Check health | `ping` → "pong from Super Claude 🚀" |
| See files | `fs_list("path")` |
| Read file | `fs_read("path")` |
| Write file | `fs_write("path", "content")` |
| Run command | `shell_exec("command")` |
| View containers | `docker_ps()` |
| Get secret | `auth_get("item name")` |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Claude Interfaces                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Mobile   │  │ Web      │  │ Code     │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
└───────┼─────────────┼─────────────┼────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │ (MCP over HTTPS)
                      ▼
        ┌─────────────────────────────┐
        │  super-claude (Docker)      │
        │  zanni.synology.me/mcp      │
        │                             │
        │  /data (mounted volume)     │
        │  ├── mcps/                  │
        │  ├── domains/               │
        │  ├── shared/                │
        │  └── config/                │
        └─────────────────────────────┘
```

## Domain System

Domains are isolated knowledge areas. Each contains:
- `{domain}.md` - Always loaded. Player profile, goals, how to respond.
- `state.json` - Lightweight session state.
- `context/` - Reference files loaded on demand.

**Active domains:** super-claude, projects
**Planned domains:** msf, grc

## Infrastructure

- **Host**: Synology RS1221+ with UPS
- **Network**: Ubiquiti, DDNS via zanni.synology.me
- **Container**: super-claude on port 8000 → 443 via reverse proxy
- **Auth**: 1Password service account

## Current Tools

| Tool | Purpose |
|------|---------|
| `ping` | Health check |
| `auth_get` | Get secret by item name |
| `auth_get_ref` | Get secret by full reference |
| `fs_list` | List directory |
| `fs_read` | Read file |
| `fs_write` | Write/create file |
| `fs_append` | Append to file |
| `fs_delete` | Delete file |
| `fs_mkdir` | Create directory |
| `fs_rmdir` | Remove directory |
| `fs_move` | Move/rename |
| `fs_copy` | Copy file/directory |
| `shell_exec` | Run shell command |
| `docker_ps` | List containers |
| `docker_logs` | View container logs |
| `docker_restart` | Restart container |
| `docker_stop` | Stop container |
| `docker_start` | Start container |

## Pointers

| Topic | Location |
|-------|----------|
| Why this exists, design principles | `context/why.md` |
| Deploy from scratch | `context/setup-guide.md` |
| Day-to-day operations, troubleshooting | `context/operations.md` |
| How to create/design domains | `context/domain-philosophy.md` |
| What's in each folder | `context/file-structure.md` |
| Planned features | `context/roadmap.md` |
| Architecture decisions | `context/decisions.md` |
| Change history | `context/changelog.md` |

## Matthew's Working Style

- **Tracer bullet first**: Prove it works minimally before building fully
- **Iterative**: First version is for learning, expect revision
- **Mobile-preferred**: Voice input, on-the-go usage
- **Concise responses**: Bullet points for actions, prose for explanations
