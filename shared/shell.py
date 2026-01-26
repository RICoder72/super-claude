"""
Shared shell execution utilities for Super Claude MCPs.

Provides a unified shell execution function with safety guards.
"""

import subprocess
import re
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# Commands/patterns that should be blocked for safety
# These could cause serious damage if executed accidentally
BLOCKED_PATTERNS = [
    r'\brm\s+-rf\s+/',           # rm -rf /
    r'\brm\s+-rf\s+~',           # rm -rf ~
    r'\brm\s+-rf\s+\*',          # rm -rf *
    r'\brmdir\s+/',              # rmdir /
    r'>\s*/dev/sd',              # Writing to raw disk
    r'\bmkfs\b',                 # Formatting filesystems
    r'\bdd\s+.*of=/',            # dd to system paths
    r'\bdocker\s+system\s+prune', # Docker system prune
    r'\bdocker\s+rm\s+-f\s+\$',  # docker rm -f $(...)  
    r':(){.*};:',                # Fork bomb
]

# Container names that should not be stopped/removed via shell
# Note: These are checked with word boundaries to avoid false positives
# (e.g., "super-claude" shouldn't block "super-claude-ops")
PROTECTED_CONTAINERS = [
    'super-claude-ops',      # Longer names first to match precisely
    'super-claude-router',
    'super-claude-auth',
    'super-claude',          # Base name last
]


def is_command_blocked(command: str) -> Tuple[bool, str]:
    """
    Check if a command matches any blocked pattern.
    
    Args:
        command: Shell command to check
        
    Returns:
        Tuple of (is_blocked, reason)
    """
    command_lower = command.lower()
    
    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command_lower):
            return True, f"Command matches blocked pattern: {pattern}"
    
    # Check for attempts to stop/rm protected containers
    # Use regex with word boundary to avoid false positives
    for container in PROTECTED_CONTAINERS:
        # Pattern matches: docker stop <container> (with word boundary after)
        stop_pattern = rf'\bdocker\s+stop\s+{re.escape(container)}(?:\s|$|;|&|\|)'
        rm_pattern = rf'\bdocker\s+rm\s+{re.escape(container)}(?:\s|$|;|&|\|)'
        
        if re.search(stop_pattern, command_lower):
            return True, f"Cannot stop protected container: {container}"
        if re.search(rm_pattern, command_lower):
            return True, f"Cannot remove protected container: {container}"
    
    return False, ""


def run_shell(
    command: str,
    timeout: int = 30,
    cwd: Path = None,
    check_blocked: bool = True
) -> Tuple[bool, str]:
    """
    Execute a shell command safely.
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory (default: /data)
        check_blocked: Whether to check against blocked patterns (default: True)
        
    Returns:
        Tuple of (success, output)
    """
    from config import SUPER_CLAUDE_ROOT
    
    if cwd is None:
        cwd = SUPER_CLAUDE_ROOT
    
    # Safety check
    if check_blocked:
        blocked, reason = is_command_blocked(command)
        if blocked:
            logger.warning(f"Blocked command: {command} - {reason}")
            return False, f"❌ Command blocked for safety: {reason}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd)
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
            
        return result.returncode == 0, output.strip() or "(no output)"
        
    except subprocess.TimeoutExpired:
        return False, f"❌ Command timed out after {timeout}s"
    except Exception as e:
        return False, f"❌ Error: {e}"


def run_shell_simple(command: str, timeout: int = 30) -> str:
    """
    Execute a shell command and return just the output string.
    
    This is a convenience wrapper that returns a single string,
    suitable for direct use as an MCP tool return value.
    
    Args:
        command: Shell command to execute
        timeout: Timeout in seconds
        
    Returns:
        Output string (includes error info if failed)
    """
    success, output = run_shell(command, timeout)
    return output
