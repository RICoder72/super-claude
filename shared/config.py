"""
Shared configuration constants for Super Claude MCPs.

Import from here to avoid duplication across server.py, ops, and plugins.
"""

from pathlib import Path

# Base paths
SUPER_CLAUDE_ROOT = Path("/data")
DOMAINS_DIR = SUPER_CLAUDE_ROOT / "domains"
CONFIG_DIR = SUPER_CLAUDE_ROOT / "config"
OUTPUTS_DIR = SUPER_CLAUDE_ROOT / "outputs"
BACKUPS_DIR = SUPER_CLAUDE_ROOT / "backups"
MCPS_DIR = SUPER_CLAUDE_ROOT / "mcps"

# Docker
DOCKER_NETWORK = "super-claude_super-claude-net"

# Public URLs
PUBLIC_BASE_URL = "https://zanni.synology.me/super-claude-output"

# Paths within mcps/super-claude
PLUGINS_DIR = MCPS_DIR / "super-claude" / "plugins"
CORE_DIR = MCPS_DIR / "super-claude" / "core"
PROVIDERS_DIR = MCPS_DIR / "super-claude" / "providers"

# Storage config
STORAGE_CONFIG = CONFIG_DIR / "storage_accounts.json"
