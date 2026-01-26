"""
Super Claude Ops MCP Server

Administrative MCP for managing Super Claude infrastructure.
Provides rebuild, backup, and monitoring capabilities.

Key capability: Can rebuild the main super-claude container,
while super-claude can rebuild this one. Mutual administration.
"""

from fastmcp import FastMCP
import subprocess
from pathlib import Path
from datetime import datetime
import sys

# =============================================================================
# SHARED MODULE IMPORTS
# =============================================================================
sys.path.insert(0, "/app/shared")
sys.path.insert(0, "/data/shared")

try:
    from config import SUPER_CLAUDE_ROOT, BACKUPS_DIR, DOCKER_NETWORK
    from shell import run_shell
    SHARED_MODULES_AVAILABLE = True
except ImportError:
    SHARED_MODULES_AVAILABLE = False
    SUPER_CLAUDE_ROOT = Path("/data")
    BACKUPS_DIR = SUPER_CLAUDE_ROOT / "backups"
    DOCKER_NETWORK = "super-claude_super-claude-net"

mcp = FastMCP("Super Claude Ops")

# =============================================================================
# HELPERS
# =============================================================================
def _run(command: str, timeout: int = 120) -> tuple[bool, str]:
    """Run shell command, return (success, output)"""
    if SHARED_MODULES_AVAILABLE:
        return run_shell(command, timeout, cwd=SUPER_CLAUDE_ROOT, check_blocked=False)
    
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

def _validate_path(path: str) -> Path:
    """
    Validate and resolve path within sandbox.
    Raises ValueError if path escapes sandbox.
    """
    # Resolve relative to SUPER_CLAUDE_ROOT
    if path.startswith("/"):
        full_path = Path(path)
    else:
        full_path = SUPER_CLAUDE_ROOT / path
    
    # Resolve to absolute and check it's within sandbox
    resolved = full_path.resolve()
    if not str(resolved).startswith(str(SUPER_CLAUDE_ROOT.resolve())):
        raise ValueError(f"Path outside sandbox: {path}")
    
    return resolved

# =============================================================================
# HEALTH
# =============================================================================
@mcp.tool()
def ping() -> str:
    """Health check. Returns pong if Ops MCP is running."""
    return "pong from Super Claude Ops 🔧"

@mcp.tool()
def status() -> str:
    """Get status of both containers."""
    success, output = _run("docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'super-claude'")
    if not success or not output:
        return "❌ Could not get container status"
    
    lines = ["📊 Container Status", "─" * 40]
    for line in output.strip().split("\n"):
        if line:
            lines.append(f"  {line}")
    return "\n".join(lines)

# =============================================================================
# SUPER CLAUDE MANAGEMENT
# =============================================================================
@mcp.tool()
def rebuild_super_claude() -> str:
    """
    Full rebuild of super-claude container.
    Stops, removes, rebuilds image, and restarts with correct mounts.
    """
    # Ensure temp directory exists
    temp_dir = SUPER_CLAUDE_ROOT / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Make script executable and run in background
    script_path = SUPER_CLAUDE_ROOT / "scripts" / "rebuild-super-claude.sh"
    _run(f"chmod +x {script_path}", timeout=5)
    
    # Launch in background with nohup
    success, output = _run(f"nohup {script_path} > /dev/null 2>&1 &", timeout=5)
    
    if not success:
        return f"❌ Failed to start rebuild:\n{output}"
    
    return """🔨 Rebuild started in background!

Monitor progress with: `rebuild_status()`
Or check logs with: `logs_super_claude()`

⚠️  When complete, start a new chat to reconnect."""

@mcp.tool()
def rebuild_status() -> str:
    """Check the status of a background rebuild."""
    log_path = SUPER_CLAUDE_ROOT / "temp" / "rebuild.log"
    
    if not log_path.exists():
        return "📋 No rebuild log found. No rebuild in progress or log was cleared."
    
    content = log_path.read_text()
    if not content.strip():
        return "📋 Rebuild log is empty. Rebuild may be starting..."
    
    # Check if complete
    if "✅ Super Claude rebuilt successfully!" in content:
        status = "✅ COMPLETE"
    elif "❌" in content.split("\n")[-5:]:  # Check last 5 lines for errors
        status = "❌ FAILED"
    else:
        status = "🔄 IN PROGRESS"
    
    lines = content.strip().split("\n")
    recent = "\n".join(lines[-15:])  # Last 15 lines
    
    return f"📋 Rebuild Status: {status}\n{'─' * 40}\n{recent}"

