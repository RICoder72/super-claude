# Super Claude Plugin Specification v1.0

## Overview

Super Claude plugins are self-contained Python modules distributed as Git repositories. This spec defines the structure, metadata, and installation process for external plugins.

## Repository Structure

```
super-claude-plugin-{name}/
├── plugin.json          # Required: Plugin metadata
├── {name}.py            # Required: Main plugin file
├── requirements.txt     # Optional: Python dependencies
├── README.md            # Recommended: Documentation
└── LICENSE              # Recommended: License file
```

## plugin.json Schema

```json
{
  "name": "supernote",
  "version": "0.11.0",
  "description": "Sync domains with Supernote via cloud storage",
  "author": "Matthew",
  "license": "MIT",
  "entry_point": "supernote.py",
  "class_name": "SupernotePlugin",
  "requires": {
    "python": ["reportlab", "pymupdf"],
    "system": ["supernote-tool"]
  },
  "super_claude_version": ">=1.0.0",
  "homepage": "https://github.com/user/super-claude-plugin-supernote",
  "keywords": ["supernote", "notes", "sync", "handwriting"]
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Plugin identifier (lowercase, no spaces) |
| `version` | string | Semantic version (X.Y.Z) |
| `description` | string | Brief description |
| `entry_point` | string | Main Python file |
| `class_name` | string | Plugin class name (must extend SuperClaudePlugin) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Plugin author |
| `license` | string | License identifier |
| `requires.python` | array | Python packages to pip install |
| `requires.system` | array | System dependencies (informational) |
| `super_claude_version` | string | Compatible Super Claude version |
| `homepage` | string | Project URL |
| `keywords` | array | Search keywords |

## Plugin Class Requirements

Plugins must extend `SuperClaudePlugin` and implement:

```python
from plugin_base import SuperClaudePlugin

class MyPlugin(SuperClaudePlugin):
    def initialize(self) -> None:
        """Set up metadata and register tools."""
        self.metadata = {
            "name": "myplugin",
            "version": "1.0.0",
            "description": "What it does",
            "author": "Author",
            "requires": []
        }
        
        self.tools = {
            "tool_name": self.tool_method,
        }
    
    async def tool_method(self, param: str) -> str:
        """Tool implementation."""
        return "result"
    
    def on_load(self) -> None:
        """Called when plugin loads (optional)."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin unloads (optional)."""
        pass
```

## Installation Locations

```
/app/plugins/                    # Built-in plugins (in container)
/data/plugins/                   # External plugins (persistent)
/data/plugins/{name}/            # Each installed plugin
/data/plugins/{name}/plugin.json
/data/plugins/{name}/{name}.py
```

## Installation Process

1. **Clone** repository to `/data/plugins/{name}/`
2. **Validate** plugin.json exists and is valid
3. **Install** Python dependencies via pip
4. **Register** plugin with plugin loader
5. **Load** plugin and verify tools register

## Plugin Management Tools

### plugin_install

```
plugin_install(url, branch="main")
```

Install a plugin from a Git repository URL.

**Parameters:**
- `url`: Git repository URL (HTTPS)
- `branch`: Branch to clone (default: "main")

**Example:**
```
plugin_install("https://github.com/user/super-claude-plugin-supernote")
```

### plugin_uninstall

```
plugin_uninstall(name)
```

Remove an installed plugin.

**Parameters:**
- `name`: Plugin name

### plugin_update

```
plugin_update(name)
```

Update a plugin to the latest version (git pull + reload).

**Parameters:**
- `name`: Plugin name, or "all" to update all external plugins

### plugin_list_available

```
plugin_list_available()
```

List installed external plugins with their versions and update status.

## Security Considerations

1. **Code Review**: Plugins execute arbitrary Python code. Only install from trusted sources.
2. **Sandboxing**: Plugins run in the same context as Super Claude - no isolation.
3. **Dependencies**: Plugin dependencies are installed globally in the container.
4. **Network**: Plugins have the same network access as Super Claude.

## Versioning

Plugins should follow semantic versioning:
- **MAJOR**: Breaking changes to tool signatures or behavior
- **MINOR**: New tools or features, backward compatible
- **PATCH**: Bug fixes, no API changes

## Example: Minimal Plugin

**plugin.json:**
```json
{
  "name": "hello",
  "version": "1.0.0",
  "description": "A simple hello world plugin",
  "entry_point": "hello.py",
  "class_name": "HelloPlugin"
}
```

**hello.py:**
```python
from plugin_base import SuperClaudePlugin

class HelloPlugin(SuperClaudePlugin):
    def initialize(self) -> None:
        self.metadata = {
            "name": "hello",
            "version": "1.0.0",
            "description": "A simple hello world plugin",
            "author": "Anonymous",
            "requires": []
        }
        self.tools = {
            "hello_world": self.hello_world,
        }
    
    async def hello_world(self, name: str = "World") -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"
```
