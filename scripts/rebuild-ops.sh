#!/bin/bash
# =============================================================================
# Rebuild Super Claude Ops Container
# =============================================================================
# Rebuilds from git-tracked source in /data/mcps/ops/
#
# Usage: ./rebuild-ops.sh [--no-cache]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")"
cd "$DATA_DIR"

LOG="$DATA_DIR/temp/rebuild-ops.log"
NETWORK="super-claude_super-claude-net"

# Parse args
NO_CACHE=""
if [ "$1" = "--no-cache" ]; then
    NO_CACHE="--no-cache"
    echo "🔧 Rebuilding with --no-cache"
fi

# Ensure temp dir exists
mkdir -p "$DATA_DIR/temp"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# Clear previous log
echo "" > "$LOG"
log "🔧 Starting Super Claude Ops rebuild..."
log "   Source: $DATA_DIR/mcps/ops/"

# Step 1: Build new image
log "1️⃣ Building image..."
if docker build $NO_CACHE -t super-claude-ops -f mcps/ops/Dockerfile . >> "$LOG" 2>&1; then
    log "   ✅ Image built"
else
    log "   ❌ Build failed - check $LOG"
    exit 1
fi

# Step 2: Stop and remove old container
log "2️⃣ Stopping old container..."
docker stop super-claude-ops >> "$LOG" 2>&1 || true
docker rm super-claude-ops >> "$LOG" 2>&1 || true
log "   ✅ Stopped and removed"

# Step 3: Start new container
log "3️⃣ Starting new container..."
if docker run -d \
    --name super-claude-ops \
    --network "$NETWORK" \
    --env-file "$DATA_DIR/config/.env" \
    -p 8001:8001 \
    -v /volume1/docker/super-claude:/data \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --restart unless-stopped \
    super-claude-ops >> "$LOG" 2>&1; then
    log "   ✅ Started"
else
    log "   ❌ Run failed - check $LOG"
    exit 1
fi

log ""
log "✅ Super Claude Ops rebuilt successfully!"
log ""
log "Container: super-claude-ops"
log "Port: 8001"
log "MCP endpoint: http://localhost:8001/ops"