# =============================================================================
# SUPER CLAUDE MANAGEMENT - INDIVIDUAL STEPS
# =============================================================================
@mcp.tool()
def build_super_claude_image() -> str:
    """
    Build the super-claude Docker image without stopping the container.
    Use this to pre-build before a quick restart.
    """
    success, output = _run(
        "docker build -t super-claude -f mcps/super-claude/Dockerfile .", 
        timeout=300
    )
    if success:
        return "✅ Image built successfully!\n\nNext steps:\n1. stop_super_claude()\n2. start_super_claude()"
    return f"❌ Build failed:\n{output}"

@mcp.tool()
def stop_super_claude() -> str:
    """Stop and remove the super-claude container."""
    _run("docker stop super-claude", timeout=30)
    success, output = _run("docker rm super-claude", timeout=10)
    
    # Verify it's gone
    check_success, check_output = _run("docker ps -a --filter name=super-claude --format '{{.Names}}'")
    if "super-claude" not in check_output:
        return "✅ Super Claude stopped and removed"
    return f"⚠️ Container may still exist:\n{check_output}"

@mcp.tool()
def start_super_claude() -> str:
    """
    Start the super-claude container from the existing image.
    Use after stop_super_claude() or after building a new image.
    """
    run_cmd = f"""docker run -d \
        --name super-claude \
        --network {DOCKER_NETWORK} \
        --env-file /data/config/.env \
        -p 8000:8000 \
        -v /volume1/docker/super-claude:/data \
        -v /var/run/docker.sock:/var/run/docker.sock \
        --restart unless-stopped \
        super-claude"""
    
    success, output = _run(run_cmd)
    if success:
        return "✅ Super Claude started!\n\n⚠️  Start a new chat to reconnect."
    return f"❌ Failed to start:\n{output}"

@mcp.tool()
def restart_super_claude() -> str:
    """Restart super-claude container without rebuilding."""
    success, output = _run("docker restart super-claude")
    if success:
        return "✅ Super Claude restarted\n\n⚠️  Remember: Start a new chat to reconnect."
    return f"❌ Restart failed:\n{output}"

@mcp.tool()
def logs_super_claude(lines: int = 50) -> str:
    """Get recent logs from super-claude container."""
    success, output = _run(f"docker logs --tail {lines} super-claude")
    if success:
        return f"📋 Super Claude Logs (last {lines} lines):\n{'─' * 40}\n{output}"
    return f"❌ Could not get logs:\n{output}"

# =============================================================================
# FILE OPERATIONS
# =============================================================================
@mcp.tool()
def fs_read(path: str) -> str:
    """
    Read file contents from the super-claude repo.
    Use this when super-claude container is down and you need to inspect/fix files.
    
    Args:
        path: Path relative to repo root (or absolute within /data)
    """
    try:
        resolved = _validate_path(path)
        if not resolved.exists():
            return f"❌ File not found: {path}"
        if not resolved.is_file():
            return f"❌ Not a file: {path}"
        
        content = resolved.read_text()
        return f"📄 {path}\n{'─' * 40}\n{content}"
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error reading file: {e}"

@mcp.tool()
def fs_write(path: str, content: str) -> str:
    """
    Write content to a file. Creates parent directories if needed.
    Use this when super-claude container is down and you need to fix files.
    
    Args:
        path: Path relative to repo root (or absolute within /data)
        content: Content to write
    """
    try:
        resolved = _validate_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
        return f"✅ Wrote {len(content)} bytes to {path}"
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error writing file: {e}"

