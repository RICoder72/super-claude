#!/bin/bash
# Deploy Auth MCP
# Run from /volume1/docker/claude/

set -e

MCP_NAME="claude-auth"
PORT=8000

echo "Building $MCP_NAME..."
docker build -f mcps/auth/Dockerfile -t $MCP_NAME .

echo "Stopping existing container (if any)..."
docker stop $MCP_NAME 2>/dev/null || true
docker rm $MCP_NAME 2>/dev/null || true

# Also stop the old tracer if it's still running
docker stop super-claude-tracer 2>/dev/null || true
docker rm super-claude-tracer 2>/dev/null || true

echo "Starting $MCP_NAME..."
docker run -d \
  --name $MCP_NAME \
  -p $PORT:8000 \
  --env-file config/.env \
  --restart unless-stopped \
  $MCP_NAME

echo "Done! $MCP_NAME running on port $PORT"
echo ""
echo "Test with: curl http://localhost:$PORT/mcp"
echo "Logs: docker logs $MCP_NAME"
