# Reusable Prompts

Prompts for common Super Claude operations. Copy/paste as needed.

---

## Chat → Domain Update

**Use when:** You're in a regular Claude chat (with Super Claude tools connected) and want to capture valuable content before deleting the chat.

```
I want to capture the valuable content from this conversation before I delete it. Please:

1. Load the Super Claude domain system: call `context_list()` to see available domains
2. Identify which domain(s) this conversation relates to based on the topics we discussed
3. Load the relevant domain(s) with `context_load()`
4. Review this conversation and extract:
   - Key decisions or conclusions we reached
   - New information or insights worth preserving
   - Any preferences, facts, or frameworks I shared
   - Technical details or solutions that worked
5. Propose specific additions to the domain's context files or state.json
6. After I approve, make the updates using `fs_write()`, `fs_append()`, or `context_update()`
7. Confirm what was saved and where

Focus on durable knowledge, not ephemeral discussion. If something was just a quick Q&A with no lasting value, say so.
```

---

## Project Chat → Domain

**Use when:** You're in a Claude Project (no Super Claude access) and want to extract content to update or create a domain.

```
I want to extract the valuable content from this project and save it to my Super Claude domain system. This project doesn't have direct access to Super Claude tools, so please:

1. Review the project knowledge files (if any are attached)
2. Review the project instructions (if you can see them)
3. Review our conversation history in this project
4. Identify the core topics, decisions, frameworks, and insights worth preserving
5. Determine if this content should:
   a) Update an existing domain (if so, which one and what files)
   b) Create a new domain (if so, propose a name, description, and trigger keywords)
6. Output the content in a format I can copy/paste:
   - For existing domains: markdown sections to append to specific files
   - For new domains: complete file contents for {domain}.md, state.json, and any context/ files
```

---

## Domain Review (Batch)

**Use when:** You want to review all domains for cleanup, trigger updates, and chat consolidation (like we just did).

```
Let's do a domain review session. For each domain alphabetically:

1. Load the domain with `context_load()`
2. Check its triggers in `config/domain_triggers.json`
3. Search past chats for related content using `conversation_search()`
4. Assess:
   - Are triggers comprehensive? Suggest additions.
   - Is domain content well-populated?
   - Are there past chats that should be captured before deletion?
5. Make approved updates and note chats for manual deletion

Keep a running tally of chats to delete. At the end, give me the master list.
```

---

## New Domain Creation

**Use when:** Starting a new area of focus that deserves its own domain.

```
I want to create a new domain for [TOPIC]. Please:

1. Propose a domain name (short, lowercase, hyphenated if needed)
2. Write a description and suggest trigger keywords
3. Create the folder structure:
   - domains/{name}/{name}.md - main context file
   - domains/{name}/state.json - initial state
   - domains/{name}/context/ - folder for reference files
4. The {name}.md should include:
   - What this domain is about
   - How I want Claude to respond in this context
   - Key background/preferences I have
   - Pointers to context files
5. Add to config/domain_triggers.json
6. Commit and push

Ask me clarifying questions first if needed to make the domain useful.
```
