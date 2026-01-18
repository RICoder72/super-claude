"""
Infrastructure Secrets Backends

Available backends for secrets storage.
"""

from .onepassword import OnePasswordBackend

# Registry of available backends
BACKENDS = {
    "onepassword": OnePasswordBackend,
    "1password": OnePasswordBackend,  # Alias
}

__all__ = ["BACKENDS", "OnePasswordBackend"]
