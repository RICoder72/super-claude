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
- **Storage tools**: Cloud storage abstraction (Google Drive, etc.)

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
| List storage | `storage_list_files("account", "/path")` |

## Session Protocol

**In-flight:**
- When something significant happens (decision, architecture change, new capability, blocker), mention it
- Don't prompt for minor/obvious things

**End-of-session (when user says "wrap up" or "end session"):**

Update these four files in `context/`:

| File | Update with... |
|------|----------------|
| `changelog.md` | Session summary: what we did, why, key decisions |
| `todo.md` | New items, completed items (move to changelog), priority changes |
| `features.md` | New capabilities, tools, or integrations added |
| `architecture.md` | New ADRs, diagram changes, infrastructure updates |

Then update `state.json`:
- `active_work`: Current focus for next session
- `last_session_summary`: One-line description

Finally, commit to git with descriptive message.

## Documentation

| Topic | Location |
|-------|----------|
| **Development docs** | |
| Features & capabilities | `context/features.md` |
| Change history | `context/changelog.md` |
| Backlog & roadmap | `context/todo.md` |
| System design & ADRs | `context/architecture.md` |
| **Reference docs** | |
| Why this exists | `context/why.md` |
| Deploy from scratch | `context/setup-guide.md` |
| Operations & troubleshooting | `context/operations.md` |
| Domain design philosophy | `context/domain-philosophy.md` |
| Folder structure | `context/file-structure.md` |
| Claude Code setup | `context/claude-code-setup.md` |
| Reusable prompts | `context/prompts.md` |

## Infrastructure

- **Host**: Synology RS1221+ with UPS
- **Network**: Ubiquiti, DDNS via zanni.synology.me
- **Containers**: super-claude (8000), super-claude-ops (8001), super-claude-router (8080), super-claude-auth (8002)
- **Auth**: 1Password service account + OAuth/JWT
- **Docker network**: super-claude_super-claude-net

## Matthew's Working Style

- **Tracer bullet first**: Prove it works minimally before building fully
- **Iterative**: First version is for learning, expect revision
- **Mobile-preferred**: Voice input, on-the-go usage
- **Concise responses**: Bullet points for actions, prose for explanations
