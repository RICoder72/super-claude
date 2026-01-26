#!/bin/bash
# Background rebuild script for super-claude container
# Logs to /data/temp/rebuild.log

set -e

LOG="/data/temp/rebuild.log"
NETWORK="super-claude_super-claude-net"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# Clear previous log
echo "" > "$LOG"
log "🔨 Starting Super Claude rebuild..."

# Step 1: Build new image
log "1️⃣ Building image..."
if docker build -t super-claude -f /data/mcps/super-claude/Dockerfile /data >> "$LOG" 2>&1; then
    log "   ✅ Image built"
else
    log "   ❌ Build failed"
    exit 1
fi

# Step 2: Stop and remove old container
log "2️⃣ Stopping old container..."
docker stop super-claude >> "$LOG" 2>&1 || true
docker rm super-claude >> "$LOG" 2>&1 || true
log "   ✅ Stopped and removed"

# Step 3: Start new container
log "3️⃣ Starting new container..."
if docker run -d \
    --name super-claude \
    --network "$NETWORK" \
    --env-file /data/config/.env \
    -p 8000:8000 \
    -v /volume1/docker/super-claude:/data \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --restart unless-stopped \
    super-claude >> "$LOG" 2>&1; then
    log "   ✅ Started"
else
    log "   ❌ Run failed"
    exit 1
fi

log ""
log "✅ Super Claude rebuilt successfully!"
log ""
log "⚠️  Remember: Disconnect and reconnect the Super Claude connector, then start a new chat."
