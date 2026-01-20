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

# =============================================================================
# SHARED MODULE IMPORTS
# =============================================================================
# Add shared directory to path
sys.path.insert(0, "/app/shared")
sys.path.insert(0, "/data/shared")

try:
    from config import (
        SUPER_CLAUDE_ROOT, DOMAINS_DIR, CONFIG_DIR, OUTPUTS_DIR,
        PLUGINS_DIR, CORE_DIR, PROVIDERS_DIR, STORAGE_CONFIG,
        DOCKER_NETWORK, PUBLIC_BASE_URL
    )
    from shell import run_shell, run_shell_simple, is_command_blocked
    SHARED_MODULES_AVAILABLE = True
    logger.info("Shared modules loaded")
except ImportError as e:
    logger.warning(f"Shared modules unavailable, using local definitions: {e}")
    SHARED_MODULES_AVAILABLE = False
    # Fallback definitions
    SUPER_CLAUDE_ROOT = Path("/data")
    DOMAINS_DIR = SUPER_CLAUDE_ROOT / "domains"
    CONFIG_DIR = SUPER_CLAUDE_ROOT / "config"
    OUTPUTS_DIR = SUPER_CLAUDE_ROOT / "outputs"
    PLUGINS_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "plugins"
    CORE_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "core"
    PROVIDERS_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "providers"
    STORAGE_CONFIG = CONFIG_DIR / "storage_accounts.json"
    DOCKER_NETWORK = "super-claude_super-claude-net"
    PUBLIC_BASE_URL = "https://zanni.synology.me/super-claude-output"

# =============================================================================
# PLUGIN SYSTEM INITIALIZATION
# =============================================================================
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

try:
    from plugin_loader import PluginLoader
    from plugin_manager import PluginManager
    PLUGINS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Plugin system unavailable: {e}")
    PLUGINS_AVAILABLE = False

# Also import 1Password helper for backward compatibility
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
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))
if str(PROVIDERS_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDERS_DIR))

try:
    from storage_manager import StorageManager
    from providers.gdrive import GoogleDriveProvider
    storage_manager = StorageManager(STORAGE_CONFIG)
    storage_manager.register_provider_type("gdrive", GoogleDriveProvider)
    STORAGE_AVAILABLE = True
    logger.info("Storage system initialized")
except ImportError as e:
    logger.warning(f"Storage system unavailable: {e}")
    storage_manager = None
    STORAGE_AVAILABLE = False

# =============================================================================
# MAIL SERVICE INITIALIZATION
# =============================================================================
SERVICES_DIR = SUPER_CLAUDE_ROOT / "mcps" / "super-claude" / "services"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

try:
    from mail.manager import MailManager
    from mail.adapters.gmail import GmailAdapter
    mail_manager = MailManager()
    mail_manager.register_adapter_type("gmail", GmailAdapter)
    MAIL_AVAILABLE = True
    logger.info("Mail service initialized")
except ImportError as e:
    logger.warning(f"Mail service unavailable: {e}")
    mail_manager = None
    MAIL_AVAILABLE = False

# =============================================================================
# CALENDAR SERVICE INITIALIZATION
# =============================================================================
try:
    from calendarservice.manager import CalendarManager
    from calendarservice.adapters.gcal import GCalAdapter
    calendar_manager = CalendarManager()
    calendar_manager.register_adapter_type("gcal", GCalAdapter)
    CALENDAR_AVAILABLE = True
    logger.info("Calendar service initialized")
except ImportError as e:
    logger.warning(f"Calendar service unavailable: {e}")
    calendar_manager = None
    CALENDAR_AVAILABLE = False

# =============================================================================
# CONTACTS SERVICE INITIALIZATION
# =============================================================================
try:
    from contacts.manager import ContactsManager
    from contacts.adapters.gcontacts import GoogleContactsAdapter
    contacts_manager = ContactsManager()
    contacts_manager.register_adapter_type("gcontacts", GoogleContactsAdapter)
    CONTACTS_AVAILABLE = True
    logger.info("Contacts service initialized")
except ImportError as e:
    logger.warning(f"Contacts service unavailable: {e}")
    contacts_manager = None
    CONTACTS_AVAILABLE = False


# =============================================================================
# DOMAIN CONFIG
# =============================================================================
def _load_domain_config() -> dict:
    """Load domain triggers and descriptions from config file."""
    config_file = CONFIG_DIR / "domain_triggers.json"
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
    """Run shell command, return (success, output). Uses shared module if available."""
    if SHARED_MODULES_AVAILABLE:
        return run_shell(command, timeout, cwd=SUPER_CLAUDE_ROOT)
    
    # Fallback implementation
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
    return DOMAINS_DIR / domain

