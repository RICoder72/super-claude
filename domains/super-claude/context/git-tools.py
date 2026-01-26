"""
Git Tools for Super Claude

Core git operations available to Claude.
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


def _run_git(args: list, cwd: Path = None, timeout: int = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n" + result.stderr.strip() if output else result.stderr.strip()
        
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


async def git_clone(url: str, path: str = None, branch: str = None, depth: int = None) -> str:
    """
    Clone a git repository.
    
    Args:
        url: Repository URL (HTTPS or SSH)
        path: Local path to clone to (default: repo name in /data/repos/)
        branch: Branch to clone (default: default branch)
        depth: Shallow clone depth (default: full clone)
    
    Returns:
        Status message with clone location
    """
    # Determine target path
    if path is None:
        repo_name = url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        path = f"/data/repos/{repo_name}"
    
    target = Path(path)
    if target.exists():
        return f"❌ Path already exists: {path}"
    
    # Build clone command
    args = ["clone"]
    if branch:
        args.extend(["--branch", branch])
    if depth:
        args.extend(["--depth", str(depth)])
    args.extend([url, str(target)])
    
    success, output = _run_git(args, timeout=120)
    
    if success:
        return f"✅ Cloned to: {path}\n\n{output}"
    return f"❌ Clone failed: {output}"


async def git_status(path: str) -> str:
    """
    Show git status for a repository.
    
    Args:
        path: Path to repository
    
    Returns:
        Git status output
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    success, output = _run_git(["status"], cwd=repo)
    
    if success:
        return f"📊 Git Status: {path}\n{'─' * 40}\n{output}"
    return f"❌ Status failed: {output}"


async def git_pull(path: str, remote: str = "origin", branch: str = None) -> str:
    """
    Pull latest changes from remote.
    
    Args:
        path: Path to repository
        remote: Remote name (default: origin)
        branch: Branch to pull (default: current branch)
    
    Returns:
        Pull result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    args = ["pull", remote]
    if branch:
        args.append(branch)
    
    success, output = _run_git(args, cwd=repo)
    
    if success:
        return f"✅ Pull complete\n\n{output}"
    return f"❌ Pull failed: {output}"


async def git_push(path: str, remote: str = "origin", branch: str = None) -> str:
    """
    Push commits to remote.
    
    Args:
        path: Path to repository
        remote: Remote name (default: origin)
        branch: Branch to push (default: current branch)
    
    Returns:
        Push result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    args = ["push", remote]
    if branch:
        args.append(branch)
    
    success, output = _run_git(args, cwd=repo, timeout=120)
    
    if success:
        return f"✅ Push complete\n\n{output}"
    return f"❌ Push failed: {output}"


async def git_commit(path: str, message: str, add_all: bool = True) -> str:
    """
    Commit changes to repository.
    
    Args:
        path: Path to repository
        message: Commit message
        add_all: Stage all changes before commit (default: True)
    
    Returns:
        Commit result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    if add_all:
        success, output = _run_git(["add", "-A"], cwd=repo)
        if not success:
            return f"❌ Add failed: {output}"
    
    success, output = _run_git(["commit", "-m", message], cwd=repo)
    
    if success:
        return f"✅ Committed\n\n{output}"
    if "nothing to commit" in output:
        return f"ℹ️ Nothing to commit\n\n{output}"
    return f"❌ Commit failed: {output}"


async def git_log(path: str, count: int = 10, oneline: bool = True) -> str:
    """
    Show commit history.
    
    Args:
        path: Path to repository
        count: Number of commits to show (default: 10)
        oneline: Use one-line format (default: True)
    
    Returns:
        Commit log
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    args = ["log", f"-{count}"]
    if oneline:
        args.append("--oneline")
    
    success, output = _run_git(args, cwd=repo)
    
    if success:
        return f"📜 Git Log: {path}\n{'─' * 40}\n{output}"
    return f"❌ Log failed: {output}"


