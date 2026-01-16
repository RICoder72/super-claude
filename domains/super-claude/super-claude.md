# Super Claude (Development Domain)

> **Meta note**: This domain is for *building and maintaining* Super Claude itself—the infrastructure, containers, MCP code, and domain system. All other domains *use* Super Claude; this one *is about* Super Claude. Load this when working on the system itself, not when using it for other purposes.

Personal MCP infrastructure that gives Claude persistent context, external API access, and self-modification capabilities across all interfaces (mobile, web, Claude Code).

## What This Is

A Docker-based MCP server running on Matthew's Synology NAS that provides:
- **Auth tools**: 1Password secret retrieval and storage
- **Filesystem tools**: Read/write/manage files within the sandbox
- **Shell tools**: Execute commands
- **Docker tools**: Container management
- **Context tools**: Domain-specific knowledge loading
- **Publish tools**: Make files web-accessible

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
| Store secret | `auth_set("title", '{"credential": "value"}')` |
| Load domain | `context_load("domain-name")` |
| Publish file | `publish("path/to/file")` |

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

**Active domains**: See `context_list()` for current inventory.

## Infrastructure

- **Host**: Synology RS1221+ with UPS
- **Network**: Ubiquiti, DDNS via zanni.synology.me
- **Containers**: super-claude (8000), super-claude-ops (8001), super-claude-router (8080)
- **Auth**: 1Password service account + OAuth/JWT
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
| Claude Code integration | `context/claude-code-setup.md` |
| Planned features | `context/roadmap.md` |
| Architecture decisions | `context/decisions.md` |
| Change history | `context/changelog.md` |
| Reusable prompts | `context/prompts.md` |

## Matthew's Working Style

- **Tracer bullet first**: Prove it works minimally before building fully
- **Iterative**: First version is for learning, expect revision
- **Mobile-preferred**: Voice input, on-the-go usage
- **Concise responses**: Bullet points for actions, prose for explanations