def _check_token_expiry() -> str | None:
    """Check if token is expiring soon. Returns warning message or None."""
    try:
        state_file = DOMAINS_DIR / "super-claude" / "state.json"
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
    except Exception as e:
        logger.debug(f"Token expiry check failed: {e}")
        return None

def _detect_domain(text: str) -> str | None:
    """Detect domain from text based on keywords. Returns domain name or None."""
    text_lower = text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return domain
    return None


def _load_global_instructions() -> str | None:
    """Load global INSTRUCTIONS.md if it exists. Returns content or None."""
    instructions_file = SUPER_CLAUDE_ROOT / "INSTRUCTIONS.md"
    if instructions_file.exists():
        try:
            return instructions_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Failed to load global instructions: {e}")
    return None

def _get_available_domains() -> list[dict]:
    """Get list of available domains with their descriptions."""
    if not DOMAINS_DIR.exists():
        return []
    
    domains = []
    for item in sorted(DOMAINS_DIR.iterdir()):
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
    if SHARED_MODULES_AVAILABLE:
        return run_shell_simple(command, timeout)
    
    # Fallback implementation
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
        
        result = f"📖 Loaded domain: {domain}\n\n{file_content}{trigger_note}"
        
        # Load domain-specific instructions if they exist
        instructions_file = domain_path / "INSTRUCTIONS.md"
        if instructions_file.exists():
            try:
                instructions_content = instructions_file.read_text().strip()
                if instructions_content:
                    result += "\n\n📋 Domain Instructions\n" + "─" * 30 + "\n" + instructions_content
            except Exception:
                pass  # Silently skip if we can't read instructions
        
        return result
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
    
    
    # Global instructions
    global_instructions = _load_global_instructions()
    if global_instructions:
        lines.append("")
        lines.append("📋 Global Instructions")
        lines.append("─" * 30)
        lines.append(global_instructions)
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
        state_file = DOMAINS_DIR / "super-claude" / "state.json"
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
        state_file = DOMAINS_DIR / "super-claude" / "state.json"
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
def instructions_get(domain: str = "") -> str:
    """
    Get instructions for a domain or global instructions.
    
    Args:
        domain: Domain name, or empty string for global instructions
    
    Returns:
        The contents of INSTRUCTIONS.md (domain-specific or global)
    """
    if domain:
        instructions_file = _get_domain_path(domain) / "INSTRUCTIONS.md"
        label = f"Domain '{domain}'"
    else:
        instructions_file = SUPER_CLAUDE_ROOT / "INSTRUCTIONS.md"
        label = "Global"
    
    if not instructions_file.exists():
        return f"📋 No {label.lower()} instructions found. Use instructions_set to create them."
    
    try:
        content = instructions_file.read_text().strip()
        return f"📋 {label} Instructions\n{'─' * 30}\n{content}"
    except Exception as e:
        return f"❌ Error reading instructions: {e}"

@mcp.tool()
def instructions_set(content: str, domain: str = "") -> str:
    """
    Set instructions for a domain or global instructions.
    
    Args:
        content: The instruction content (markdown)
        domain: Domain name, or empty string for global instructions
    
    Returns:
        Confirmation message
    """
    if domain:
        domain_path = _get_domain_path(domain)
        if not domain_path.exists():
            return f"❌ Domain '{domain}' does not exist"
        instructions_file = domain_path / "INSTRUCTIONS.md"
        label = f"domain '{domain}'"
    else:
        instructions_file = SUPER_CLAUDE_ROOT / "INSTRUCTIONS.md"
        label = "global"
    
    try:
        instructions_file.write_text(content.strip() + "\n")
        return f"✅ Updated {label} instructions ({len(content)} bytes)"
    except Exception as e:
        return f"❌ Error writing instructions: {e}"