async def git_diff(path: str, staged: bool = False) -> str:
    """
    Show changes in repository.
    
    Args:
        path: Path to repository
        staged: Show staged changes only (default: False)
    
    Returns:
        Diff output
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    args = ["diff"]
    if staged:
        args.append("--staged")
    
    success, output = _run_git(args, cwd=repo)
    
    if success:
        if not output:
            return "ℹ️ No changes"
        return f"📝 Diff:\n{'─' * 40}\n{output}"
    return f"❌ Diff failed: {output}"


async def git_branch(path: str, name: str = None, delete: bool = False) -> str:
    """
    List, create, or delete branches.
    
    Args:
        path: Path to repository
        name: Branch name to create/delete (omit to list)
        delete: Delete the branch instead of creating
    
    Returns:
        Branch operation result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    if name is None:
        # List branches
        success, output = _run_git(["branch", "-a"], cwd=repo)
        if success:
            return f"🌿 Branches:\n{'─' * 40}\n{output}"
        return f"❌ Failed: {output}"
    
    if delete:
        success, output = _run_git(["branch", "-d", name], cwd=repo)
        if success:
            return f"✅ Deleted branch: {name}"
        return f"❌ Delete failed: {output}"
    
    # Create branch
    success, output = _run_git(["branch", name], cwd=repo)
    if success:
        return f"✅ Created branch: {name}"
    return f"❌ Create failed: {output}"


async def git_checkout(path: str, target: str, create: bool = False) -> str:
    """
    Switch branches or restore files.
    
    Args:
        path: Path to repository
        target: Branch name or file path
        create: Create new branch (default: False)
    
    Returns:
        Checkout result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(target)
    
    success, output = _run_git(args, cwd=repo)
    
    if success:
        return f"✅ Switched to: {target}\n\n{output}"
    return f"❌ Checkout failed: {output}"


async def git_remote(path: str, name: str = None, url: str = None, remove: bool = False) -> str:
    """
    Manage remotes.
    
    Args:
        path: Path to repository
        name: Remote name (omit to list all)
        url: URL to add/set (omit to show URL)
        remove: Remove the remote
    
    Returns:
        Remote operation result
    """
    repo = Path(path)
    if not (repo / ".git").exists():
        return f"❌ Not a git repository: {path}"
    
    if name is None:
        # List remotes
        success, output = _run_git(["remote", "-v"], cwd=repo)
        if success:
            return f"🔗 Remotes:\n{'─' * 40}\n{output or '(none)'}"
        return f"❌ Failed: {output}"
    
    if remove:
        success, output = _run_git(["remote", "remove", name], cwd=repo)
        if success:
            return f"✅ Removed remote: {name}"
        return f"❌ Remove failed: {output}"
    
    if url:
        # Check if remote exists
        success, _ = _run_git(["remote", "get-url", name], cwd=repo)
        if success:
            # Update existing
            success, output = _run_git(["remote", "set-url", name, url], cwd=repo)
            action = "Updated"
        else:
            # Add new
            success, output = _run_git(["remote", "add", name, url], cwd=repo)
            action = "Added"
        
        if success:
            return f"✅ {action} remote: {name} → {url}"
        return f"❌ Failed: {output}"
    
    # Show URL
    success, output = _run_git(["remote", "get-url", name], cwd=repo)
    if success:
        return f"🔗 {name}: {output}"
    return f"❌ Remote not found: {name}"


async def git_init(path: str, bare: bool = False) -> str:
    """
    Initialize a new git repository.
    
    Args:
        path: Path for new repository
        bare: Create bare repository (default: False)
    
    Returns:
        Init result
    """
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    
    args = ["init"]
    if bare:
        args.append("--bare")
    
    success, output = _run_git(args, cwd=target)
    
    if success:
        return f"✅ Initialized repository: {path}\n\n{output}"
    return f"❌ Init failed: {output}"


async def git_config(path: str, key: str, value: str = None, global_config: bool = False) -> str:
    """
    Get or set git config.
    
    Args:
        path: Path to repository (ignored if global)
        key: Config key (e.g., "user.email")
        value: Value to set (omit to get current value)
        global_config: Use global config instead of repo
    
    Returns:
        Config operation result
    """
    repo = Path(path) if not global_config else None
    
    args = ["config"]
    if global_config:
        args.append("--global")
    
    if value is None:
        # Get value
        args.append(key)
        success, output = _run_git(args, cwd=repo)
        if success:
            return f"{key} = {output}"
        return f"ℹ️ {key} not set"
    
    # Set value
    args.extend([key, value])
    success, output = _run_git(args, cwd=repo)
    
    if success:
        return f"✅ Set {key} = {value}"
    return f"❌ Config failed: {output}"


# Tool registration
GIT_TOOLS = {
    "git_clone": git_clone,
    "git_status": git_status,
    "git_pull": git_pull,
    "git_push": git_push,
    "git_commit": git_commit,
    "git_log": git_log,
    "git_diff": git_diff,
    "git_branch": git_branch,
    "git_checkout": git_checkout,
    "git_remote": git_remote,
    "git_init": git_init,
    "git_config": git_config,
}
