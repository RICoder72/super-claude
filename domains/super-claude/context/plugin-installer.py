"""
External Plugin Installer for Super Claude

Handles installation, updates, and removal of plugins from Git repositories.
Add these tools to server.py or integrate into plugin_manager.py.
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# External plugins install here (persistent across container rebuilds)
EXTERNAL_PLUGINS_DIR = Path("/data/plugins")


def _run_git(args: list, cwd: Path = None) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _run_pip(args: list) -> tuple[bool, str]:
    """Run a pip command and return (success, output)."""
    try:
        result = subprocess.run(
            ["pip"] + args + ["--break-system-packages"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _validate_plugin(plugin_dir: Path) -> tuple[bool, str, Optional[dict]]:
    """Validate a plugin directory has required files."""
    manifest_path = plugin_dir / "plugin.json"
    
    if not manifest_path.exists():
        return False, "Missing plugin.json", None
    
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return False, f"Invalid plugin.json: {e}", None
    
    # Check required fields
    required = ["name", "version", "entry_point", "class_name"]
    missing = [f for f in required if f not in manifest]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}", None
    
    # Check entry point exists
    entry_point = plugin_dir / manifest["entry_point"]
    if not entry_point.exists():
        return False, f"Entry point not found: {manifest['entry_point']}", None
    
    return True, "Valid", manifest


def _install_dependencies(manifest: dict) -> tuple[bool, str]:
    """Install Python dependencies from plugin manifest."""
    requires = manifest.get("requires", {})
    python_deps = requires.get("python", [])
    
    if not python_deps:
        return True, "No dependencies"
    
    success, output = _run_pip(["install"] + python_deps)
    if success:
        return True, f"Installed: {', '.join(python_deps)}"
    return False, f"Dependency install failed: {output}"


async def plugin_install(url: str, branch: str = "main") -> str:
    """
    Install a plugin from a Git repository.
    
    Args:
        url: Git repository URL (HTTPS)
        branch: Branch to clone (default: "main")
    
    Returns:
        Installation status message
    
    Example:
        plugin_install("https://github.com/user/super-claude-plugin-supernote")
    """
    # Ensure plugins directory exists
    EXTERNAL_PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Extract plugin name from URL
    # https://github.com/user/super-claude-plugin-supernote -> supernote
    repo_name = url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    # Handle super-claude-plugin-{name} convention
    if repo_name.startswith("super-claude-plugin-"):
        plugin_name = repo_name[20:]  # Remove prefix
    else:
        plugin_name = repo_name
    
    plugin_dir = EXTERNAL_PLUGINS_DIR / plugin_name
    
    # Check if already installed
    if plugin_dir.exists():
        return f"❌ Plugin '{plugin_name}' already installed. Use plugin_update to upgrade."
    
    # Clone repository
    success, output = _run_git(["clone", "--branch", branch, "--depth", "1", url, str(plugin_dir)])
    if not success:
        return f"❌ Clone failed: {output}"
    
    # Validate plugin structure
    valid, message, manifest = _validate_plugin(plugin_dir)
    if not valid:
        # Clean up failed install
        shutil.rmtree(plugin_dir, ignore_errors=True)
        return f"❌ Invalid plugin: {message}"
    
    # Install Python dependencies
    dep_success, dep_message = _install_dependencies(manifest)
    if not dep_success:
        shutil.rmtree(plugin_dir, ignore_errors=True)
        return f"❌ {dep_message}"
    
    # Create symlink to /app/plugins for the loader to find it
    # The plugin loader scans /app/plugins, so we symlink there
    app_plugin_link = Path("/app/plugins") / f"{plugin_name}.py"
    entry_point = plugin_dir / manifest["entry_point"]
    
    try:
        if app_plugin_link.exists():
            app_plugin_link.unlink()
        app_plugin_link.symlink_to(entry_point)
    except Exception as e:
        logger.warning(f"Could not create symlink: {e}")
    
    # Trigger plugin reload
    try:
        import server
        if hasattr(server, 'plugin_manager'):
            server.plugin_manager.load_plugin(plugin_name, str(entry_point))
    except Exception as e:
        logger.warning(f"Auto-load failed: {e}. Restart may be required.")
    
    return f"""✅ Installed plugin: {manifest['name']} v{manifest['version']}

**Description:** {manifest.get('description', 'No description')}
**Author:** {manifest.get('author', 'Unknown')}
**Dependencies:** {dep_message}

