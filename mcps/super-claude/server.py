"""
Super Claude MCP Server with Plugin Architecture

Central MCP with plugin support providing:
- Core tools: Session, Filesystem, Shell, Docker, Context, Publish, Ops, Token
- Dynamic plugins: Auth (1Password), Supernote, and more
"""

from fastmcp import FastMCP
import subprocess
import json
from pathlib import Path
from datetime import datetime
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add plugins to path for imports
SUPER_CLAUDE_ROOT = Path("/data")
PLUGINS_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "plugins"
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

# Import plugin system
try:
    from plugin_loader import PluginLoader
    from plugin_manager import PluginManager
    PLUGINS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Plugin system unavailable: {e}")
    PLUGINS_AVAILABLE = False

# Also import 1Password helper for backward compatibility
sys.path.insert(0, "/app/shared")
try:
    from op_client import get_secret, get_secret_by_ref, create_item
except ImportError:
    logger.warning("1Password client unavailable")
    get_secret = get_secret_by_ref = create_item = None

# Initialize FastMCP
mcp = FastMCP("Super Claude")

# Initialize plugin system
if PLUGINS_AVAILABLE:
    plugin_loader = PluginLoader(PLUGINS_DIR)
    plugin_manager = PluginManager(plugin_loader)
    
    # Load all plugins at startup
    results = plugin_loader.load_all()
    for plugin_name, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} Plugin {plugin_name}: {'loaded' if success else 'failed'}")


# =============================================================================
# STORAGE SYSTEM INITIALIZATION
# =============================================================================
CORE_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "core"
PROVIDERS_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "providers"
STORAGE_CONFIG = SUPER_CLAUDE_ROOT / "config" / "storage_accounts.json"

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))
if str(PROVIDERS_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDERS_DIR))

try:
    from storage_manager import StorageManager
    from providers.gdrive import GoogleDriveProvider
    # supernote handled via plugin, not provider
    storage_manager = StorageManager(STORAGE_CONFIG)
    storage_manager.register_provider_type("gdrive", GoogleDriveProvider)
    STORAGE_AVAILABLE = True
    logger.info("Storage system initialized")
except ImportError as e:
    logger.warning(f"Storage system unavailable: {e}")
    storage_manager = None
    STORAGE_AVAILABLE = False

# =============================================================================
# CONFIG
# =============================================================================
SUPER_CLAUDE_ROOT = Path("/data")
DOCKER_NETWORK = "super-claude_super-claude-net"
OUTPUTS_DIR = SUPER_CLAUDE_ROOT / "outputs"
PUBLIC_BASE_URL = "https://zanni.synology.me/super-claude-output"

def _load_domain_config() -> dict:
    """Load domain triggers and descriptions from config file."""
    config_file = SUPER_CLAUDE_ROOT / "config" / "domain_triggers.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except Exception:
            pass
    return {}

DOMAIN_CONFIG = _load_domain_config()

DOMAIN_KEYWORDS = {
    domain: config.get("triggers", []) 
    for domain, config in DOMAIN_CONFIG.items()
}

# =============================================================================
# HELPERS
# =============================================================================
def _run_command(command: str, timeout: int = 30) -> tuple[bool, str]:
    """Run shell command, return (success, output)"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SUPER_CLAUDE_ROOT)
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr] {result.stderr}"
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, f"Error: {e}"

def _get_domain_path(domain: str) -> Path:
    """Get path for a domain"""
    return SUPER_CLAUDE_ROOT / "domains" / domain

def _check_token_expiry() -> str | None:
    """Check if token is expiring soon. Returns warning message or None."""
    try:
        state_file = SUPER_CLAUDE_ROOT / "domains" / "super-claude" / "state.json"
        if not state_file.exists():
            return None
        
        state = json.loads(state_file.read_text())
        auth = state.get("auth", {})
        token_info = auth.get("token", {})
        
        expires_at = token_info.get("expiresAt")
        if not expires_at:
            return None
        
        exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        now = datetime.now(exp_date.tzinfo) if exp_date.tzinfo else datetime.now()
        days_until = (exp_date - now).days
        
        warn_days = token_info.get("warnDaysBefore", 14)
        
        if days_until < 0:
            return f"🚨 TOKEN EXPIRED {abs(days_until)} days ago! Generate a new token immediately."
        elif days_until <= warn_days:
            return f"⚠️ Token expires in {days_until} days ({expires_at[:10]}). Consider generating a new token."
        
        return None
    except Exception:
        return None

def _detect_domain(text: str) -> str | None:
    """Detect domain from text based on keywords. Returns domain name or None."""
    text_lower = text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return domain
    return None

def _get_available_domains() -> list[dict]:
    """Get list of available domains with their descriptions."""
    domains_dir = SUPER_CLAUDE_ROOT / "domains"
    if not domains_dir.exists():
        return []
    
    domains = []
    for item in sorted(domains_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            config = DOMAIN_CONFIG.get(item.name, {})
            description = config.get("description", "")
            keywords = config.get("triggers", [])
            
            domains.append({
                "name": item.name,
                "description": description,
                "has_context": (item / "context").exists(),
                "keywords": keywords
            })
    
    return domains

def _shell_exec_impl(command: str, timeout: int = 30) -> str:
    """Shell execution implementation - use this from other tools."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SUPER_CLAUDE_ROOT)
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"❌ Command timed out after {timeout}s"
    except Exception as e:
        return f"❌ Error: {e}"

