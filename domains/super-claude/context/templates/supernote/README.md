# Super Claude Plugin: Supernote

Sync [Supernote](https://supernote.com/) handwritten notes with Super Claude domains via cloud storage.

## Features

- **Pull notes** from Supernote device (via cloud sync)
- **Convert** .note files to PNG/PDF for viewing
- **Extract markdown** from handwritten content using Claude's vision
- **Push documents** (PDFs, converted markdown) back to Supernote
- **Annotation support** - merge .mark files with PDFs
- **Archive management** - track processed vs pending notes

## Requirements

### System Dependencies

- **supernote-tool** - CLI for .note file conversion
  ```bash
  pip install supernote-tool
  ```

### Python Dependencies

Installed automatically:
- `reportlab` - PDF generation for markdown → PDF
- `pymupdf` - PDF manipulation for annotation merging

### Cloud Storage

Supernote must sync to a cloud storage provider that Super Claude can access:
- Dropbox (recommended - native Supernote support)
- Google Drive
- OneDrive

## Installation

```
plugin_install("https://github.com/yourusername/super-claude-plugin-supernote")
```

## Setup

Configure for a domain:

```python
supernote_setup(
    domain="mydomain",
    account="dropbox",           # Your storage account name
    subfolder="work",            # Subfolder on Supernote (Note/work/, Document/work/)
    sync_notes=True,
    sync_documents=True,
    convert_to="png"
)
```

## Usage

### Pull & Process Notes

```python
# Download new notes from device
supernote_pull("mydomain")

# List available notes
supernote_list_notes("mydomain")

# View note pages (returns images for Claude vision)
supernote_read_note("mydomain", "20260121_meeting")

# Extract to markdown
supernote_extract_markdown("mydomain", "20260121_meeting", "documents/meeting.md")

# Mark as processed (archives locally, deletes from device)
supernote_mark_processed("mydomain", "20260121_meeting")
```

### Send Documents to Supernote

```python
# Convert markdown to PDF and push
supernote_send_markdown("mydomain", "context/agenda.md")

# Or convert separately
supernote_md2pdf("mydomain", "context/agenda.md")
supernote_push("mydomain")
```

## Tools Reference

| Tool | Description |
|------|-------------|
| `supernote_setup` | Configure sync for a domain |
| `supernote_status` | Show current configuration |
| `supernote_pull` | Download and convert notes |
| `supernote_push` | Upload documents to device |
| `supernote_list_remote` | List files on device |
| `supernote_list_notes` | List local notes (pending/archived) |
| `supernote_read_note` | View note as images |
| `supernote_read_page` | View single page |
| `supernote_extract_markdown` | Extract handwriting to markdown |
| `supernote_note2txt` | Extract embedded text |
| `supernote_note2png` | Convert to PNG images |
| `supernote_note2pdf` | Convert to PDF |
| `supernote_md2pdf` | Convert markdown to PDF |
| `supernote_send_markdown` | Convert + stage + push markdown |
| `supernote_mark_processed` | Archive note, delete from device |
| `supernote_unprocess` | Restore archived note |
| `supernote_read_annotations` | Merge .mark with PDF |

## Architecture

```
Supernote Device → (auto-sync) → Cloud Storage ← (storage_* tools) ← Super Claude
                                      ↓
                              Domain plugin folder
                              ├── notes/        (pending .note files)
                              ├── converted/    (PNG/PDF/TXT)
                              ├── documents/    (files to push)
                              └── archive/      (processed notes)
```

## License

MIT
