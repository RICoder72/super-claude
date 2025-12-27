# Why Super Claude Exists

## The Problem

Matthew uses Claude across multiple interfaces:
- **Claude Mobile** - Voice input, on-the-go, preferred for casual use
- **Claude Web** - Desktop work, file uploads
- **Claude Code** - CLI, great for coding but not always convenient

Each conversation starts fresh. Claude doesn't remember:
- What project you're working on
- Your preferences and working style
- Context from previous sessions
- Access to your tools and APIs

## The Solution

Super Claude is a personal MCP (Model Context Protocol) server that gives Claude:
- **Persistent context** - Domain knowledge that survives across sessions
- **External access** - 1Password secrets, file storage, shell commands
- **Self-modification** - Claude can update its own knowledge and tools
- **Cross-device parity** - Same capabilities on phone, web, or CLI

## Matthew's Working Style

### Tracer Bullet Development
Before committing to a solution, run a minimal end-to-end test that proves the path works. Don't spec exhaustively then build - validate assumptions with working code early.

**Implications for Claude:**
- Suggest minimal proof-of-concept first
- Don't over-engineer the first pass
- Expect iteration - first version is for learning
- Ask "what's the simplest thing that would prove this works?"

### Session Patterns
- **5-minute sessions**: Quick questions, status checks, mobile voice
- **1-hour deep dives**: Building, planning, complex work
- **Iterative progress**: Small chunks across many sessions

### Preferences
- Prefers mobile/web over CLI when possible
- Uses Synology Drive for file sync across devices
- Likes concise responses, bullet points for action items
- Appreciates when Claude remembers context without being told

## Why MCP Over Alternatives

**Considered:**
- Git repos with CLAUDE.md files (was using this)
- Custom API server
- Cloud functions

**Chose MCP because:**
- Native Claude integration (appears as tools)
- Works on mobile now that remote MCP is supported
- Bidirectional - Claude can read AND write
- Extensible - add tools without changing Claude

## Design Principles

1. **Claude-first** - Optimize for Claude's use, not human interfaces
2. **Progressive loading** - Don't dump everything into context; load on demand
3. **Self-documenting** - Domain files explain how to use them
4. **Recoverable** - Text files, git-friendly, no complex state
5. **Sandboxed** - Can't break things outside super-claude directory