def _context_load_impl(domain: str) -> str:
    """Context loading implementation - use this from other tools."""
    domain_path = _get_domain_path(domain)
    context_file = domain_path / f"{domain}.md"
    
    if not domain_path.exists():
        return f"❌ Domain '{domain}' does not exist"
    if not context_file.exists():
        return f"❌ Context file not found: {domain}.md"
    
    try:
        file_content = context_file.read_text()
        state_file = domain_path / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                state["lastSession"] = datetime.now().isoformat()[:10]
                state_file.write_text(json.dumps(state, indent=2))
            except:
                pass
        
        config = DOMAIN_CONFIG.get(domain, {})
        triggers = config.get("triggers", [])
        trigger_note = ""
        if not triggers:
            trigger_note = f"\n\n💡 **Note:** This domain has no auto-detection triggers. Want to add some keywords so I can recognize when we're discussing {domain}?"
        
        return f"📖 Loaded domain: {domain}\n\n{file_content}{trigger_note}"
    except Exception as e:
        return f"❌ Error loading context: {e}"

# =============================================================================
# CORE SESSION TOOLS
# =============================================================================
@mcp.tool()
def session_start(user_message: str = "") -> str:
    """
    Initialize a Super Claude session with plugin and domain detection.
    """
    lines = ["🚀 Super Claude Session Started", "─" * 40, ""]
    
    # Plugin status
    if PLUGINS_AVAILABLE:
        info = plugin_manager.get_plugin_info()
        lines.append(f"🔌 Plugins: {info['plugin_count']} loaded ({info['tool_count']} tools)")
        lines.append("")
    
    # Token status
    token_warning = _check_token_expiry()
    if token_warning:
        lines.append(token_warning)
        lines.append("")
    
    # Available domains
    domains = _get_available_domains()
    if domains:
        lines.append("📚 Available Domains:")
        for d in domains:
            desc = f" - {d['description']}" if d['description'] else ""
            triggers = f" (triggers: {', '.join(d['keywords'][:3])})" if d['keywords'] else " ⚠️ no triggers"
            lines.append(f"   • {d['name']}{desc}{triggers}")
        lines.append("")
    
    # Auto-detect domain
    detected = None
    if user_message:
        detected = _detect_domain(user_message)
        if detected:
            lines.append(f"🎯 Auto-detected domain: {detected}")
            lines.append(f"   Loading context automatically...")
            lines.append("")
    
    if detected:
        domain_content = _context_load_impl(detected)
        lines.append(domain_content)
    else:
        lines.append("💡 No specific domain detected. Say 'let's work on [domain]' or ask about:")
        lines.append("   • Super Claude infrastructure, Docker, MCP, plugins")
        lines.append("   • Projects, tasks, backlog")
        lines.append("   • Or any registered domain")
    
    return "\n".join(lines)

@mcp.tool()
def ping() -> str:
    """Health check. Returns pong if Super Claude is running."""
    response = "pong from Super Claude 🚀"
    
    warning = _check_token_expiry()
    if warning:
        response += f"\n\n{warning}"
    
    if PLUGINS_AVAILABLE:
        info = plugin_manager.get_plugin_info()
        response += f"\n\n🔌 Plugins: {info['plugin_count']} loaded"
    
    return response