Plugin loaded. Use `plugin_status` to see available tools."""


async def plugin_uninstall(name: str) -> str:
    """
    Remove an installed external plugin.
    
    Args:
        name: Plugin name
    
    Returns:
        Uninstallation status message
    """
    plugin_dir = EXTERNAL_PLUGINS_DIR / name
    
    if not plugin_dir.exists():
        return f"❌ Plugin '{name}' not found in external plugins"
    
    # Remove symlink from /app/plugins
    app_plugin_link = Path("/app/plugins") / f"{name}.py"
    if app_plugin_link.is_symlink():
        app_plugin_link.unlink()
    
    # Unload from plugin manager
    try:
        import server
        if hasattr(server, 'plugin_manager'):
            server.plugin_manager.unload_plugin(name)
    except Exception as e:
        logger.warning(f"Unload failed: {e}")
    
    # Remove plugin directory
    try:
        shutil.rmtree(plugin_dir)
    except Exception as e:
        return f"❌ Failed to remove plugin directory: {e}"
    
    return f"✅ Uninstalled plugin: {name}"


async def plugin_update(name: str = "all") -> str:
    """
    Update an external plugin to the latest version.
    
    Args:
        name: Plugin name, or "all" to update all external plugins
    
    Returns:
        Update status message
    """
    if name == "all":
        # Update all external plugins
        if not EXTERNAL_PLUGINS_DIR.exists():
            return "📂 No external plugins installed"
        
        plugins = [d for d in EXTERNAL_PLUGINS_DIR.iterdir() if d.is_dir() and (d / "plugin.json").exists()]
        
        if not plugins:
            return "📂 No external plugins installed"
        
        results = []
        for plugin_dir in plugins:
            plugin_name = plugin_dir.name
            result = await _update_single_plugin(plugin_dir)
            results.append(f"**{plugin_name}:** {result}")
        
        return "Plugin Update Results:\n\n" + "\n".join(results)
    else:
        plugin_dir = EXTERNAL_PLUGINS_DIR / name
        if not plugin_dir.exists():
            return f"❌ Plugin '{name}' not found"
        
        return await _update_single_plugin(plugin_dir)


async def _update_single_plugin(plugin_dir: Path) -> str:
    """Update a single plugin directory."""
    plugin_name = plugin_dir.name
    
    # Get current version
    valid, _, old_manifest = _validate_plugin(plugin_dir)
    old_version = old_manifest.get("version", "unknown") if old_manifest else "unknown"
    
    # Git pull
    success, output = _run_git(["pull", "--ff-only"], cwd=plugin_dir)
    if not success:
        return f"❌ Git pull failed: {output}"
    
    # Re-validate
    valid, message, new_manifest = _validate_plugin(plugin_dir)
    if not valid:
        return f"❌ Plugin invalid after update: {message}"
    
    new_version = new_manifest.get("version", "unknown")
    
    # Reinstall dependencies (in case they changed)
    _install_dependencies(new_manifest)
    
    # Reload plugin
    try:
        import server
        if hasattr(server, 'plugin_manager'):
            server.plugin_manager.reload_plugin(plugin_name)
    except Exception as e:
        return f"⚠️ Updated {old_version} → {new_version}, but reload failed: {e}"
    
    if old_version == new_version:
        return f"✅ Already at latest ({new_version})"
    
    return f"✅ Updated {old_version} → {new_version}"


async def plugin_list_external() -> str:
    """
    List all installed external plugins.
    
    Returns:
        List of external plugins with versions and status
    """
    if not EXTERNAL_PLUGINS_DIR.exists():
        return "📂 No external plugins directory"
    
    plugins = [d for d in EXTERNAL_PLUGINS_DIR.iterdir() if d.is_dir()]
    
    if not plugins:
        return "📂 No external plugins installed"
    
    lines = ["🔌 External Plugins", "─" * 40]
    
    for plugin_dir in sorted(plugins):
        valid, message, manifest = _validate_plugin(plugin_dir)
        
        if valid:
            name = manifest["name"]
            version = manifest["version"]
            desc = manifest.get("description", "")[:50]
            lines.append(f"✅ **{name}** v{version}")
            if desc:
                lines.append(f"   {desc}")
        else:
            lines.append(f"❌ **{plugin_dir.name}** - {message}")
    
    lines.append("")
    lines.append(f"Install location: {EXTERNAL_PLUGINS_DIR}")
    
    return "\n".join(lines)


# Tool registration dict for adding to server.py
INSTALLER_TOOLS = {
    "plugin_install": plugin_install,
    "plugin_uninstall": plugin_uninstall,
    "plugin_update": plugin_update,
    "plugin_list_external": plugin_list_external,
}
