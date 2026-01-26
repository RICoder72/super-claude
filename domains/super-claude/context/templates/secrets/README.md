# Super Claude Plugin: Secrets

User-facing credential and password storage for Super Claude. Store API keys, service credentials, and other sensitive data that Claude can use on your behalf.

## Features

- **Account-based organization** - Group secrets by service/account
- **Secure storage** - Credentials stored encrypted in Super Claude's data directory
- **Simple API** - Get, set, list, delete operations
- **Integration ready** - Use stored credentials with other plugins and tools

## Installation

```
plugin_install("https://github.com/yourusername/super-claude-plugin-secrets")
```

## Usage

### Managing Accounts

```python
# Add a new account/service
secrets_add_account("github", description="GitHub API access")

# List all accounts
secrets_list_accounts()

# Remove an account (and all its secrets)
secrets_remove_account("github")
```

### Managing Secrets

```python
# Store a secret
secrets_set("github", "api_token", "ghp_xxxxxxxxxxxx")
secrets_set("github", "username", "myuser")

# Retrieve a secret
secrets_get("github", "api_token")

# List secrets in an account (shows keys, not values)
secrets_list("github")

# Delete a secret
secrets_delete("github", "api_token")
```

## Tools Reference

| Tool | Description |
|------|-------------|
| `secrets_list_accounts` | List all configured accounts |
| `secrets_add_account` | Create a new account/service |
| `secrets_remove_account` | Delete an account and all secrets |
| `secrets_list` | List secret keys in an account |
| `secrets_get` | Retrieve a secret value |
| `secrets_set` | Store a secret value |
| `secrets_delete` | Delete a secret |

## Storage

Secrets are stored in `/data/config/user_secrets.json` (encrypted at rest if Super Claude is configured with encryption).

## Security Notes

- Secrets are accessible to Claude during conversations
- Do not store secrets you wouldn't want Claude to use
- Consider using 1Password integration for more sensitive credentials
- Secrets persist across container restarts

## Use Cases

- API tokens for web services
- Database credentials for automation
- Service account passwords
- License keys
- Any credential Claude needs to act on your behalf

## License

MIT
