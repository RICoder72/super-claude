# Super Claude

Personal MCP infrastructure that gives Claude persistent context, external API access, and self-modification capabilities across all interfaces (mobile, web, Claude Code).

## What This Is

A Docker-based MCP server running on Matthew's Synology NAS that provides:
- **Auth tools**: 1Password secret retrieval
- **Filesystem tools**: Read/write/manage files within the sandbox
- **Shell tools**: Execute commands
- **Docker tools**: Container management
- **Context tools**: Domain-specific knowledge loading

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
- **Containers**: super-claude (8000), super-claude-ops (8001), super-claude-router (8080)
- **Auth**: 1Password service account
- **Docker network**: super-claude_super-claude-net (all containers must be on this)

## Session Protocol

**In-flight:**
- When something significant happens (decision, architecture change, new capability, blocker), ask: "Worth saving X to state?"
- If yes, update state.json
- Don't prompt for minor/obvious things

**End-of-session:**
- User says "wrap up" or "end session"
- Review what happened, propose anything worth capturing
- Ask if user has anything to add
- Update state.json and close out

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
