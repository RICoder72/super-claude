# Setup Guide

How to deploy Super Claude from scratch. Assumes Synology NAS with Docker.

## Prerequisites

- Synology NAS with Docker package installed
- Domain/DDNS pointing to your NAS (e.g., zanni.synology.me)
- SSL certificate (Let's Encrypt via Synology works great)
- 1Password account with service account capability
- Port 443 available for external access

## 1. Create Folder Structure

```bash
ssh your-nas

mkdir -p /volume1/docker/super-claude
cd /volume1/docker/super-claude

mkdir -p mcps/super-claude
mkdir -p shared
mkdir -p config
mkdir -p domains
```

## 2. Set Up 1Password Service Account

1. Go to https://my.1password.com/developer-tools/infrastructure-secrets/
2. Create a service account
3. Create a vault (e.g., "Key Vault") and grant access
4. Copy the service account token

```bash
# Create env file
echo "OP_SERVICE_ACCOUNT_TOKEN=ops_your_token_here" > config/.env
chmod 600 config/.env
```

## 3. Create Shared Module

Create `shared/op_client.py`:

```python
import os
from onepassword import Client

_client = None

async def _get_client():
    global _client
    if _client is None:
        token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
        if not token:
            raise ValueError("OP_SERVICE_ACCOUNT_TOKEN not set")
        _client = await Client.authenticate(
            auth=token,
            integration_name="Super Claude",
            integration_version="1.0.0"
        )
    return _client

async def get_secret(item_name: str, field: str = "credential", vault: str = "Key Vault") -> str:
    client = await _get_client()
    secret_ref = f"op://{vault}/{item_name}/{field}"
    return await client.secrets.resolve(secret_ref)

async def get_secret_by_ref(secret_ref: str) -> str:
    client = await _get_client()
    return await client.secrets.resolve(secret_ref)
```

## 4. Create MCP Server

Copy `server.py`, `Dockerfile`, and `pyproject.toml` to `mcps/super-claude/`.

See the actual files in that directory for current versions.

## 5. Build and Run

```bash
cd /volume1/docker/super-claude

# Build
sudo docker build -t super-claude -f mcps/super-claude/Dockerfile .

# Run with mounts
sudo docker run -d \
  --name super-claude \
  --env-file config/.env \
  -p 8000:8000 \
  -v /volume1/docker/super-claude:/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --restart unless-stopped \
  super-claude
```

## 6. Configure Reverse Proxy (Synology)

1. DSM → Control Panel → Login Portal → Advanced → Reverse Proxy
2. Create rule:
   - **Source**: HTTPS, your.domain.com, port 443
   - **Destination**: HTTP, localhost, port 8000
3. Assign your SSL certificate to this rule

## 7. Configure Port Forwarding (Router)

Forward external port 443 to your Synology's internal IP, port 443.

For Ubiquiti: UniFi Controller → Settings → Firewall & Security → Port Forwarding

## 8. Add Connector in Claude

1. Claude.ai or Claude mobile → Settings → Connectors
2. Add custom connector
3. URL: `https://your.domain.com/mcp`
4. Name it something recognizable

## 9. Test

In a new Claude conversation with the connector enabled:

> "Ping super claude and list the root directory"

Should return pong and show your folder structure.

## Troubleshooting

| Problem | Check |
|---------|-------|
| Container won't start | `docker logs super-claude` |
| Can't reach externally | Port forwarding, firewall, SSL cert |
| Tools not appearing | Disconnect/reconnect connector, new chat |
| Auth fails | Check .env file, service account token |
| Path errors | Ensure volume mounted at /data |
