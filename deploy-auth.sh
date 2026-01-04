#!/bin/bash
# Deploy Super Claude with OAuth Authentication
# Pulls JWT secret from 1Password at deploy time

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔐 Super Claude OAuth Deployment${NC}"
echo "=================================================="

cd /volume1/docker/super-claude

# Check for 1Password CLI
if ! command -v op &> /dev/null; then
    echo -e "${YELLOW}⚠️  1Password CLI not found - installing...${NC}"
    # For Synology, we'll use a different approach - the Python SDK in a helper script
fi

# Fetch JWT secret from 1Password using Python SDK (already available in MCP container)
echo -e "${YELLOW}🔑 Fetching JWT secret from 1Password...${NC}"

# Create a temporary Python script to fetch the secret
cat > /tmp/fetch_jwt_secret.py << 'EOF'
import asyncio
import os
import sys

sys.path.insert(0, "/volume1/docker/super-claude/shared")

async def main():
    # Set the token from the env file
    with open("/volume1/docker/super-claude/config/.env") as f:
        for line in f:
            if line.startswith("OP_SERVICE_ACCOUNT_TOKEN="):
                os.environ["OP_SERVICE_ACCOUNT_TOKEN"] = line.strip().split("=", 1)[1]
                break
    
    from op_client import get_secret
    secret = await get_secret("Super Claude JWT Secret", "credential", "Key Vault")
    print(secret)

asyncio.run(main())
EOF

# We need to run this inside a container that has the 1Password SDK
JWT_SECRET=$(docker run --rm \
    -v /volume1/docker/super-claude:/data \
    -e OP_SERVICE_ACCOUNT_TOKEN="$(grep OP_SERVICE_ACCOUNT_TOKEN /volume1/docker/super-claude/config/.env | cut -d= -f2)" \
    --entrypoint python \
    super-claude \
    -c "
import asyncio
import os
import sys
sys.path.insert(0, '/data/shared')
from op_client import get_secret
async def main():
    secret = await get_secret('Super Claude JWT Secret', 'credential', 'Key Vault')
    print(secret, end='')
asyncio.run(main())
" 2>/dev/null)

if [ -z "$JWT_SECRET" ]; then
    echo -e "${RED}❌ Failed to fetch JWT secret from 1Password${NC}"
    echo "Make sure 'Super Claude JWT Secret' exists in Key Vault"
    exit 1
fi

echo -e "${GREEN}✅ JWT secret retrieved${NC}"

# Write the auth environment file
echo -e "${YELLOW}⚙️  Writing auth configuration...${NC}"
cat > config/.env.auth << EOF
# JWT Authentication Configuration (auto-generated)
# Source: 1Password - Key Vault / Super Claude JWT Secret
JWT_SECRET=${JWT_SECRET}
JWT_ISSUER=super-claude
JWT_AUDIENCE=super-claude-mcp
EOF

echo -e "${GREEN}✅ Auth configuration written${NC}"

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

# Build and start with auth
echo -e "${YELLOW}🏗️  Building and starting with OAuth...${NC}"
docker-compose -f docker-compose-auth.yml up -d --build

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services...${NC}"
sleep 5

# Check health
echo -e "${YELLOW}🔍 Checking service health...${NC}"

if curl -sf http://localhost:8080/health > /dev/null; then
    echo -e "${GREEN}✅ Router healthy${NC}"
else
    echo -e "${RED}❌ Router not responding${NC}"
fi

if docker exec super-claude-auth wget -q --spider http://localhost:3000/health; then
    echo -e "${GREEN}✅ Auth service healthy${NC}"
else
    echo -e "${RED}❌ Auth service not responding${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Generate a token: node auth-service/jwt-utils.js generate claude-user 'read,write,admin' 180d"
echo "2. Update your Claude MCP configuration with the token"
echo "3. Test: curl -H 'Authorization: Bearer <token>' https://zanni.synology.me/mcp"