@mcp.tool()
def context_list() -> str:
    """List all available domains and their status."""
    if not DOMAINS_DIR.exists():
        return "❌ Domains directory not found"
    
    domains = []
    for item in sorted(DOMAINS_DIR.iterdir()):
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
# MAIL TOOLS
# =============================================================================
if MAIL_AVAILABLE:
    @mcp.tool()
    def mail_list_accounts() -> str:
        """List all configured mail accounts."""
        return mail_manager.list_accounts()
    
    @mcp.tool()
    def mail_add_account(
        name: str,
        adapter: str,
        credentials_ref: str = "",
        config: str = "{}"
    ) -> str:
        """Add a new mail account."""
        try:
            config_dict = json.loads(config) if config else {}
            return mail_manager.add_account(name, adapter, credentials_ref, config_dict)
        except json.JSONDecodeError as e:
            return f"Invalid config JSON: {e}"
    
    @mcp.tool()
    def mail_remove_account(name: str) -> str:
        """Remove a mail account."""
        return mail_manager.remove_account(name)
    
    @mcp.tool()
    async def mail_list_folders(account: str) -> str:
        """List mailbox folders."""
        folders = await mail_manager.list_folders(account)
        if not folders:
            return f"No folders found or could not connect to {account}"
        lines = [f"📁 Folders in {account}", "─" * 40]
        for f in folders:
            unread = f" ({f.unread_count} unread)" if f.unread_count else ""
            lines.append(f"  {f.name}{unread}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def mail_list_messages(
        account: str,
        folder: str = "INBOX",
        limit: int = 20,
        unread_only: bool = False
    ) -> str:
        """List messages in a folder."""
        page = await mail_manager.list_messages(account, folder, limit, unread_only=unread_only)
        if not page.messages:
            return f"No messages in {folder}"
        lines = [f"📧 Messages in {account}/{folder}", "─" * 40]
        for m in page.messages:
            date_str = m.date.strftime("%m/%d %H:%M") if m.date else ""
            unread = "●" if any(f.value == "unread" for f in m.flags) else " "
            lines.append(f"{unread} {date_str} | {m.sender.email[:25]:<25} | {m.subject[:40]}")
            lines.append(f"    ID: {m.id}")
        if page.next_cursor:
            lines.append(f"\n(more messages available)")
        return "\n".join(lines)
    
    @mcp.tool()
    async def mail_get_message(account: str, message_id: str) -> str:
        """Get full message with body."""
        msg = await mail_manager.get_message(account, message_id)
        if not msg:
            return f"Message not found: {message_id}"
        lines = [
            f"📧 Message: {msg.subject}",
            "─" * 40,
            f"From: {msg.sender}",
            f"To: {', '.join(str(r) for r in msg.recipients)}",
            f"Date: {msg.date}",
        ]
        if msg.cc:
            lines.append(f"CC: {', '.join(str(r) for r in msg.cc)}")
        if msg.attachments:
            lines.append(f"Attachments: {len(msg.attachments)}")
        lines.append("")
        lines.append(msg.body_text or msg.body_html or "(no body)")
        return "\n".join(lines)
    
    @mcp.tool()
    async def mail_search(account: str, query: str, limit: int = 20) -> str:
        """Search messages."""
        page = await mail_manager.search(account, query, limit=limit)
        if not page.messages:
            return f"No messages matching: {query}"
        lines = [f"🔍 Search: {query}", "─" * 40]
        for m in page.messages:
            date_str = m.date.strftime("%m/%d") if m.date else ""
            lines.append(f"{date_str} | {m.sender.email[:20]} | {m.subject[:35]}")
            lines.append(f"    ID: {m.id}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def mail_send(
        account: str,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        html: bool = False
    ) -> str:
        """Send an email."""
        to_list = [t.strip() for t in to.split(",") if t.strip()]
        cc_list = [c.strip() for c in cc.split(",") if c.strip()] if cc else None
        return await mail_manager.send(account, to_list, subject, body, cc=cc_list, html=html)
    
    @mcp.tool()
    async def mail_delete(account: str, message_id: str, permanent: bool = False) -> str:
        """Delete a message (moves to trash by default)."""
        return await mail_manager.delete(account, message_id, permanent)
    
    @mcp.tool()
    async def mail_mark_read(account: str, message_id: str, read: bool = True) -> str:
        """Mark message as read or unread."""
        return await mail_manager.mark_read(account, message_id, read)

