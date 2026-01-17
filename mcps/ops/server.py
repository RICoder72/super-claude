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
    steps = ["🔨 Rebuilding Super Claude...", ""]
    
    # Step 1: Build new image
    steps.append("1️⃣ Building image...")
    success, output = _run("docker build -t super-claude -f mcps/super-claude/Dockerfile .", timeout=300)
    if not success:
        return "\n".join(steps) + f"\n❌ Build failed:\n{output}"
    steps.append("   ✅ Image built")
    
    # Step 2: Stop and remove old container
    steps.append("2️⃣ Stopping old container...")
    _run("docker stop super-claude")
    _run("docker rm super-claude")
    steps.append("   ✅ Stopped and removed")
    
    # Step 3: Start new container with network
    steps.append("3️⃣ Starting new container...")
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
    if not success:
        return "\n".join(steps) + f"\n❌ Run failed:\n{output}"
    steps.append("   ✅ Started")
    
    steps.append("")
    steps.append("✅ Super Claude rebuilt successfully!")
    steps.append("")
    steps.append("⚠️  Remember: Disconnect and reconnect the Super Claude connector, then start a new chat.")
    
    return "\n".join(steps)

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
