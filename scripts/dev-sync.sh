#!/bin/bash
# =============================================================================
# Quick Sync for Development
# =============================================================================
# For development: copies changed files into running container without rebuild
# Useful when you're iterating quickly and don't want to wait for docker build
#
# Usage: ./dev-sync.sh [super-claude|ops|both]
#
# NOTE: Changes are lost on container restart! This is just for quick testing.
# Always do a proper rebuild when changes are finalized.
# =============================================================================

set -e

sync_super_claude() {
    echo "📦 Syncing super-claude..."
    
    # Copy server.py
    docker cp /data/mcps/super-claude/server.py super-claude:/app/server.py
    
    # Copy plugins
    docker cp /data/mcps/super-claude/plugins/. super-claude:/app/plugins/
    
    # Copy core modules
    docker cp /data/mcps/super-claude/core/. super-claude:/app/core/
    
    # Copy services
    docker cp /data/mcps/super-claude/services/. super-claude:/app/services/
    
    # Copy shared
    docker cp /data/shared/. super-claude:/app/shared/
    
    echo "   ✅ Files synced"
    echo "   Restarting container..."
    docker restart super-claude
    echo "   ✅ Restarted"
}

sync_ops() {
    echo "🔧 Syncing super-claude-ops..."
    
    # Copy server.py
    docker cp /data/mcps/ops/server.py super-claude-ops:/app/server.py
    
    # Copy shared
    docker cp /data/shared/. super-claude-ops:/app/shared/
    
    echo "   ✅ Files synced"
    echo "   Restarting container..."
    docker restart super-claude-ops
    echo "   ✅ Restarted"
}

TARGET="${1:-both}"

case "$TARGET" in
    super-claude|sc|main)
        sync_super_claude
        ;;
    ops)
        sync_ops
        ;;
    both|all)
        sync_ops
        sync_super_claude
        ;;
    *)
        echo "Usage: $0 [super-claude|ops|both]"
        exit 1
        ;;
esac

echo ""
echo "⚠️  Remember: This is temporary! Do a proper rebuild when done."
echo "⚠️  Start a new Claude chat to reconnect."
