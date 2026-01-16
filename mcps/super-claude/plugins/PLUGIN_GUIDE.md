# Plugin Developer Guide

## Overview

Super Claude uses a pluggable architecture for MCP tools. This allows you to:
- Add new capabilities without modifying core server code
- Share plugins with others
- Dynamically reload plugins without restarting the server

## Creating a New Plugin

### Step 1: Extend SuperClaudePlugin

Create a new file in `plugins/` with your plugin code:

```python
from plugin_base import SuperClaudePlugin

class MyPlugin(SuperClaudePlugin):
    def initialize(self):
        """Called once when plugin loads."""
        self.metadata = {
            "name": "myplugin",
            "version": "0.1.0",
            "description": "What this plugin does",
            "author": "Your Name",
            "requires": ["any external dependencies"]
        }
        
        # Register your tools
        self.tools = {
            "my_tool": self.my_tool,
            "another_tool": self.another_tool,
        }
    
    async def my_tool(self, param: str) -> str:
        """Your tool function."""
        return f"✅ Done with {param}"
    
    async def another_tool(self) -> str:
        """Another tool."""
        return "✅ Another result"
    
    def on_load(self):
        """Called when plugin loads. Override for setup."""
        pass
    
    def on_unload(self):
        """Called when plugin unloads. Override for cleanup."""
        pass
```

### Step 2: Save and Reload

Save your plugin to `plugins/myplugin.py`, then reload:

```
plugin_reload_changed  # Automatically finds and loads new plugins
```

Or manually reload a specific plugin:

```
plugin_reload("myplugin")
```

## Plugin Architecture Details

### Plugin Loader
- Scans `plugins/` directory for `*.py` files
- Imports and instantiates `SuperClaudePlugin` subclasses
- Registers tools in a global registry
- Tracks file modification times for hot reload
- Tools accessible via: `{plugin_name}:{tool_name}`

### Tool Registration
When your plugin loads, its tools are registered as:
- `myplugin:my_tool`
- `myplugin:another_tool`

This namespace prevents conflicts between plugins.

### Dynamic Reloading
The `plugin_reload_changed()` tool:
1. Checks modification time of each plugin file
2. Reloads any plugins that have changed
3. Loads any newly discovered plugins
4. Returns a summary of changes

No server restart needed.

## Best Practices

### 1. Keep Tools Focused
One tool per function. Good:
```python
self.tools = {
    "auth_get": self.auth_get,
    "auth_set": self.auth_set,
}
```

### 2. Use Async for I/O
If your tool makes network calls or disk I/O, use `async`:
```python
async def fetch_data(self, url: str) -> str:
    # Use aiohttp, etc.
    return result
```

### 3. Return Readable Output
Tools should return formatted strings for Claude:
```python
return "✅ Success: did the thing\n📎 Details: ..."
return "❌ Error: why it failed"
```

### 4. Error Handling
Wrap external calls in try/except:
```python
try:
    result = expensive_operation()
    return f"✅ {result}"
except Exception as e:
    return f"❌ Failed: {e}"
```

### 5. Store Config in State
Use `context_update()` to persist plugin config:
```python
# In your plugin
super_claude_root = Path("/data")
config_file = super_claude_root / "config" / "myplugin.json"
```

## Example: Simple HTTP Plugin

```python
from plugin_base import SuperClaudePlugin
import aiohttp

class HTTPPlugin(SuperClaudePlugin):
    def initialize(self):
        self.metadata = {
            "name": "http",
            "version": "0.1.0",
            "description": "HTTP request tool",
        }
        self.tools = {
            "http_get": self.http_get,
        }
    
    async def http_get(self, url: str) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    text = await resp.text()
                    return f"✅ Status {resp.status}\n\n{text[:500]}"
        except Exception as e:
            return f"❌ Request failed: {e}"
```

## File Structure

```
plugins/
├── plugin_base.py          # Base class (don't edit)
├── plugin_loader.py        # Loader system (don't edit)
├── plugin_manager.py       # Manager (don't edit)
├── onepassword.py          # 1Password plugin
├── supernote.py            # Supernote plugin
├── myplugin.py             # Your new plugin
└── __init__.py
```

## Testing Your Plugin

1. Create your plugin file
2. Run `plugin_reload_changed()`
3. Run `plugin_status()` to see it loaded
4. Test your tools via Claude

If there's an error, check server logs:
```
docker logs super-claude | grep "myplugin"
```

## Debugging

### Plugin Won't Load
- Check syntax: `python -m py_compile plugins/myplugin.py`
- Check class name and inheritance
- Look for import errors in logs

### Tool Not Showing Up
- Verify it's in `self.tools` dict
- Check `plugin_status()` shows correct tool count
- Restart if file permissions issue

### Hot Reload Not Working
- File must be saved to disk first
- Run `plugin_reload_changed()` manually
- Or wait a few seconds for automatic detection

## Open Source Guidelines

When sharing a plugin:

1. **License**: Include LICENSE file (recommend PolyForm Noncommercial)
2. **README.md**: Document what it does, how to use it
3. **Dependencies**: List in `metadata["requires"]`
4. **Error Handling**: Return helpful error messages
5. **No Hardcoded Secrets**: Use 1Password or environment variables

Example shared plugin structure:
```
my-super-claude-plugin/
├── README.md
├── LICENSE
├── myplugin.py
└── requirements.txt
```

## Advanced: Shared Code

For common functionality across plugins, create shared modules:

```python
# plugins/_shared.py
def format_result(data):
    return f"✅ {data}"

# plugins/myplugin.py
from _shared import format_result

class MyPlugin(SuperClaudePlugin):
    async def my_tool(self):
        return format_result("done")
```

---

Questions? Ask in your next Super Claude session!
