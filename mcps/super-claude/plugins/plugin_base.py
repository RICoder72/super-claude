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
        with plugin information.
        
        Required metadata fields:
            - name: Plugin identifier
            - version: Semantic version
            - description: What this plugin does
        
        Recommended metadata fields for usage guidance:
            - triggers: List of keywords/phrases that suggest this plugin
            - workflows: Dict of workflow_name -> description of common patterns
            - anti_patterns: List of things Claude should NOT do when this applies
        
        Example:
            self.metadata = {
                "name": "supernote",
                "version": "1.0.0",
                "description": "Supernote sync with two-phase workflow",
                "triggers": ["supernote", "handwritten notes", "stylus notes"],
                "workflows": {
                    "process_notes": "pull → list_unprocessed → process_note → mark_processed"
                },
                "anti_patterns": [
                    "Don't manually read from plugins/supernote/inbox/"
                ]
            }
            self.tools = {
                "supernote_pull": self.supernote_pull,
            }
        """
        pass
    
    def get_tools(self) -> Dict[str, Callable]:
        """Return all tools provided by this plugin."""
        return self.tools
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata."""
        return self.metadata
    
    def get_usage(self) -> str:
        """
        Generate usage guide from metadata.
        
        Returns a formatted string with:
        - Plugin name and description
        - When to use it (triggers)
        - Common workflows
        - Anti-patterns (what NOT to do)
        - Available tools
        
        Subclasses can override for custom documentation.
        """
        meta = self.metadata
        name = meta.get("name", "unknown")
        version = meta.get("version", "?")
        description = meta.get("description", "No description")
        
        lines = [
            f"📖 **{name}** v{version}",
            "═" * 50,
            "",
            f"**Description:** {description}",
            "",
        ]
        
        # Triggers - when to think of this plugin
        triggers = meta.get("triggers", [])
        if triggers:
            lines.append("**When to use** (trigger phrases):")
            for t in triggers:
                lines.append(f"  • \"{t}\"")
            lines.append("")
        else:
            lines.append("⚠️ **No triggers defined** - consider adding trigger phrases")
            lines.append("")
        
        # Workflows - common patterns
        workflows = meta.get("workflows", {})
        if workflows:
            lines.append("**Common Workflows:**")
            for name, desc in workflows.items():
                lines.append(f"  **{name}:**")
                lines.append(f"    {desc}")
            lines.append("")
        
        # Anti-patterns - what NOT to do
        anti_patterns = meta.get("anti_patterns", [])
        if anti_patterns:
            lines.append("**Don't do this** (anti-patterns):")
            for ap in anti_patterns:
                lines.append(f"  ❌ {ap}")
            lines.append("")
        
        # Available tools
        if self.tools:
            lines.append("**Available Tools:**")
            for tool_name in sorted(self.tools.keys()):
                func = self.tools[tool_name]
                doc = func.__doc__
                if doc:
                    # Get first line of docstring
                    first_line = doc.strip().split("\n")[0]
                    lines.append(f"  • `{tool_name}` - {first_line}")
                else:
                    lines.append(f"  • `{tool_name}`")
            lines.append("")
        
        return "\n".join(lines)
    
    def on_load(self) -> None:
        """Called when plugin is loaded. Override for custom setup."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded. Override for cleanup."""
        pass
