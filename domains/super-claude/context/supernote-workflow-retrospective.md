# Supernote Workflow Retrospective

**Date**: 2026-01-21
**Test**: Push PDF to Supernote → User annotates → Pull and process

## What We Tested

1. Generate a "High Priority Projects" PDF from Burrillville todo list
2. Push to Supernote
3. User marks up PDF and creates a new handwritten note
4. Pull everything back
5. Read/extract the content

## Problems Identified

### 1. Wrong Container for File Creation
**What happened**: I created the PDF generation script in `/home/claude` (Claude.ai container), then tried to `cp` it to `/data` (Super Claude container). Failed because they're different filesystems.

**Fix needed**: Always use Super Claude tools (`fs_write`, `shell_exec`) for file operations, not Claude.ai's computer tools. Or better: use `supernote_send_markdown` which handles everything.

### 2. Path Discovery Thrashing
**What happened**: Multiple `fs_list` calls trying to find where Supernote stores things:
- `domains/burrillville/supernote` (doesn't exist)
- `domains/burrillville` 
- `state.json`
- `data/`
- `mcps/super-claude/plugins`

**Fix needed**: I should know the convention: `domains/{name}/plugins/supernote/{notes,documents,converted,archive}/`

### 3. supernote_read_annotations Tool Not Registered
**What happened**: The code for `supernote_read_annotations` exists in the plugin (line ~380), and it's in the tools dict, but calling it returned "tool not found".

**Root cause**: Unknown - need to investigate. The tool is in `self.tools` dict in `initialize()`.

### 4. No Automatic Extraction on Pull
**What happened**: `supernote_pull` downloads .note files and converts to PNG, but doesn't extract text. I had to manually call `supernote_read_note` which returns images, then I have to visually read them.

**Ideal behavior**: Pull should:
1. Download .note files
2. Convert to PNG (done)
3. **NEW**: Run vision/OCR and extract to markdown file
4. Store markdown alongside PNGs for text-based retrieval

### 5. No Automatic .mark Processing on Pull
**What happened**: Pull downloads .mark files but doesn't process them. I had to manually run:
```bash
supernote-tool convert -t png -a --exclude-background documents/High_Priority_Projects_2026-01-21.pdf.mark converted/...
```

**Ideal behavior**: Pull should automatically:
1. Detect .mark files
2. Convert to transparent PNGs
3. Merge with original PDF to create `*_annotated.pdf`

### 6. Tried to Pull Images Into Context
**What happened**: I tried using `view` tool on converted PNGs, tried downloading via curl, etc. Wasteful and doesn't work cross-container.

**Correct approach**: 
- For my viewing: Use `publish` to make URL accessible
- For Claude's viewing: supernote_read_note returns Image objects (works)
- For text content: Should have markdown extraction, no images needed

### 7. Workflow Didn't Stay in Super Claude
**What happened**: Mixed Claude.ai tools (create_file, bash_tool, view) with Super Claude tools. Caused confusion and failures.

**Fix needed**: When working with Supernote, stay entirely in Super Claude tools.

## Proposed Improvements

### Immediate (This Session)

1. **Fix supernote_read_annotations registration** - Debug why tool isn't available
2. **Add auto-.mark processing to pull** - When .mark files are downloaded, auto-convert and merge
3. **Add markdown extraction** - After PNG conversion, run OCR/vision and save .md file

### Workflow (Claude Behavior)

1. **Use supernote_send_markdown** for pushing documents - don't manually create/copy/push
2. **Never use Claude.ai container tools for Super Claude files**
3. **Don't pull images into context** - use publish for viewing, rely on text extraction

### Architecture (Future)

1. **Async processing** - Pull could trigger background jobs that process without blocking
2. **Event-driven** - Cloud storage webhook triggers pull automatically when Supernote syncs
3. **Smart extraction** - Different templates for different note types (meeting notes, todos, freeform)

## Ideal End State

```
User: "Process my Supernote notes"

Claude: [calls supernote_pull]
→ Downloads 2 new .note files, 1 .mark file
→ Converts .note to PNG (background)
→ Extracts text to .md (background)  
→ Merges .mark with PDF (background)

Claude: "Found 2 new notes and 1 annotated PDF. Here's what I extracted:

**Note 1 (Budget Board 01/21)**
- Work with Leslie by 3/1 to solidify grants before budget

**High Priority Projects (annotated)**
- [extracted checkmarks and notes from your markup]

Want me to add these to the todo list?"
```

No images in context. No manual tool calls. Just text results.


---

## Resolution (2026-01-21)

### Changes Made

**Plugin v0.10.0:**
1. Added `_process_mark_file()` helper method for annotation processing
2. Modified `supernote_pull()` to automatically process downloaded .mark files:
   - Converts .mark → transparent PNGs
   - Merges with original PDF
   - Creates `*_annotated.pdf`
3. Updated output messages to show processing results

### Remaining Work

1. **Markdown extraction** - The big missing piece. Need to run vision/OCR on converted PNG pages and extract to .md file. This would make content available as text without pulling images into context.

2. **Tool schema caching** - Documented limitation: new tools added to plugins aren't visible until a new conversation starts. This is an MCP client caching issue, not fixable server-side.

3. **Claude workflow documentation** - Need clear guidance for Claude:
   - Use `supernote_send_markdown` for pushing docs (not manual PDF creation)
   - Never use Claude.ai container tools for Super Claude files
   - Don't pull images into context - use `publish` for viewing, rely on text extraction

### Ideal Workflow (Updated)

```
User: "Process my Supernote notes"

Claude: [calls supernote_pull]
→ Downloads 2 new .note files, 1 .mark file
→ Converts .note → PNG ✅
→ Extracts .note text → .md (TODO)
→ Converts .mark → PNG ✅  
→ Merges .mark with PDF → _annotated.pdf ✅

Claude: "Found 2 new notes and 1 annotated PDF:

**Note 1 (20260121_183220)**
[extracted markdown content here - TODO]

**High Priority Projects (annotated)**
Created annotated PDF. View at: [published URL]

Want me to add extracted items to the todo list?"
```
