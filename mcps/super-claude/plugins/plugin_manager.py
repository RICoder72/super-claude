"""
Plugin Manager Tool

Provides runtime management of plugins including dynamic reload.
"""

from plugin_loader import PluginLoader
from pathlib import Path
import json


class PluginManager:
    """Manages plugin lifecycle and capabilities."""
    
    def __init__(self, loader: PluginLoader):
        """
        Initialize plugin manager.
        
        Args:
            loader: PluginLoader instance
        """
        self.loader = loader
    
    def plugin_status(self) -> str:
        """Get status of all loaded plugins."""
        info = self.loader.get_plugin_info()
        
        lines = [
            "🔌 Plugin Status",
            "─" * 40,
            f"Loaded: {info['plugin_count']} plugins",
            f"Tools: {info['tool_count']} total",
            ""
        ]
        
        for plugin_name, plugin_info in info["plugins"].items():
            lines.append(f"✅ {plugin_name}")
            lines.append(f"   Version: {plugin_info.get('version', 'unknown')}")
            lines.append(f"   Description: {plugin_info.get('description', 'N/A')}")
            lines.append(f"   Tools: {', '.join(plugin_info.get('tools', []))}")
            lines.append("")
        
        return "\n".join(lines)
    
    def reload_changed(self) -> str:
        """
        Check for changed plugins and reload them.
        
        Returns:
            Summary of reloaded plugins
        """
        changed = self.loader.check_for_changes()
        
        if not changed:
            return "✅ No plugin changes detected"
        
        lines = [f"🔄 Reloading {len(changed)} plugin(s):", ""]
        
        for plugin_name in changed:
            if plugin_name in self.loader.loaded_plugins:
                # Reload existing
                success = self.loader.reload_plugin(plugin_name)
                status = "✅" if success else "❌"
                lines.append(f"{status} Reloaded: {plugin_name}")
            else:
                # Load new
                success = self.loader.load_plugin(plugin_name)
                status = "✅" if success else "❌"
                lines.append(f"{status} Loaded: {plugin_name}")
        
        return "\n".join(lines)
    
    def reload_plugin(self, plugin_name: str) -> str:
        """
        Manually reload a specific plugin.
        
        Args:
            plugin_name: Name of plugin to reload
        
        Returns:
            Success or error message
        """
        success = self.loader.reload_plugin(plugin_name)
        if success:
            return f"✅ Reloaded plugin: {plugin_name}"
        else:
            return f"❌ Failed to reload plugin: {plugin_name}"
    
    def list_available(self) -> str:
        """List all available plugins (loaded and discoverable)."""
        discovered = self.loader.discover_plugins()
        loaded = set(self.loader.loaded_plugins.keys())
        
        lines = [
            "📦 Available Plugins",
            "─" * 40,
        ]
        
        if not discovered:
            lines.append("(no plugins found)")
            return "\n".join(lines)
        
        for plugin_name in sorted(discovered):
            status = "✅" if plugin_name in loaded else "⏸️"
            lines.append(f"{status} {plugin_name}")
        
        return "\n".join(lines)
    
    def get_tools(self) -> dict:
        """Get all available tools from loaded plugins."""
        return self.loader.get_tools()
    
    def get_plugin_info(self) -> dict:
        """Get information about all loaded plugins (delegates to loader)."""
        return self.loader.get_plugin_info()