# =============================================================================
# TOKEN MANAGEMENT
# =============================================================================
@mcp.tool()
def token_status() -> str:
    """Check the status of the current authentication token."""
    try:
        state_file = SUPER_CLAUDE_ROOT / "domains" / "super-claude" / "state.json"
        if not state_file.exists():
            return "❌ State file not found"
        
        state = json.loads(state_file.read_text())
        auth = state.get("auth", {})
        
        if not auth.get("enabled"):
            return "🔓 Authentication is not enabled"
        
        token_info = auth.get("token", {})
        
        issued = token_info.get("issuedAt", "Unknown")
        expires = token_info.get("expiresAt", "Unknown")
        subject = token_info.get("subject", "Unknown")
        
        lines = [
            "🔐 Token Status",
            "─" * 30,
            f"Subject: {subject}",
            f"Issued:  {issued[:10] if issued != 'Unknown' else 'Unknown'}",
            f"Expires: {expires[:10] if expires != 'Unknown' else 'Unknown'}",
        ]
        
        if expires != "Unknown":
            try:
                exp_date = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                now = datetime.now(exp_date.tzinfo) if exp_date.tzinfo else datetime.now()
                days_until = (exp_date - now).days
                
                if days_until < 0:
                    lines.append(f"Status:  🚨 EXPIRED ({abs(days_until)} days ago)")
                elif days_until <= 14:
                    lines.append(f"Status:  ⚠️ Expiring soon ({days_until} days)")
                else:
                    lines.append(f"Status:  ✅ Valid ({days_until} days remaining)")
            except Exception:
                lines.append("Status:  ❓ Could not calculate")
        
        lines.append("")
        lines.append("To generate a new token:")
        lines.append("  node auth-service/jwt-utils.js generate claude-user 'read,write,admin' 180d")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error checking token status: {e}"

@mcp.tool()
def token_record(subject: str, issued_at: str, expires_at: str) -> str:
    """Record token information after generating a new token."""
    try:
        state_file = SUPER_CLAUDE_ROOT / "domains" / "super-claude" / "state.json"
        if not state_file.exists():
            return "❌ State file not found"
        
        state = json.loads(state_file.read_text())
        
        if "auth" not in state:
            state["auth"] = {"enabled": True}
        
        state["auth"]["token"] = {
            "subject": subject,
            "issuedAt": issued_at,
            "expiresAt": expires_at,
            "warnDaysBefore": 14
        }
        state["lastUpdated"] = datetime.now().isoformat()[:10]
        
        state_file.write_text(json.dumps(state, indent=2))
        
        return f"✅ Token info recorded\n   Subject: {subject}\n   Expires: {expires_at[:10]}"
    except Exception as e:
        return f"❌ Error recording token: {e}"

# =============================================================================
# CONTEXT SYSTEM
# =============================================================================
@mcp.tool()
def context_load(domain: str) -> str:
    """Load domain context for a specific area of work."""
    return _context_load_impl(domain)

@mcp.tool()
def context_get(domain: str, file: str) -> str:
    """Get specific context file from domain's context/ directory."""
    domain_path = _get_domain_path(domain)
    context_dir = domain_path / "context"
    target_file = context_dir / file
    
    if not domain_path.exists():
        return f"❌ Domain '{domain}' does not exist"
    if not context_dir.exists():
        return f"❌ Context directory not found for domain '{domain}'"
    if not target_file.exists():
        return f"❌ Context file not found: {file}"
    
    try:
        content = target_file.read_text()
        return f"📄 {domain}/context/{file}\n\n{content}"
    except Exception as e:
        return f"❌ Error reading context file: {e}"

@mcp.tool()
def context_update(domain: str, key: str, value: str) -> str:
    """Update domain state.json with key-value data."""
    domain_path = _get_domain_path(domain)
    state_file = domain_path / "state.json"
    
    if not domain_path.exists():
        return f"❌ Domain '{domain}' does not exist"
    
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            state = {}
    else:
        state = {"created": datetime.now().isoformat()[:10]}
    
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    state[key] = parsed_value
    state["lastUpdated"] = datetime.now().isoformat()[:10]
    
    try:
        state_file.write_text(json.dumps(state, indent=2))
        return f"✅ Updated {domain} state: {key} = {parsed_value}"
    except Exception as e:
        return f"❌ Error updating state: {e}"

