"""
Super Claude Storage Providers

Provider implementations for the storage interface.
"""

from .gdrive import GoogleDriveProvider
from .supernote_provider import SupernoteProvider

__all__ = [
    "GoogleDriveProvider",
    "SupernoteProvider"
]

# Provider registry for auto-discovery
PROVIDERS = {
    "gdrive": GoogleDriveProvider,
    "supernote": SupernoteProvider,
}
