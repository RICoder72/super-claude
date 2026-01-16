"""
Plugin Base Class

Defines the interface that all Super Claude plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable


class SuperClaudePlugin(ABC):
    """Base class for Super Claude plugins."""
    
    def __init__(self):
        """Initialize the plugin. Override in subclass if needed."""
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, Any] = {}
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the plugin and register tools.
        
        Must populate self.tools with tool functions and self.metadata
        with plugin information (name, version, description, etc).
        
        Example:
            self.metadata = {
                "name": "auth",
                "version": "0.1.0",
                "description": "Authentication and secret management"
            }
            self.tools = {
                "auth_get": self.auth_get,
                "auth_set": self.auth_set,
            }
        """
        pass
    
    def get_tools(self) -> Dict[str, Callable]:
        """Return all tools provided by this plugin."""
        return self.tools
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata."""
        return self.metadata
    
    def on_load(self) -> None:
        """Called when plugin is loaded. Override for custom setup."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded. Override for cleanup."""
        pass