@mcp.tool()
def context_list() -> str:
    """List all available domains and their status."""
    domains_dir = SUPER_CLAUDE_ROOT / "domains"
    if not domains_dir.exists():
        return "❌ Domains directory not found"
    
    domains = []
    for item in sorted(domains_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            has_md = (item / f"{item.name}.md").exists()
            
            status = "✅" if has_md else "⚠️"
            
            config = DOMAIN_CONFIG.get(item.name, {})
            description = config.get("description", "")
            keywords = config.get("triggers", [])
            
            desc_str = f" - {description}" if description else ""
            keywords_str = f" (triggers: {', '.join(keywords[:3])})" if keywords else " ⚠️ no triggers"
            
            domains.append(f"{status} {item.name}{desc_str}{keywords_str}")
    
    header = "📚 Available Domains\n" + "─" * 30
    listing = "\n".join(domains) if domains else "(no domains found)"
    return f"{header}\n{listing}"

# =============================================================================
# LEGACY AUTH TOOLS (For backward compatibility, use plugins in new code)
# =============================================================================
if get_secret:
    @mcp.tool()
    async def auth_get(item_name: str, field: str = "credential", vault: str = "Key Vault") -> str:
        """Get a secret from 1Password."""
        return await get_secret(item_name, field, vault)

    @mcp.tool()
    async def auth_get_ref(secret_ref: str) -> str:
        """Get a secret using a full 1Password secret reference."""
        return await get_secret_by_ref(secret_ref)

    @mcp.tool()
    async def auth_set(
        title: str,
        fields: str,
        vault: str = "Key Vault",
        category: str = "api_credential",
        notes: str = ""
    ) -> str:
        """Create a new item in 1Password."""
        try:
            import json as json_module
            fields_dict = json_module.loads(fields)
            return await create_item(title, fields_dict, vault, category, notes)
        except json_module.JSONDecodeError as e:
            return f"❌ Invalid JSON in fields: {e}"
        except Exception as e:
            return f"❌ Error creating item: {e}"

# =============================================================================
# FILESYSTEM TOOLS
# =============================================================================
def _validate_path(path: str) -> Path:
    """Ensure path is within sandbox. Returns resolved Path."""
    if path.startswith("/"):
        resolved = Path(path).resolve()
    else:
        resolved = (SUPER_CLAUDE_ROOT / path).resolve()
    
    if not str(resolved).startswith(str(SUPER_CLAUDE_ROOT)):
        raise ValueError(f"Path outside sandbox: {path}")
    return resolved

@mcp.tool()
def fs_list(path: str = ".") -> str:
    """List directory contents."""
    target = _validate_path(path)
    if not target.exists():
        return f"❌ Path does not exist: {path}"
    if not target.is_dir():
        return f"❌ Not a directory: {path}"
    
    items = []
    for item in sorted(target.iterdir()):
        if item.is_dir():
            items.append(f"📁 {item.name}/")
        else:
            size = item.stat().st_size
            items.append(f"📄 {item.name} ({size} bytes)")
    
    header = f"📂 {path}\n" + "─" * 40
    listing = "\n".join(items) if items else "(empty)"
    return f"{header}\n{listing}"

@mcp.tool()
def fs_read(path: str) -> str:
    """Read file contents."""
    target = _validate_path(path)
    if not target.exists():
        return f"❌ File does not exist: {path}"
    if not target.is_file():
        return f"❌ Not a file: {path}"
    
    try:
        return target.read_text()
    except UnicodeDecodeError:
        return f"❌ Cannot read binary file: {path}"

@mcp.tool()
def fs_write(path: str, content: str) -> str:
    """Write content to file. Creates parent directories if needed."""
    target = _validate_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"✅ Written: {path} ({len(content)} bytes)"

@mcp.tool()
def fs_append(path: str, content: str) -> str:
    """Append content to file. Creates file if it doesn't exist."""
    target = _validate_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a") as f:
        f.write(content)
    return f"✅ Appended to: {path} ({len(content)} bytes)"

@mcp.tool()
def fs_delete(path: str) -> str:
    """Delete a file."""
    target = _validate_path(path)
    if not target.exists():
        return f"❌ Does not exist: {path}"
    if target.is_dir():
        return f"❌ Is a directory (use fs_rmdir): {path}"
    target.unlink()
    return f"✅ Deleted: {path}"

@mcp.tool()
def fs_mkdir(path: str) -> str:
    """Create directory (including parents)."""
    target = _validate_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"✅ Created directory: {path}"

@mcp.tool()
def fs_rmdir(path: str, force: bool = False) -> str:
    """Remove directory."""
    target = _validate_path(path)
    if not target.exists():
        return f"❌ Does not exist: {path}"
    if not target.is_dir():
        return f"❌ Not a directory: {path}"
    
    if force:
        import shutil
        shutil.rmtree(target)
        return f"✅ Removed directory and contents: {path}"
    else:
        if any(target.iterdir()):
            return f"❌ Directory not empty (use force=True): {path}"
        target.rmdir()
        return f"✅ Removed directory: {path}"

@mcp.tool()
def fs_move(source: str, destination: str) -> str:
    """Move or rename file/directory."""
    src = _validate_path(source)
    dst = _validate_path(destination)
    if not src.exists():
        return f"❌ Source does not exist: {source}"
    src.rename(dst)
    return f"✅ Moved: {source} → {destination}"

@mcp.tool()
def fs_copy(source: str, destination: str) -> str:
    """Copy file or directory."""
    import shutil
    src = _validate_path(source)
    dst = _validate_path(destination)
    if not src.exists():
        return f"❌ Source does not exist: {source}"
    
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return f"✅ Copied: {source} → {destination}"

# =============================================================================
# PUBLISH TOOLS
# =============================================================================
@mcp.tool()
def publish(source: str, dest_name: str = None, domain: str = None) -> str:
    """Publish a file to the outputs directory for external access."""
    import shutil
    
    src = _validate_path(source)
    if not src.exists():
        return f"❌ Source does not exist: {source}"
    if not src.is_file():
        return f"❌ Source is not a file: {source}"
    
    filename = dest_name or src.name
    if domain:
        dest_dir = OUTPUTS_DIR / domain
    else:
        dest_dir = OUTPUTS_DIR
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    
    shutil.copy2(src, dest)
    
    if domain:
        url = f"{PUBLIC_BASE_URL}/{domain}/{filename}"
    else:
        url = f"{PUBLIC_BASE_URL}/{filename}"
    
    return f"✅ Published: {filename}\n📎 {url}"

@mcp.tool()
def publish_list(domain: str = None) -> str:
    """List published files."""
    if not OUTPUTS_DIR.exists():
        return "📂 No outputs published yet"
    
    target = OUTPUTS_DIR / domain if domain else OUTPUTS_DIR
    if not target.exists():
        return f"📂 No outputs for domain: {domain}" if domain else "📂 No outputs published yet"
    
    files = []
    for item in sorted(target.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(OUTPUTS_DIR)
            url = f"{PUBLIC_BASE_URL}/{rel_path}"
            size = item.stat().st_size
            files.append(f"📄 {rel_path} ({size} bytes)\n   {url}")
    
    if not files:
        return "📂 No outputs published yet"
    
    header = f"📤 Published Outputs" + (f" ({domain})" if domain else "") + "\n" + "─" * 40
    return f"{header}\n" + "\n".join(files)

@mcp.tool()
def unpublish(path: str) -> str:
    """Remove a published file."""
    target = OUTPUTS_DIR / path
    
    if not str(target.resolve()).startswith(str(OUTPUTS_DIR.resolve())):
        return f"❌ Invalid path: {path}"
    
    if not target.exists():
        return f"❌ Not found: {path}"
    if not target.is_file():
        return f"❌ Not a file: {path}"
    
    target.unlink()
    return f"✅ Unpublished: {path}"

# =============================================================================
# SHELL TOOLS
# =============================================================================
@mcp.tool()
def shell_exec(command: str, timeout: int = 30) -> str:
    """Execute shell command in the Super Claude container."""
    return _shell_exec_impl(command, timeout)

# =============================================================================
# DOCKER TOOLS
# =============================================================================
@mcp.tool()
def docker_ps(all: bool = False) -> str:
    """List Docker containers."""
    flag = "-a" if all else ""
    return _shell_exec_impl(f"docker ps {flag} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'")

@mcp.tool()
def docker_logs(container: str, lines: int = 50) -> str:
    """Get container logs."""
    return _shell_exec_impl(f"docker logs --tail {lines} {container}")

@mcp.tool()
def docker_restart(container: str) -> str:
    """Restart a container."""
    result = _shell_exec_impl(f"docker restart {container}")
    if "Error" not in result:
        return f"✅ Restarted: {container}"
    return result

@mcp.tool()
def docker_stop(container: str) -> str:
    """Stop a container."""
    result = _shell_exec_impl(f"docker stop {container}")
    if "Error" not in result:
        return f"✅ Stopped: {container}"
    return result

@mcp.tool()
def docker_start(container: str) -> str:
    """Start a stopped container."""
    result = _shell_exec_impl(f"docker start {container}")
    if "Error" not in result:
        return f"✅ Started: {container}"
    return result

# =============================================================================
# PLUGIN MANAGEMENT TOOLS (only if plugins available)
# =============================================================================
if PLUGINS_AVAILABLE:
    @mcp.tool()
    def plugin_status() -> str:
        """Get status of all loaded plugins and their tools."""
        return plugin_manager.plugin_status()
    
    @mcp.tool()
    def plugin_reload_changed() -> str:
        """Check for changed plugins and reload them dynamically."""
        return plugin_manager.reload_changed()
    
    @mcp.tool()
    def plugin_reload(plugin_name: str) -> str:
        """Manually reload a specific plugin."""
        return plugin_manager.reload_plugin(plugin_name)
    
    @mcp.tool()
    def plugin_list() -> str:
        """List all available plugins."""
        return plugin_manager.list_available()

# =============================================================================
# STORAGE TOOLS (Cloud Storage with Named Accounts)
# =============================================================================
if STORAGE_AVAILABLE:
    @mcp.tool()
    def storage_list_accounts() -> str:
        """List all configured storage accounts."""
        return storage_manager.list_accounts()
    
    @mcp.tool()
    def storage_add_account(
        name: str,
        provider: str,
        credentials_ref: str = "",
        config: str = "{}"
    ) -> str:
        """
        Add a new storage account.
        
        Args:
            name: Account label (e.g., "work", "personal")
            provider: Provider type ("gdrive", "onedrive", "dropbox")
            credentials_ref: 1Password reference for credentials
            config: JSON string with provider config
        """
        try:
            config_dict = json.loads(config) if config else {}
            return storage_manager.add_account(name, provider, credentials_ref, config_dict)
        except json.JSONDecodeError as e:
            return f"Invalid config JSON: {e}"
    
    @mcp.tool()
    def storage_remove_account(name: str) -> str:
        """Remove a storage account."""
        return storage_manager.remove_account(name)
    
    @mcp.tool()
    async def storage_list_files(account: str, path: str = "/") -> str:
        """List files in a storage account."""
        files = await storage_manager.list_files(account, path)
        if not files:
            return f"No files found at {path}"
        lines = [f"Files at {account}:{path}", "-" * 40]
        for f in files:
            icon = "D" if f.is_directory else "F"
            lines.append(f"[{icon}] {f.name}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def storage_upload(account: str, local_path: str, remote_path: str) -> str:
        """Upload a file to cloud storage."""
        local = _validate_path(local_path)
        return await storage_manager.upload(account, local, remote_path)
    
    @mcp.tool()
    async def storage_download(account: str, remote_path: str, local_path: str) -> str:
        """Download a file from cloud storage."""
        local = _validate_path(local_path)
        return await storage_manager.download(account, remote_path, local)

# =============================================================================
# OPS MANAGEMENT
# =============================================================================
@mcp.tool()
def rebuild_ops() -> str:
    """Full rebuild of super-claude-ops container."""
    steps = ["🔧 Rebuilding Ops from Super Claude...", ""]
    
    steps.append("1️⃣ Building image...")
    success, output = _run_command("docker build -t super-claude-ops -f mcps/ops/Dockerfile .", timeout=300)
    if not success:
        return "\n".join(steps) + f"\n❌ Build failed:\n{output}"
    steps.append("   ✅ Image built")
    
    steps.append("2️⃣ Stopping old container...")
    _run_command("docker stop super-claude-ops")
    _run_command("docker rm super-claude-ops")
    steps.append("   ✅ Stopped and removed")
    
    steps.append("3️⃣ Starting new container...")
    run_cmd = f"""docker run -d \
        --name super-claude-ops \
        --network {DOCKER_NETWORK} \
        --env-file /data/config/.env \
        -p 8001:8001 \
        -v /volume1/docker/super-claude:/data \
        -v /var/run/docker.sock:/var/run/docker.sock \
        --restart unless-stopped \
        super-claude-ops"""
    success, output = _run_command(run_cmd)
    if not success:
        return "\n".join(steps) + f"\n❌ Run failed:\n{output}"
    steps.append("   ✅ Started")
    
    steps.append("")
    steps.append("✅ Ops rebuilt successfully!")
    steps.append("")
    steps.append("⚠️  Remember: Disconnect and reconnect the Ops connector, then start a new chat.")
    
    return "\n".join(steps)

# =============================================================================
# =============================================================================
# SUPERNOTE PLUGIN TOOLS
# =============================================================================
# Expose supernote plugin tools via MCP
# Plugin handles sync between domains and cloud storage (where Supernote syncs)

if PLUGINS_AVAILABLE and 'supernote' in plugin_loader.loaded_plugins:
    _supernote = plugin_loader.loaded_plugins['supernote']
    
    @mcp.tool()
    async def supernote_setup(
        domain: str,
        account: str,
        subfolder: str,
        sync_notes: bool = True,
        sync_documents: bool = True,
        convert_to: str = "pdf,png"
    ) -> str:
        """
        Configure Supernote sync for a domain.
        
        Args:
            domain: Domain name to configure
            account: Storage account name (from storage_list_accounts)
            subfolder: Subfolder name on Supernote (e.g., "burrillville")
            sync_notes: Whether to sync .note files from device (default: True)
            sync_documents: Whether to sync documents to device (default: True)
            convert_to: Formats to convert .note files to (comma-separated: pdf,png)
        """
        return await _supernote.supernote_setup(domain, account, subfolder, sync_notes, sync_documents, convert_to)
    
    @mcp.tool()
    async def supernote_status(domain: str) -> str:
        """Show Supernote sync status for a domain."""
        return await _supernote.supernote_status(domain)
    
    @mcp.tool()
    async def supernote_pull(domain: str, convert: bool = True) -> str:
        """
        Pull .note files from Supernote (via cloud storage).
        
        Args:
            domain: Domain name
            convert: Whether to convert .note files to PDF/PNG (default: True)
        """
        return await _supernote.supernote_pull(domain, convert)
    
    @mcp.tool()
    async def supernote_push(domain: str) -> str:
        """Push documents to Supernote (via cloud storage)."""
        return await _supernote.supernote_push(domain)
    
    @mcp.tool()
    async def supernote_list_remote(domain: str, path_type: str = "notes") -> str:
        """
        List files in the remote Supernote folder.
        
        Args:
            domain: Domain name
            path_type: "notes" or "documents"
        """
        return await _supernote.supernote_list_remote(domain, path_type)

    @mcp.tool()
    async def supernote_list_notes(domain: str) -> str:
        """
        List available notes for a domain with their page counts.
        
        Args:
            domain: Domain name
        
        Returns:
            List of notes and their converted pages
        """
        return await _supernote.supernote_list_notes(domain)
    
    @mcp.tool()
    async def supernote_read_note(domain: str, note_stem: str):
        """
        Read all pages of a Supernote note as images.
        
        This returns the converted PNG pages as images that Claude can see
        and interpret using vision. Use this to extract content from handwritten notes.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension (e.g., "20260116_140203")
        
        Returns:
            List of Image objects (one per page) that Claude can see
        """
        return await _supernote.supernote_read_note(domain, note_stem)
    
    @mcp.tool()
    async def supernote_read_page(domain: str, note_stem: str, page: int = 0):
        """
        Read a single page of a Supernote note as an image.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension (e.g., "20260116_140203")
            page: Page number (0-indexed)
        
        Returns:
            Image object that Claude can see
        """
        return await _supernote.supernote_read_page(domain, note_stem, page)

# MAIN
# =============================================================================
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
