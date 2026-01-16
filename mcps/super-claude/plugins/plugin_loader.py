"""
Plugin Loader with Dynamic Reload

Discovers, loads, and manages Super Claude plugins with file watching.
"""

import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, Callable
from datetime import datetime
import logging

from plugin_base import SuperClaudePlugin

logger = logging.getLogger(__name__)


class PluginLoader:
    """Dynamically loads and manages Super Claude plugins."""
    
    def __init__(self, plugins_dir: Path):
        """
        Initialize the plugin loader.
        
        Args:
            plugins_dir: Path to directory containing plugins
        """
        self.plugins_dir = plugins_dir
        self.loaded_plugins: Dict[str, SuperClaudePlugin] = {}
        self.plugin_mtimes: Dict[str, float] = {}  # Track modification times
        self.all_tools: Dict[str, Callable] = {}
        self.plugin_registry: Dict[str, Dict[str, Any]] = {}  # Metadata registry
        
        # Ensure plugins dir exists
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Add plugins dir to Python path
        if str(self.plugins_dir) not in sys.path:
            sys.path.insert(0, str(self.plugins_dir))
    
    def discover_plugins(self) -> list[str]:
        """
        Discover available plugin modules (*.py files).
        
        Returns:
            List of plugin module names (without .py extension)
        """
        plugins = []
        for file in self.plugins_dir.glob("*.py"):
            # Skip private/special files
            if file.name.startswith("_"):
                continue
            if file.name in {"plugin_base.py", "plugin_loader.py", "plugin_manager.py"}:
                continue
            plugins.append(file.stem)
        return plugins
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a single plugin by name.
        
        Args:
            plugin_name: Name of plugin module (without .py)
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Import module
            if plugin_name in sys.modules:
                # Reload if already loaded
                module = importlib.reload(sys.modules[plugin_name])
            else:
                module = importlib.import_module(plugin_name)
            
            # Find plugin class (should be the first SuperClaudePlugin subclass)
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SuperClaudePlugin) and 
                    obj != SuperClaudePlugin):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error(f"❌ No SuperClaudePlugin subclass found in {plugin_name}")
                return False
            
            # Instantiate and initialize
            plugin_instance = plugin_class()
            plugin_instance.initialize()
            plugin_instance.on_load()
            
            # Register
            self.loaded_plugins[plugin_name] = plugin_instance
            self.plugin_registry[plugin_name] = plugin_instance.get_metadata()
            
            # Add tools to global registry
            for tool_name, tool_func in plugin_instance.get_tools().items():
                full_name = f"{plugin_name}:{tool_name}"
                self.all_tools[full_name] = tool_func
            
            # Track modification time
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            self.plugin_mtimes[plugin_name] = plugin_file.stat().st_mtime
            
            logger.info(f"✅ Loaded plugin: {plugin_name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to load plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and remove its tools.
        
        Args:
            plugin_name: Name of plugin to unload
        
        Returns:
            True if unloaded successfully
        """
        try:
            if plugin_name not in self.loaded_plugins:
                return False
            
            plugin = self.loaded_plugins[plugin_name]
            plugin.on_unload()
            
            # Remove tools from registry
            for tool_name in list(self.all_tools.keys()):
                if tool_name.startswith(f"{plugin_name}:"):
                    del self.all_tools[tool_name]
            
            # Remove plugin
            del self.loaded_plugins[plugin_name]
            del self.plugin_registry[plugin_name]
            if plugin_name in self.plugin_mtimes:
                del self.plugin_mtimes[plugin_name]
            
            logger.info(f"✅ Unloaded plugin: {plugin_name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin (unload then load).
        
        Args:
            plugin_name: Name of plugin to reload
        
        Returns:
            True if reloaded successfully
        """
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name)
    
    def load_all(self) -> Dict[str, bool]:
        """
        Load all discovered plugins.
        
        Returns:
            Dict of plugin_name -> success (bool)
        """
        results = {}
        for plugin_name in self.discover_plugins():
            results[plugin_name] = self.load_plugin(plugin_name)
        return results
    
    def check_for_changes(self) -> list[str]:
        """
        Check if any loaded plugins have been modified.
        
        Returns:
            List of plugin names that have changed
        """
        changed = []
        for plugin_name in list(self.loaded_plugins.keys()):
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            if not plugin_file.exists():
                changed.append(plugin_name)
                continue
            
            current_mtime = plugin_file.stat().st_mtime
            if current_mtime != self.plugin_mtimes.get(plugin_name):
                changed.append(plugin_name)
        
        # Also check for new plugins
        for plugin_name in self.discover_plugins():
            if plugin_name not in self.loaded_plugins:
                changed.append(plugin_name)
        
        return changed
    
    def get_tools(self) -> Dict[str, Callable]:
        """Get all registered tools from all plugins."""
        return self.all_tools.copy()
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all loaded plugins."""
        info = {
            "loaded_at": datetime.now().isoformat(),
            "plugin_count": len(self.loaded_plugins),
            "tool_count": len(self.all_tools),
            "plugins": {}
        }
        
        for plugin_name, metadata in self.plugin_registry.items():
            tool_count = sum(1 for t in self.all_tools.keys() 
                           if t.startswith(f"{plugin_name}:"))
            info["plugins"][plugin_name] = {
                **metadata,
                "tool_count": tool_count,
                "tools": [t.split(":", 1)[1] for t in self.all_tools.keys() 
                         if t.startswith(f"{plugin_name}:")]
            }
        
        return info