# =============================================================================
# CALENDAR TOOLS
# =============================================================================
if CALENDAR_AVAILABLE:
    @mcp.tool()
    def calendar_list_accounts() -> str:
        """List all configured calendar accounts."""
        return calendar_manager.list_accounts()
    
    @mcp.tool()
    def calendar_add_account(
        name: str,
        adapter: str,
        credentials_ref: str = "",
        config: str = "{}"
    ) -> str:
        """Add a new calendar account."""
        try:
            config_dict = json.loads(config) if config else {}
            return calendar_manager.add_account(name, adapter, credentials_ref, config_dict)
        except json.JSONDecodeError as e:
            return f"Invalid config JSON: {e}"
    
    @mcp.tool()
    def calendar_remove_account(name: str) -> str:
        """Remove a calendar account."""
        return calendar_manager.remove_account(name)
    
    @mcp.tool()
    async def calendar_list_calendars(account: str) -> str:
        """List available calendars."""
        calendars = await calendar_manager.list_calendars(account)
        if not calendars:
            return f"No calendars found or could not connect to {account}"
        lines = [f"📅 Calendars in {account}", "─" * 40]
        for c in calendars:
            primary = " (primary)" if c.primary else ""
            lines.append(f"  {c.name}{primary}")
            lines.append(f"    ID: {c.id}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def calendar_list_events(
        account: str,
        calendar_id: str = "primary",
        days: int = 7,
        limit: int = 50
    ) -> str:
        """List upcoming events."""
        from datetime import datetime, timedelta, timezone
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=days)
        page = await calendar_manager.list_events(account, calendar_id, start, end, limit)
        if not page.events:
            return f"No events in the next {days} days"
        lines = [f"📅 Events ({days} days)", "─" * 40]
        for e in page.events:
            date_str = e.start.strftime("%m/%d %H:%M") if not e.all_day else e.start.strftime("%m/%d") + " (all day)"
            lines.append(f"{date_str} | {e.title}")
            if e.location:
                lines.append(f"    📍 {e.location}")
            lines.append(f"    ID: {e.id}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def calendar_get_event(account: str, calendar_id: str, event_id: str) -> str:
        """Get full event details."""
        event = await calendar_manager.get_event(account, calendar_id, event_id)
        if not event:
            return f"Event not found: {event_id}"
        lines = [
            f"📅 {event.title}",
            "─" * 40,
            f"Start: {event.start}",
            f"End: {event.end}",
        ]
        if event.location:
            lines.append(f"Location: {event.location}")
        if event.description:
            lines.append(f"\nDescription:\n{event.description}")
        if event.attendees:
            lines.append(f"\nAttendees:")
            for a in event.attendees:
                status = a.response.value if a.response else "unknown"
                lines.append(f"  - {a.email} ({status})")
        if event.conference_link:
            lines.append(f"\nConference: {event.conference_link}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def calendar_create_event(
        account: str,
        title: str,
        start: str,
        end: str,
        calendar_id: str = "primary",
        description: str = "",
        location: str = "",
        attendees: str = "",
        all_day: bool = False,
        conference: bool = False
    ) -> str:
        """Create a new event. Dates should be ISO format (YYYY-MM-DDTHH:MM:SS)."""
        from datetime import datetime
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as e:
            return f"❌ Invalid date format: {e}"
        
        attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else None
        
        return await calendar_manager.create_event(
            account, calendar_id, title, start_dt, end_dt,
            description=description or None,
            location=location or None,
            attendees=attendee_list,
            all_day=all_day,
            conference=conference
        )
    
    @mcp.tool()
    async def calendar_delete_event(account: str, calendar_id: str, event_id: str) -> str:
        """Delete an event."""
        return await calendar_manager.delete_event(account, calendar_id, event_id)

# =============================================================================
# CONTACTS TOOLS
# =============================================================================
if CONTACTS_AVAILABLE:
    @mcp.tool()
    def contacts_list_accounts() -> str:
        """List all configured contacts accounts."""
        return contacts_manager.list_accounts()
    
    @mcp.tool()
    def contacts_add_account(
        name: str,
        adapter: str,
        credentials_ref: str = "",
        config: str = "{}"
    ) -> str:
        """Add a new contacts account."""
        try:
            config_dict = json.loads(config) if config else {}
            return contacts_manager.add_account(name, adapter, credentials_ref, config_dict)
        except json.JSONDecodeError as e:
            return f"Invalid config JSON: {e}"
    
    @mcp.tool()
    def contacts_remove_account(name: str) -> str:
        """Remove a contacts account."""
        return contacts_manager.remove_account(name)
    
    @mcp.tool()
    async def contacts_list(account: str, limit: int = 50) -> str:
        """List contacts."""
        page = await contacts_manager.list_contacts(account, limit)
        if not page.contacts:
            return f"No contacts found in {account}"
        lines = [f"👤 Contacts in {account}", "─" * 40]
        for c in page.contacts:
            email = c.primary_email or ""
            phone = c.primary_phone or ""
            info = f" | {email}" if email else ""
            info += f" | {phone}" if phone else ""
            lines.append(f"  {c.display_name}{info}")
            lines.append(f"    ID: {c.id}")
        if page.next_cursor:
            lines.append(f"\n(more contacts available)")
        return "\n".join(lines)
    
    @mcp.tool()
    async def contacts_search(account: str, query: str, limit: int = 20) -> str:
        """Search contacts by name, email, or phone."""
        contacts = await contacts_manager.search_contacts(account, query, limit)
        if not contacts:
            return f"No contacts matching: {query}"
        lines = [f"🔍 Search: {query}", "─" * 40]
        for c in contacts:
            email = c.primary_email or ""
            lines.append(f"  {c.display_name} | {email}")
            lines.append(f"    ID: {c.id}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def contacts_get(account: str, contact_id: str) -> str:
        """Get full contact details."""
        contact = await contacts_manager.get_contact(account, contact_id)
        if not contact:
            return f"Contact not found: {contact_id}"
        lines = [
            f"👤 {contact.display_name}",
            "─" * 40,
        ]
        if contact.organizations:
            org = contact.organizations[0]
            if org.title and org.name:
                lines.append(f"🏢 {org.title} at {org.name}")
            elif org.name:
                lines.append(f"🏢 {org.name}")
            elif org.title:
                lines.append(f"💼 {org.title}")
        if contact.emails:
            lines.append("\nEmails:")
            for e in contact.emails:
                primary = " (primary)" if e.primary else ""
                lines.append(f"  📧 {e.address}{primary}")
        if contact.phones:
            lines.append("\nPhones:")
            for p in contact.phones:
                primary = " (primary)" if p.primary else ""
                lines.append(f"  📱 {p.number} ({p.type.value}){primary}")
        if contact.addresses:
            lines.append("\nAddresses:")
            for a in contact.addresses:
                lines.append(f"  📍 {a.formatted or 'No formatted address'}")
        if contact.birthday:
            lines.append(f"\n🎂 Birthday: {contact.birthday}")
        if contact.notes:
            lines.append(f"\nNotes: {contact.notes}")
        return "\n".join(lines)
    
    @mcp.tool()
    async def contacts_create(
        account: str,
        given_name: str = "",
        family_name: str = "",
        email: str = "",
        phone: str = "",
        organization: str = "",
        title: str = "",
        notes: str = ""
    ) -> str:
        """Create a new contact."""
        return await contacts_manager.create_contact(
            account,
            given_name=given_name or None,
            family_name=family_name or None,
            email=email or None,
            phone=phone or None,
            organization=organization or None,
            title=title or None,
            notes=notes or None
        )
    
    @mcp.tool()
    async def contacts_update(
        account: str,
        contact_id: str,
        given_name: str = None,
        family_name: str = None,
        email: str = None,
        phone: str = None,
        organization: str = None,
        title: str = None,
        notes: str = None
    ) -> str:
        """Update an existing contact."""
        return await contacts_manager.update_contact(
            account, contact_id,
            given_name=given_name,
            family_name=family_name,
            email=email,
            phone=phone,
            organization=organization,
            title=title,
            notes=notes
        )
    
    @mcp.tool()
    async def contacts_delete(account: str, contact_id: str) -> str:
        """Delete a contact."""
        return await contacts_manager.delete_contact(account, contact_id)
    
    @mcp.tool()
    async def contacts_list_groups(account: str) -> str:
        """List contact groups/labels."""
        groups = await contacts_manager.list_groups(account)
        if not groups:
            return f"No groups found in {account}"
        lines = [f"🏷️ Contact Groups in {account}", "─" * 40]
        for g in groups:
            type_str = " (system)" if g.group_type == "system" else ""
            lines.append(f"  {g.name}{type_str} - {g.member_count} members")
            lines.append(f"    ID: {g.id}")
        return "\n".join(lines)

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
# SUPERNOTE PLUGIN TOOLS
# =============================================================================
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
    async def supernote_list_notes(domain: str, include_processed: bool = False) -> str:
        """
        List available notes for a domain with their page counts.
        
        Args:
            domain: Domain name
            include_processed: Whether to show processed notes (default: False)
        
        Returns:
            List of notes and their converted pages
        """
        return await _supernote.supernote_list_notes(domain, include_processed)
    
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
    
    @mcp.tool()
    async def supernote_mark_processed(domain: str, note_stem: str) -> str:
        """
        Mark a note as processed by moving it to the processed folder.
        
        The .note file moves to processed/. Converted PNGs stay in converted/
        for future reference.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension (e.g., "20260116_140203")
        
        Returns:
            Confirmation message
        """
        return await _supernote.supernote_mark_processed(domain, note_stem)
    
    @mcp.tool()
    async def supernote_unprocess(domain: str, note_stem: str) -> str:
        """
        Move a processed note back to pending.
        
        Args:
            domain: Domain name
            note_stem: Note filename without extension
        
        Returns:
            Confirmation message
        """
        return await _supernote.supernote_unprocess(domain, note_stem)

# MAIN
# =============================================================================
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
