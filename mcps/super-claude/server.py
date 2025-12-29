"""
Super Claude MCP Server

Central MCP providing:
- Auth: 1Password secret retrieval
- Filesystem: Read, write, delete, move files within sandbox
- Shell: Execute commands
- Docker: Container management
- Context: Domain-specific knowledge loading
- Publish: Output files to web-accessible location
- Ops: Rebuild ops container (mutual administration)
"""

from fastmcp import FastMCP
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Import 1Password helper
import sys
sys.path.insert(0, "/app/shared")
from op_client import get_secret, get_secret_by_ref

mcp = FastMCP("Super Claude")

# =============================================================================
# CONFIG
# =============================================================================
SUPER_CLAUDE_ROOT = Path("/data")  # Mounted volume: /volume1/docker/super-claude
DOCKER_NETWORK = "super-claude_super-claude-net"
OUTPUTS_DIR = SUPER_CLAUDE_ROOT / "outputs"
PUBLIC_BASE_URL = "https://zanni.synology.me/super-claude-output"

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

# =============================================================================
# HEALTH
# =============================================================================
@mcp.tool()
def ping() -> str:
    """Health check. Returns pong if the auth MCP is running."""
    return "pong from Super Claude 🚀"

# =============================================================================
# CONTEXT SYSTEM
# =============================================================================
@mcp.tool()
def context_load(domain: str) -> str:
    """
    Load domain context - the core {domain}.md file that establishes working context.
    
    Args:
        domain: Domain name (e.g., "msf", "grc", "super-claude")
    
    Returns:
        Domain context content or error message
    """
    domain_path = _get_domain_path(domain)
    context_file = domain_path / f"{domain}.md"
    
    if not domain_path.exists():
        return f"❌ Domain '{domain}' does not exist"
    if not context_file.exists():
        return f"❌ Context file not found: {domain}.md"
    
    try:
        content = context_file.read_text()
        # Update last session in state.json
        state_file = domain_path / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                state["lastSession"] = datetime.now().isoformat()[:10]
                state_file.write_text(json.dumps(state, indent=2))
            except:
                pass  # Don't fail if state update fails
        
        return f"📖 Loaded domain: {domain}\n\n{content}"
    except Exception as e:
        return f"❌ Error loading context: {e}"

@mcp.tool()
def context_get(domain: str, file: str) -> str:
    """
    Get specific context file from domain's context/ directory.
    
    Args:
        domain: Domain name
        file: File name within domain/context/
    
    Returns:
        File content or error message
    """
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
    """
    Update domain state.json with key-value data.
    
    Args:
        domain: Domain name
        key: State key to update
        value: State value (will be JSON parsed if possible)
    
    Returns:
        Success message or error
    """
    domain_path = _get_domain_path(domain)
    state_file = domain_path / "state.json"
    
    if not domain_path.exists():
        return f"❌ Domain '{domain}' does not exist"
    
    # Load or create state
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            state = {}
    else:
        state = {"created": datetime.now().isoformat()[:10]}
    
    # Try to parse value as JSON, fall back to string
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    # Update state
    state[key] = parsed_value
    state["lastUpdated"] = datetime.now().isoformat()[:10]
    
    try:
        state_file.write_text(json.dumps(state, indent=2))
        return f"✅ Updated {domain} state: {key} = {parsed_value}"
    except Exception as e:
        return f"❌ Error updating state: {e}"

