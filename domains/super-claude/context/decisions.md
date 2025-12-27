# Architecture Decisions

## ADR-001: Single MCP vs Multiple
**Date**: 2024-12-27
**Status**: Decided

**Context**: Should we have separate MCPs for auth, filesystem, docker, etc.?

**Decision**: Single MCP (`super-claude`) with all tools.

**Rationale**:
- Simpler connector management (one URL)
- Shared code/state between tools
- Can always split later if needed
- Auth MCP was separate initially, merged it in

---

## ADR-002: Filesystem Sandboxing
**Date**: 2024-12-27
**Status**: Decided

**Context**: Should Claude have full NAS access or be sandboxed?

**Decision**: Sandbox to `/volume1/docker/super-claude` (mounted as `/data`).

**Rationale**:
- Safety: Can't accidentally delete system files
- Open source friendly: Clear boundary for personal data
- Still has full access within sandbox
- Can always expand later if needed

---

## ADR-003: Domain Structure
**Date**: 2024-12-27
**Status**: Decided

**Context**: How should domain knowledge be organized?

**Decision**: 
```
domains/{name}/
├── {name}.md      # Always loaded, core context
├── state.json     # Session state, lightweight
└── context/       # Reference files, loaded on demand
```

**Rationale**:
- Main file is the "brain" - player profile, interaction patterns
- state.json is minimal, changes often
- context/ files are stable reference, pulled as needed
- Keeps token usage low (don't load everything every time)

---

## ADR-004: Ops Container for Self-Modification
**Date**: 2024-12-27
**Status**: Proposed

**Context**: Super-claude can't rebuild itself (would kill the process).

**Decision**: Create separate `super-claude-ops` container that can rebuild super-claude, and vice versa.

**Rationale**:
- Mutual administration capability
- Natural guardrail against self-destruction
- Ops can handle scheduled tasks, backups
- Two containers watching each other

---

## ADR-005: Git Strategy
**Date**: 2024-12-27
**Status**: Proposed

**Context**: How to version control and potentially open source?

**Decision**: 
- Public repo: `super-claude` (framework, template domain)
- Private repo: `super-claude-domains` (personal domain content)

**Rationale**:
- Framework is useful to others
- Personal game data, work stuff stays private
- Clean separation
- .gitignore excludes domains/* except _template/
