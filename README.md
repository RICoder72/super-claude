# Super Claude

Personal MCP infrastructure that gives Claude persistent context, external API access, and self-modification capabilities across all interfaces (mobile, web, Claude Code).

## What Is This?

Super Claude is a Docker-based [MCP](https://modelcontextprotocol.io/) server designed to run on a home NAS. It gives Claude:

- **Persistent context** - Domain knowledge that survives across sessions
- **External access** - 1Password secrets, file storage, shell commands
- **Self-modification** - Claude can update its own knowledge and tools
- **Cross-device parity** - Same capabilities on phone, web, or CLI

## Features

| Tool Category | Capabilities |
|---------------|--------------|
| **Auth** | 1Password secret retrieval |
| **Filesystem** | Read, write, delete, move, copy files (sandboxed) |
| **Shell** | Execute commands |
| **Docker** | List, start, stop, restart containers |
| **Context** | Domain-specific knowledge loading (planned) |

## Quick Start

See `domains/_template/` for the domain structure, or check the [Setup Guide](domains/super-claude/context/setup-guide.md) for full deployment instructions.

### Prerequisites

- Synology NAS (or similar) with Docker
- Domain/DDNS with SSL certificate
- 1Password account with service account

### Basic Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/super-claude.git
cd super-claude

# Configure
cp config/.env.example config/.env
# Edit .env with your 1Password token

# Build and run
docker build -t super-claude -f mcps/super-claude/Dockerfile .
docker run -d \
  --name super-claude \
  --env-file config/.env \
  -p 8000:8000 \
  -v $(pwd):/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --restart unless-stopped \
  super-claude
```

Then add as a connector in Claude with URL: `https://your.domain.com/mcp`

## Domain System

Domains are isolated knowledge areas with their own context and state:

```
domains/{name}/
├── {name}.md      # Core context - always loaded
├── state.json     # Lightweight session state  
└── context/       # Reference files, loaded on demand
```

See `domains/_template/` for a starting point.

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
        │                             │
        │  /data (mounted volume)     │
        │  ├── mcps/                  │
        │  ├── domains/               │
        │  ├── shared/                │
        │  └── config/                │
        └─────────────────────────────┘
```

## Documentation

Full documentation lives in the super-claude domain itself:

- [Why Super Claude Exists](domains/super-claude/context/why.md)
- [Setup Guide](domains/super-claude/context/setup-guide.md)
- [Operations Guide](domains/super-claude/context/operations.md)
- [Domain Philosophy](domains/super-claude/context/domain-philosophy.md)
- [File Structure](domains/super-claude/context/file-structure.md)
- [Roadmap](domains/super-claude/context/roadmap.md)
- [Architecture Decisions](domains/super-claude/context/decisions.md)

## License

MIT
