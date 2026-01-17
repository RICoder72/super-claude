"""
Super Claude Storage Providers

Provider implementations for the storage interface.
"""

from .gdrive import GoogleDriveProvider

__all__ = [
    "GoogleDriveProvider",
]

# Provider registry for auto-discovery
PROVIDERS = {
    "gdrive": GoogleDriveProvider,
}
