"""
Infrastructure Secrets Interface

Defines the abstract interface for secrets backends.
This is INTERNAL infrastructure, not exposed as MCP tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class SecretItem:
    """Represents a secret item."""
    id: str
    title: str
    vault: str
    category: str
    fields: Dict[str, str]  # field_name -> value
    notes: Optional[str] = None


class SecretsBackend(ABC):
    """
    Abstract base class for secrets backends.
    
    Implementations provide access to a specific secrets provider
    (1Password, Bitwarden, encrypted local files, etc.)
    """
    
    backend_type: str = "base"
    
    def __init__(self, config: dict):
        """
        Initialize the backend.
        
        Args:
            config: Backend-specific configuration dict
        """
        self.config = config
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Initialize connection to the secrets provider.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the secrets provider."""
        pass
    
    @abstractmethod
    async def get(self, item: str, field: str = "credential") -> str:
        """
        Get a secret value.
        
        Args:
            item: Item name or identifier
            field: Field name within the item (default: "credential")
        
        Returns:
            The secret value
            
        Raises:
            KeyError: If item or field not found
            ConnectionError: If not connected
        """
        pass
    
    @abstractmethod
    async def get_ref(self, reference: str) -> str:
        """
        Get a secret using a provider-specific reference URI.
        
        Args:
            reference: Full reference (e.g., "op://vault/item/field" for 1Password)
        
        Returns:
            The secret value
            
        Raises:
            KeyError: If reference not found
            ValueError: If reference format invalid
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        title: str,
        fields: Dict[str, str],
        category: str = "api_credential",
        notes: Optional[str] = None
    ) -> SecretItem:
        """
        Create or update a secret item.
        
        Args:
            title: Item title
            fields: Dict of field names to values
            category: Item category (backend-specific)
            notes: Optional notes
        
        Returns:
            The created/updated SecretItem
        """
        pass
    
    @abstractmethod
    async def delete(self, item: str) -> bool:
        """
        Delete a secret item.
        
        Args:
            item: Item name or identifier
        
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """
        List secret item names.
        
        Args:
            prefix: Optional prefix to filter by
        
        Returns:
            List of item names/titles
        """
        pass
    
    @abstractmethod
    async def exists(self, item: str) -> bool:
        """
        Check if an item exists.
        
        Args:
            item: Item name or identifier
        
        Returns:
            True if exists
        """
        pass