@mcp.tool()
def context_list() -> str:
    """
    List all available domains.
    
    Returns:
        Formatted list of domains with status
    """
    domains_dir = SUPER_CLAUDE_ROOT / "domains"
    if not domains_dir.exists():
        return "❌ Domains directory not found"
    
    domains = []
    for item in sorted(domains_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            # Check for core files
            has_md = (item / f"{item.name}.md").exists()
            has_state = (item / "state.json").exists()
            has_context = (item / "context").exists()
            
            status = "✅" if has_md else "⚠️"
            details = []
            if has_md: details.append("md")
            if has_state: details.append("state")
            if has_context: details.append("context")
            
            domains.append(f"{status} {item.name} ({', '.join(details)})")
    
    header = "📚 Available Domains\n" + "─" * 30
    listing = "\n".join(domains) if domains else "(no domains found)"
    return f"{header}\n{listing}"

# =============================================================================
# AUTH TOOLS
# =============================================================================
@mcp.tool()
async def auth_get(item_name: str, field: str = "credential", vault: str = "Key Vault") -> str:
    """
    Get a secret from 1Password.

    Args:
        item_name: Name of the item in 1Password (e.g., "GitHub PAT - Claude Code")
        field: Field name to retrieve (default: "credential")
        vault: Vault name (default: "Key Vault")

    Returns:
        The secret value, or error message if retrieval fails
    """
    return await get_secret(item_name, field, vault)

@mcp.tool()
async def auth_get_ref(secret_ref: str) -> str:
    """
    Get a secret using a full 1Password secret reference.

    Args:
        secret_ref: Full secret reference URI (e.g., "op://Key Vault/GitHub PAT/credential")

    Returns:
        The secret value, or error message if retrieval fails
    """
    return await get_secret_by_ref(secret_ref)

# =============================================================================
# FILESYSTEM TOOLS
# =============================================================================
def _validate_path(path: str) -> Path:
    """Ensure path is within sandbox. Returns resolved Path."""
    # Handle absolute vs relative paths
    if path.startswith("/"):
        resolved = Path(path).resolve()
    else:
        resolved = (SUPER_CLAUDE_ROOT / path).resolve()
    
    # Must be within root
    if not str(resolved).startswith(str(SUPER_CLAUDE_ROOT)):
        raise ValueError(f"Path outside sandbox: {path}")
    return resolved

@mcp.tool()
def fs_list(path: str = ".") -> str:
    """
    List directory contents.
    
    Args:
        path: Directory path relative to super-claude root (default: root)
    
    Returns:
        Formatted listing of files and folders
    """
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
    """
    Read file contents.
    
    Args:
        path: File path relative to super-claude root
    
    Returns:
        File contents as string
    """
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
    """
    Write content to file. Creates parent directories if needed.
    
    Args:
        path: File path relative to super-claude root
        content: Content to write
    
    Returns:
        Success message with bytes written
    """
    target = _validate_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"✅ Written: {path} ({len(content)} bytes)"

@mcp.tool()
def fs_append(path: str, content: str) -> str:
    """
    Append content to file. Creates file if it doesn't exist.
    
    Args:
        path: File path relative to super-claude root
        content: Content to append
    
    Returns:
        Success message
    """
    target = _validate_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a") as f:
        f.write(content)
    return f"✅ Appended to: {path} ({len(content)} bytes)"

@mcp.tool()
def fs_delete(path: str) -> str:
    """
    Delete a file.
    
    Args:
        path: File path relative to super-claude root
    
    Returns:
        Success or error message
    """
    target = _validate_path(path)
    if not target.exists():
        return f"❌ Does not exist: {path}"
    if target.is_dir():
        return f"❌ Is a directory (use fs_rmdir): {path}"
    target.unlink()
    return f"✅ Deleted: {path}"

@mcp.tool()
def fs_mkdir(path: str) -> str:
    """
    Create directory (including parents).
    
    Args:
        path: Directory path relative to super-claude root
    
    Returns:
        Success message
    """
    target = _validate_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"✅ Created directory: {path}"

@mcp.tool()
def fs_rmdir(path: str, force: bool = False) -> str:
    """
    Remove directory.
    
    Args:
        path: Directory path relative to super-claude root
        force: If True, remove directory and all contents. If False, directory must be empty.
    
    Returns:
        Success or error message
    """
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
    """
    Move or rename file/directory.
    
    Args:
        source: Source path relative to super-claude root
        destination: Destination path relative to super-claude root
    
    Returns:
        Success or error message
    """
    src = _validate_path(source)
    dst = _validate_path(destination)
    if not src.exists():
        return f"❌ Source does not exist: {source}"
    src.rename(dst)
    return f"✅ Moved: {source} → {destination}"

@mcp.tool()
def fs_copy(source: str, destination: str) -> str:
    """
    Copy file or directory.
    
    Args:
        source: Source path relative to super-claude root
        destination: Destination path relative to super-claude root
    
    Returns:
        Success or error message
    """
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
    """
    Publish a file to the outputs directory for external access.
    
    Args:
        source: Source file path relative to super-claude root
        dest_name: Optional destination filename (defaults to source filename)
        domain: Optional domain folder to organize under (e.g., "entertainment", "msf")
    
    Returns:
        Public URL for the published file
    """
    import shutil
    
    src = _validate_path(source)
    if not src.exists():
        return f"❌ Source does not exist: {source}"
    if not src.is_file():
        return f"❌ Source is not a file: {source}"
    
    # Determine destination
    filename = dest_name or src.name
    if domain:
        dest_dir = OUTPUTS_DIR / domain
    else:
        dest_dir = OUTPUTS_DIR
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    
    # Copy file
    shutil.copy2(src, dest)
    
    # Build URL
    if domain:
        url = f"{PUBLIC_BASE_URL}/{domain}/{filename}"
    else:
        url = f"{PUBLIC_BASE_URL}/{filename}"
    
    return f"✅ Published: {filename}\n📎 {url}"

@mcp.tool()
def publish_list(domain: str = None) -> str:
    """
    List published files.
    
    Args:
        domain: Optional domain to filter by
    
    Returns:
        List of published files with URLs
    """
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
    """
    Remove a published file.
    
    Args:
        path: Path relative to outputs (e.g., "entertainment/watchlist.md")
    
    Returns:
        Success or error message
    """
    target = OUTPUTS_DIR / path
    
    # Security check - must be within outputs
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
    """
    Execute shell command.
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 30)
    
    Returns:
        Command output (stdout + stderr) or error message
    """
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

# =============================================================================
# DOCKER TOOLS
# =============================================================================
@mcp.tool()
def docker_ps(all: bool = False) -> str:
    """
    List Docker containers.
    
    Args:
        all: If True, show all containers. If False, only running.
    
    Returns:
        Formatted container list
    """
    flag = "-a" if all else ""
    return shell_exec(f"docker ps {flag} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'")

@mcp.tool()
def docker_logs(container: str, lines: int = 50) -> str:
    """
    Get container logs.
    
    Args:
        container: Container name
        lines: Number of lines to retrieve (default: 50)
    
    Returns:
        Container log output
    """
    return shell_exec(f"docker logs --tail {lines} {container}")

@mcp.tool()
def docker_restart(container: str) -> str:
    """
    Restart a container.
    
    Args:
        container: Container name
    
    Returns:
        Success or error message
    """
    result = shell_exec(f"docker restart {container}")
    if "Error" not in result:
        return f"✅ Restarted: {container}"
    return result

@mcp.tool()
def docker_stop(container: str) -> str:
    """
    Stop a container.
    
    Args:
        container: Container name
    
    Returns:
        Success or error message
    """
    result = shell_exec(f"docker stop {container}")
    if "Error" not in result:
        return f"✅ Stopped: {container}"
    return result

@mcp.tool()
def docker_start(container: str) -> str:
    """
    Start a stopped container.
    
    Args:
        container: Container name
    
    Returns:
        Success or error message
    """
    result = shell_exec(f"docker start {container}")
    if "Error" not in result:
        return f"✅ Started: {container}"
    return result

# =============================================================================
# OPS MANAGEMENT (Mutual Administration)
# =============================================================================
@mcp.tool()
def rebuild_ops() -> str:
    """
    Full rebuild of super-claude-ops container.
    Stops, removes, rebuilds image, and restarts.
    
    This is the mutual administration capability - super-claude can rebuild ops,
    and ops can rebuild super-claude.
    """
    steps = ["🔧 Rebuilding Ops from Super Claude...", ""]
    
    # Step 1: Build new image
    steps.append("1️⃣ Building image...")
    success, output = _run_command("docker build -t super-claude-ops -f mcps/ops/Dockerfile .", timeout=300)
    if not success:
        return "\n".join(steps) + f"\n❌ Build failed:\n{output}"
    steps.append("   ✅ Image built")
    
    # Step 2: Stop and remove old container
    steps.append("2️⃣ Stopping old container...")
    _run_command("docker stop super-claude-ops")
    _run_command("docker rm super-claude-ops")
    steps.append("   ✅ Stopped and removed")
    
    # Step 3: Start new container with network
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
# MAIN
# =============================================================================
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
