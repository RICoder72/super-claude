"""
Super Claude MCP Server

Central MCP providing:
- Auth: 1Password secret retrieval
- Filesystem: Read, write, delete, move files within sandbox
- Shell: Execute commands
- Docker: Container management
"""

from fastmcp import FastMCP
import subprocess
from pathlib import Path

# Import 1Password helper
import sys
sys.path.insert(0, "/app/shared")
from op_client import get_secret, get_secret_by_ref

mcp = FastMCP("Super Claude")

# =============================================================================
# CONFIG
# =============================================================================
SUPER_CLAUDE_ROOT = Path("/data")  # Mounted volume: /volume1/docker/super-claude

# =============================================================================
# HEALTH
# =============================================================================
@mcp.tool()
def ping() -> str:
    """Health check. Returns pong if the auth MCP is running."""
    return "pong from Super Claude 🚀"

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
# MAIN
# =============================================================================
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
