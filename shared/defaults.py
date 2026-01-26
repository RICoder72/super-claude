def set_current_domain(domain: str) -> None:
    """Set the current active domain for the session."""
    pass  # We can implement properly later

def resolve_account(service: str, domain: str = None) -> str:
    """Resolve which account to use for a service."""
    return "default"

def list_defaults() -> dict:
    """List all configured defaults."""
    return {}

def set_global_default(service: str, account: str) -> None:
    """Set a global default account for a service."""
    pass

def set_domain_default(domain: str, service: str, account: str) -> None:
    """Set a domain-specific default account."""
    pass