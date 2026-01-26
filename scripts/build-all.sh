#!/bin/bash
# Build all Super Claude containers using docker-compose
# This is the canonical way to build everything

set -e
cd /data

echo "🔨 Building all Super Claude containers..."
docker-compose build

echo ""
echo "✅ All images built!"
echo ""
echo "To start/restart: ./scripts/start-all.sh"
echo "To rebuild and restart: ./scripts/rebuild-all.sh"
