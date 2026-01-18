"""
Super Claude Core Services

Provides platform-agnostic access to external capabilities:
- Storage: Cloud file storage (Google Drive, OneDrive, Dropbox)
- Mail: Email (Gmail, Outlook, IMAP)
- Calendar: Calendar events (Google Calendar, Outlook, CalDAV)

Each service follows the same pattern:
- interface.py: ABC defining the contract + dataclasses
- manager.py: Account CRUD, adapter registry, routing
- adapters/: Platform-specific implementations
"""

from pathlib import Path
import json

# Service token/config locations
CONFIG_DIR = Path("/data/config")
USER_SETTINGS_FILE = CONFIG_DIR / "user_settings.json"

# Default user settings
DEFAULT_USER_SETTINGS = {
    "timezone": "America/New_York",
    "locale": "en-US",
    "date_format": "12h"
}


def get_user_timezone() -> str:
    """Get user's configured timezone."""
    try:
        if USER_SETTINGS_FILE.exists():
            settings = json.loads(USER_SETTINGS_FILE.read_text())
            return settings.get("timezone", DEFAULT_USER_SETTINGS["timezone"])
    except Exception:
        pass
    return DEFAULT_USER_SETTINGS["timezone"]


def get_user_settings() -> dict:
    """Get all user settings."""
    try:
        if USER_SETTINGS_FILE.exists():
            return json.loads(USER_SETTINGS_FILE.read_text())
    except Exception:
        pass
    return DEFAULT_USER_SETTINGS.copy()
