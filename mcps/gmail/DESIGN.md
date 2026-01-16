# Gmail MCP Tool - Design Document

## Overview
Custom MCP tool providing full Gmail access (read, write, delete, flag, search) integrated into Super Claude. Credentials managed via 1Password OAuth2, exposed as MCP resources.

## Architecture

### Components
1. **Gmail OAuth2 Handler** - Manages authentication tokens, refresh cycles
2. **MCP Server** - Exposes tools for Claude to call
3. **API Methods** - Wrapper around Gmail API v1
4. **Credential Storage** - 1Password integration

### OAuth2 Flow
1. Initial setup: Matthew authorizes Gmail scopes
2. Token stored in 1Password (access_token, refresh_token, expiry)
3. Auto-refresh when token expires
4. Revocation on demand

## Gmail API Methods

### Core Operations
- `list_messages(query, max_results)` - Search with filter syntax
- `get_message(message_id)` - Fetch full message with attachments
- `send_message(to, subject, body, attachments)` - Compose and send
- `modify_message(message_id, add_labels, remove_labels)` - Flag, archive, etc.
- `delete_message(message_id)` - Permanent delete
- `trash_message(message_id)` - Move to trash

### Labels & Organization
- `list_labels()` - All user labels
- `create_label(name)` - New label
- `delete_label(label_id)` - Remove label

### Draft Management
- `create_draft(to, subject, body)` - Save as draft
- `send_draft(draft_id)` - Send saved draft
- `delete_draft(draft_id)` - Discard draft

## Integration Points

### Super Claude Container
- Python 3.11+ with `google-auth-oauthlib` and `google-auth-httplib2`
- MCP server runs on localhost:9001
- Mounts `/data/mcps/gmail/` for config

### 1Password
- Item: `Gmail OAuth - Super Claude`
- Fields: 
  - `client_id` - OAuth app ID
  - `client_secret` - OAuth app secret
  - `access_token` - Current token
  - `refresh_token` - Refresh token
  - `token_expiry` - ISO 8601 timestamp

### Docker Network
- Runs on `super-claude_super-claude-net`
- Accessible to super-claude container for tool registration

## File Structure
```
mcps/gmail/
├── DESIGN.md (this file)
├── server.py (MCP server, OAuth handler)
├── gmail_api.py (Gmail API wrapper)
├── requirements.txt
├── Dockerfile
├── credentials.json (local dev only, NOT committed)
└── .env (config, NOT committed)
```

## Security Considerations
- Never log access tokens or message content
- Scopes limited to Gmail only (no Drive, Calendar, etc.)
- Refresh tokens rotated automatically
- Rate limiting: Respect Gmail API quotas (10M per day)
- User confirmation required for destructive ops (delete, empty trash)

## Error Handling
- Token expired → Auto-refresh
- Rate limit hit → Exponential backoff
- Invalid query → Return clear error message
- Network failure → Retry with backoff

## Phase 1 (MVP)
- OAuth2 setup and token storage
- `list_messages()` with query
- `get_message()` 
- `send_message()`
- `modify_message()` (flag/archive)
- Basic error handling

## Phase 2 (Enhancements)
- `delete_message()` with confirmation
- Draft management
- Label creation/deletion
- Attachment handling
- Batch operations

## Testing Strategy
- Unit tests for API wrapper
- Integration tests with mock Gmail API
- Live testing against Matthew's account (once deployed)

## Deployment
1. Register OAuth app in Google Cloud Console
2. Store credentials in 1Password
3. Build Docker image for gmail MCP
4. Register as tool in super-claude container
5. Expose via MCP endpoint
