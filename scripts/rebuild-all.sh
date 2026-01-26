#!/bin/bash
# =============================================================================
# Rebuild All Super Claude Containers
# =============================================================================
# Rebuilds both super-claude and super-claude-ops from git-tracked source
#
# Usage: ./rebuild-all.sh [--no-cache]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔨 Rebuilding all Super Claude containers..."
echo ""

# Rebuild ops first (so it can still manage things if super-claude fails)
"$SCRIPT_DIR/rebuild-ops.sh" "$@"
echo ""

# Then rebuild main
"$SCRIPT_DIR/rebuild-super-claude.sh" "$@"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "✅ All containers rebuilt!"
echo ""
echo "  super-claude     → http://localhost:8000/mcp"
echo "  super-claude-ops → http://localhost:8001/ops"
echo ""
echo "⚠️  Start a new Claude chat to reconnect to MCPs"
echo "═══════════════════════════════════════════════════════════"
