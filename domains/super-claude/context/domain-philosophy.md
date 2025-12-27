# Domain Philosophy

How to think about domains, when to create them, and design principles.

## What Is a Domain?

A domain is an isolated knowledge area with its own context, state, and reference files. Examples:
- **MSF** - Marvel Strike Force game strategy and roster
- **GRC** - Work compliance and governance stuff
- **Projects** - Meta-tracking of what to work on
- **Super Claude** - This infrastructure itself (meta!)

## When to Create a Domain

Create a domain when:
- You'll have multiple conversations about the same topic
- There's persistent state to track (roster, project status, etc.)
- You want Claude to "remember" preferences specific to that area
- The context is distinct enough to warrant isolation

Don't create a domain for:
- One-off questions
- Topics covered by Claude's general knowledge
- Things that don't need persistence

## Domain Structure

```
domains/{name}/
├── {name}.md      # Core context - always loaded first
├── state.json     # Lightweight session state
└── context/       # Reference files, loaded on demand
    ├── topic-a.md
    ├── topic-b.md
    └── ...
```

### The Main File ({name}.md)

This is the "brain" of the domain. It should contain:
- **What this domain is** - Brief description
- **Who you are in this context** - Profile, preferences, goals
- **How to respond** - Interaction patterns, format preferences
- **Pointers** - "For X, see context/Y.md"
- **Current focus** - What's active right now (or reference state.json)

Design principle: Someone (Claude) reading just this file should understand how to help you in this domain.

### State File (state.json)

Lightweight, changes often. Contains:
- Session metadata (last update, current focus)
- Volatile state that doesn't belong in markdown
- Quick-reference data Claude might need

Keep it small. If state is complex, it probably belongs in a context file.

### Context Files (context/*.md)

Reference material loaded on demand. Examples:
- `teams.md` - Team compositions for a game
- `roadmap.md` - Planned features for a project
- `decisions.md` - Architecture decision records

Design principle: Claude reads the main file, then pulls context files as needed based on what you ask.

## Token Efficiency

The domain system is designed to minimize token usage:

1. **Main file only** - Most questions can be answered with just {name}.md
2. **Pull on demand** - Context files loaded only when relevant
3. **Pointers over content** - Main file says "see context/X" rather than duplicating

Bad: Loading 50KB of context every conversation
Good: Loading 2KB main file, pulling specific 5KB files as needed

## Interaction Patterns

The main file should define how Claude responds in this domain. Examples:

```markdown
### When Asked "Who Am I Farming?"
**Response Format:** Bullet list with farming locations
**Source:** context/farming.md

### When Asked "What Team For X?"
**Response Format:** Numbered list of 5 characters
**Source:** context/teams.md
```

This lets Claude know what you expect without you having to explain every time.

## Domain Independence

Domains should be self-contained. If you deleted all other domains, each one should still work. This means:
- No cross-domain file references
- No shared state between domains
- Global preferences go in a global location (TBD)

Exception: The projects domain might reference other domains by name for tracking purposes.

## Creating a New Domain

1. Create the folder: `fs_mkdir("domains/{name}/context")`
2. Create the main file with structure above
3. Create minimal state.json
4. Add context files as needed
5. Test by asking Claude to "work on {name}"

Template:
```markdown
# {Domain Name}

Brief description of what this domain covers.

## About

Who you are in this context, what you're trying to accomplish.

## How to Respond

### When Asked "X"
- Format: ...
- Source: ...

## Current Focus

What's active right now.

## Pointers

- For topic A → context/a.md
- For topic B → context/b.md
```
