"""
Dynamic Plugin Loader for Super Claude

Enables hot-loading/unloading of plugins at runtime without server restart.
Uses FastMCP's native add_tool/remove_tool capabilities.

Usage:
    from dynamic_loader import DynamicPluginLoader
    
    loader = DynamicPluginLoader(mcp, plugins_dir)
    loader.load_plugin("supernote")       # Load a plugin
    loader.reload_plugin("supernote")     # Hot-reload
    loader.unload_plugin("supernote")     # Remove all tools
    loader.load_all()                     # Load all discovered plugins
"""

import sys
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Set
from datetime import datetime

from fastmcp import FastMCP
from fastmcp.tools import Tool

from plugin_base import SuperClaudePlugin

logger = logging.getLogger(__name__)


class DynamicPluginLoader:
    """
    Manages plugins with true runtime add/remove of MCP tools.
    
    Unlike the static loader, this:
    - Adds tools to a running MCP server
    - Removes tools when plugins unload
    - Tracks which tools belong to which plugin
    - Sends list_changed notifications to connected clients
    """
    
    def __init__(self, mcp: FastMCP, plugins_dir: Path):
        """
        Initialize the dynamic loader.
        
        Args:
            mcp: The FastMCP server instance
            plugins_dir: Path to plugins directory
        """
        self.mcp = mcp
        self.plugins_dir = plugins_dir
        
        # Track loaded plugins and their state
        self.plugins: Dict[str, SuperClaudePlugin] = {}
        self.plugin_tools: Dict[str, Set[str]] = {}  # plugin_name -> set of tool names
        self.plugin_mtimes: Dict[str, float] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Ensure plugins dir is in path
        if str(plugins_dir) not in sys.path:
            sys.path.insert(0, str(plugins_dir))
    
    def discover_plugins(self) -> list[str]:
        """
        Discover available plugin modules.
        
        Returns:
            List of plugin module names
        """
        skip_files = {
            "plugin_base.py", 
            "plugin_loader.py", 
            "plugin_manager.py",
            "dynamic_loader.py",
            "__init__.py"
        }
        
        plugins = []
        for file in self.plugins_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            if file.name in skip_files:
                continue
            plugins.append(file.stem)
        
        return sorted(plugins)
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin and register its tools with MCP.
        
        Args:
            plugin_name: Name of plugin module
            
        Returns:
            True if loaded successfully
        """
        try:
            # Unload first if already loaded
            if plugin_name in self.plugins:
                self.unload_plugin(plugin_name)
            
            # Import/reload module
            if plugin_name in sys.modules:
                module = importlib.reload(sys.modules[plugin_name])
            else:
                module = importlib.import_module(plugin_name)
            
            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SuperClaudePlugin) and 
                    obj != SuperClaudePlugin):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error(f"No SuperClaudePlugin subclass in {plugin_name}")
                return False
            
            # Instantiate and initialize
            plugin = plugin_class()
            plugin.initialize()
            plugin.on_load()
            
            # Register tools with MCP
            registered_tools = set()
            for tool_name, tool_func in plugin.get_tools().items():
                # Use tool name as-is - plugins are responsible for their own namespacing
                # Get description from docstring
                description = tool_func.__doc__ or f"{tool_name} from {plugin_name}"
                
                # Create Tool and add to MCP
                tool = Tool.from_function(
                    fn=tool_func,
                    name=tool_name,
                    description=description.strip().split('\n')[0]  # First line of docstring
                )
                
                self.mcp.add_tool(tool)
                registered_tools.add(tool_name)
                logger.debug(f"  Registered tool: {tool_name}")
            
            # Track state
            self.plugins[plugin_name] = plugin
            self.plugin_tools[plugin_name] = registered_tools
            self.plugin_metadata[plugin_name] = plugin.get_metadata()
            
            # Track file modification time
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            if plugin_file.exists():
                self.plugin_mtimes[plugin_name] = plugin_file.stat().st_mtime
            
            tool_count = len(registered_tools)
            logger.info(f"✅ Loaded plugin: {plugin_name} ({tool_count} tools)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and remove its tools from MCP.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if unloaded successfully
        """
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin not loaded: {plugin_name}")
                return False
            
            # Call plugin's cleanup
            plugin = self.plugins[plugin_name]
            try:
                plugin.on_unload()
            except Exception as e:
                logger.warning(f"Plugin {plugin_name} on_unload error: {e}")
            
            # Remove all tools from MCP
            tool_names = self.plugin_tools.get(plugin_name, set())
            for tool_name in tool_names:
                try:
                    self.mcp.remove_tool(tool_name)
                    logger.debug(f"  Removed tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"  Failed to remove tool {tool_name}: {e}")
            
            # Clean up tracking
            del self.plugins[plugin_name]
            del self.plugin_tools[plugin_name]
            if plugin_name in self.plugin_metadata:
                del self.plugin_metadata[plugin_name]
            if plugin_name in self.plugin_mtimes:
                del self.plugin_mtimes[plugin_name]
            
            logger.info(f"✅ Unloaded plugin: {plugin_name} ({len(tool_names)} tools removed)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Hot-reload a plugin (unload + load).
        
        Args:
            plugin_name: Name of plugin to reload
            
        Returns:
            True if reloaded successfully
        """
        logger.info(f"🔄 Reloading plugin: {plugin_name}")
        return self.load_plugin(plugin_name)  # load_plugin handles unload
    
    def load_all(self) -> Dict[str, bool]:
        """
        Load all discovered plugins.
        
        Returns:
            Dict of plugin_name -> success
        """
        results = {}
        for plugin_name in self.discover_plugins():
            results[plugin_name] = self.load_plugin(plugin_name)
        return results
    
    def unload_all(self) -> None:
        """Unload all plugins."""
        for plugin_name in list(self.plugins.keys()):
            self.unload_plugin(plugin_name)
    
    def check_for_changes(self) -> list[str]:
        """
        Check which plugins have changed on disk.
        
        Returns:
            List of plugin names that have changed
        """
        changed = []
        
        # Check loaded plugins for modifications
        for plugin_name, old_mtime in list(self.plugin_mtimes.items()):
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            if not plugin_file.exists():
                changed.append(plugin_name)  # Deleted
                continue
            
            current_mtime = plugin_file.stat().st_mtime
            if current_mtime != old_mtime:
                changed.append(plugin_name)
        
        # Check for new plugins
        for plugin_name in self.discover_plugins():
            if plugin_name not in self.plugins:
                changed.append(plugin_name)
        
        return changed
    
    def reload_changed(self) -> str:
        """
        Reload any plugins that have changed.
        
        Returns:
            Status message
        """
        changed = self.check_for_changes()
        if not changed:
            return "No plugin changes detected"
        
        results = []
        for plugin_name in changed:
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            
            if not plugin_file.exists():
                # Plugin file deleted
                if plugin_name in self.plugins:
                    self.unload_plugin(plugin_name)
                    results.append(f"🗑️ {plugin_name}: unloaded (file deleted)")
            elif plugin_name in self.plugins:
                # Existing plugin modified
                if self.reload_plugin(plugin_name):
                    results.append(f"🔄 {plugin_name}: reloaded")
                else:
                    results.append(f"❌ {plugin_name}: reload failed")
            else:
                # New plugin
                if self.load_plugin(plugin_name):
                    results.append(f"✨ {plugin_name}: loaded (new)")
                else:
                    results.append(f"❌ {plugin_name}: load failed")
        
        return "\n".join(results)
    
    def get_status(self) -> str:
        """
        Get detailed status of all plugins and tools.
        
        Returns:
            Formatted status string
        """
        lines = ["🔌 Dynamic Plugin Status", "─" * 40]
        
        if not self.plugins:
            lines.append("No plugins loaded")
            return "\n".join(lines)
        
        total_tools = 0
        for plugin_name, plugin in sorted(self.plugins.items()):
            metadata = self.plugin_metadata.get(plugin_name, {})
            version = metadata.get('version', '?')
            description = metadata.get('description', '')
            tools = self.plugin_tools.get(plugin_name, set())
            total_tools += len(tools)
            
            lines.append(f"\n**{plugin_name}** v{version}")
            if description:
                lines.append(f"  {description}")
            lines.append(f"  Tools ({len(tools)}):")
            for tool_name in sorted(tools):
                lines.append(f"    • {tool_name}")
        
        lines.append("")
        lines.append(f"Total: {len(self.plugins)} plugins, {total_tools} tools")
        
        return "\n".join(lines)
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """
        Get plugin info as structured data.
        
        Returns:
            Dict with plugin information
        """
        return {
            "loaded_at": datetime.now().isoformat(),
            "plugin_count": len(self.plugins),
            "tool_count": sum(len(t) for t in self.plugin_tools.values()),
            "plugins": {
                name: {
                    **self.plugin_metadata.get(name, {}),
                    "tools": sorted(self.plugin_tools.get(name, set()))
                }
                for name in self.plugins
            }
        }