@mcp.tool()
def fs_list(path: str = ".") -> str:
    """
    List directory contents.
    
    Args:
        path: Path relative to repo root (default: repo root)
    """
    try:
        resolved = _validate_path(path)
        if not resolved.exists():
            return f"❌ Path not found: {path}"
        if not resolved.is_dir():
            return f"❌ Not a directory: {path}"
        
        lines = [f"📂 {path}", "─" * 40]
        
        # Sort: directories first, then files
        items = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        
        for item in items:
            if item.name.startswith('.') and item.name not in ['.env', '.gitignore']:
                continue  # Skip hidden files except common ones
            
            if item.is_dir():
                lines.append(f"  📁 {item.name}/")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                lines.append(f"  📄 {item.name} ({size_str})")
        
        return "\n".join(lines)
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error listing directory: {e}"

@mcp.tool()
def fs_str_replace(path: str, old_str: str, new_str: str) -> str:
    """
    Replace a string in a file. The old_str must appear exactly once.
    Use this for surgical edits when super-claude is down.
    
    Args:
        path: Path to file
        old_str: String to find (must be unique in file)
        new_str: String to replace with
    """
    try:
        resolved = _validate_path(path)
        if not resolved.exists():
            return f"❌ File not found: {path}"
        if not resolved.is_file():
            return f"❌ Not a file: {path}"
        
        content = resolved.read_text()
        count = content.count(old_str)
        
        if count == 0:
            return f"❌ String not found in {path}"
        if count > 1:
            return f"❌ String appears {count} times in {path} (must be unique)"
        
        new_content = content.replace(old_str, new_str)
        resolved.write_text(new_content)
        
        return f"✅ Replaced in {path}"
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error: {e}"

# =============================================================================
# BACKUP & RESTORE
# =============================================================================
@mcp.tool()
def backup(name: str = "") -> str:
    """
    Backup domains and config to a timestamped archive.
    
    Args:
        name: Optional name suffix for the backup
    """
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{name}" if name else ""
    backup_name = f"backup_{timestamp}{suffix}.tar.gz"
    backup_path = BACKUPS_DIR / backup_name
    
    # Backup domains and config (not mcps/shared - those are in git)
    cmd = f"tar -czvf {backup_path} domains/ config/.env.example"
    success, output = _run(cmd)
    
    if success:
        # Get file size
        size = backup_path.stat().st_size
        size_mb = size / (1024 * 1024)
        return f"✅ Backup created: {backup_name} ({size_mb:.2f} MB)"
    return f"❌ Backup failed:\n{output}"

@mcp.tool()
def list_backups() -> str:
    """List available backups."""
    if not BACKUPS_DIR.exists():
        return "📁 No backups directory yet"
    
    backups = sorted(BACKUPS_DIR.glob("backup_*.tar.gz"), reverse=True)
    if not backups:
        return "📁 No backups found"
    
    lines = ["📁 Available Backups", "─" * 40]
    for b in backups[:20]:  # Last 20
        size = b.stat().st_size / (1024 * 1024)
        lines.append(f"  {b.name} ({size:.2f} MB)")
    
    return "\n".join(lines)

@mcp.tool()
def restore(backup_name: str) -> str:
    """
    Restore from a backup archive.
    
    Args:
        backup_name: Name of the backup file to restore
    
    WARNING: This will overwrite current domains!
    """
    backup_path = BACKUPS_DIR / backup_name
    if not backup_path.exists():
        return f"❌ Backup not found: {backup_name}"
    
    # Extract to root
    cmd = f"tar -xzvf {backup_path}"
    success, output = _run(cmd)
    
    if success:
        return f"✅ Restored from {backup_name}\n\n⚠️  You may need to restart containers for changes to take effect."
    return f"❌ Restore failed:\n{output}"

# =============================================================================
# GIT OPERATIONS
# =============================================================================
@mcp.tool()
def git_status() -> str:
    """Show git status of the super-claude repo."""
    success, output = _run("git status")
    if success:
        return f"📊 Git Status:\n{'─' * 40}\n{output}"
    return f"❌ Git error:\n{output}"

@mcp.tool()
def git_pull() -> str:
    """Pull latest changes from origin."""
    success, output = _run("git pull")
    if success:
        return f"✅ Git pull complete:\n{output}"
    return f"❌ Git pull failed:\n{output}"

@mcp.tool()
def git_push() -> str:
    """Push commits to origin."""
    success, output = _run("git push")
    if success:
        return f"✅ Git push complete:\n{output}"
    return f"❌ Git push failed:\n{output}"

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Serve on /ops path for path-based routing
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/ops")
