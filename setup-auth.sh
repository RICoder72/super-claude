#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Super Claude Authentication Setup${NC}"
echo "=================================================="

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed${NC}"
    echo "Please install Node.js and try again"
    exit 1
fi

# Install auth service dependencies
echo -e "${YELLOW}📦 Installing auth service dependencies...${NC}"
cd auth-service
npm install
cd ..

# Generate a secure JWT secret
echo -e "${YELLOW}🔑 Generating secure JWT secret...${NC}"
cd auth-service
SECRET=$(node jwt-utils.js secret | tail -1)
cd ..

# Create environment configuration
echo -e "${YELLOW}⚙️ Creating environment configuration...${NC}"
cat > config/.env.auth << EOF
# JWT Authentication Configuration
JWT_SECRET=$SECRET
JWT_ISSUER=super-claude
JWT_AUDIENCE=super-claude-mcp
EOF

echo -e "${GREEN}✅ Environment configuration created${NC}"

# Generate a test token for immediate use
echo -e "${YELLOW}🎫 Generating test token...${NC}"
cd auth-service
TOKEN=$(node jwt-utils.js generate claude-user "read,write,admin" 24h | grep "Token:" | cut -d' ' -f2)
cd ..

# Create a quick start guide
cat > AUTH_SETUP_COMPLETE.md << EOF
# 🔐 Super Claude Authentication Setup Complete!

## 🚀 Quick Start

### 1. Deploy with Authentication
\`\`\`bash
# Stop current services (if running)
docker-compose down

# Start with authentication
docker-compose -f docker-compose-auth.yml up -d
\`\`\`

### 2. Test Token (Valid for 24 hours)
\`\`\`
$TOKEN
\`\`\`

### 3. Configure Claude MCP
Add this to your Claude MCP configuration:
\`\`\`json
{
  "type": "url",
  "url": "https://your-domain.com:8080/mcp",
  "name": "super-claude",
  "authorization_token": "$TOKEN"
}
\`\`\`

## 🔧 Token Management

### Generate New Tokens
\`\`\`bash
# Basic token (1 hour, read/write)
node auth-service/jwt-utils.js generate

# Custom token
node auth-service/jwt-utils.js generate "user-id" "read,write,admin" "7d"
\`\`\`

### Verify Tokens
\`\`\`bash
node auth-service/jwt-utils.js verify <token>
\`\`\`

## 📋 OAuth Endpoints

- Protected Resource Metadata: \`https://your-domain.com:8080/.well-known/oauth-protected-resource\`
- Authorization Server Metadata: \`https://your-domain.com:8080/.well-known/oauth-authorization-server\`
- Token Generation: \`https://your-domain.com:8080/token\`

## 🔒 Security Notes

- JWT secret is stored in \`config/.env.auth\`
- Tokens include user ID, scope, and expiration
- All MCP endpoints now require valid bearer tokens
- OAuth 2.1 compliant error responses

## 🧪 Testing

Run the test script to verify everything works:
\`\`\`bash
chmod +x test-auth.sh
./test-auth.sh
\`\`\`
EOF

echo ""
echo -e "${GREEN}🎉 Authentication setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo -e "✅ JWT secret generated and saved to config/.env.auth"
echo -e "✅ Auth service configured with Node.js"
echo -e "✅ OAuth 2.1 compliant endpoints ready"
echo -e "✅ Test token generated (valid 24h): ${TOKEN:0:50}..."
echo ""
echo -e "${YELLOW}📖 See AUTH_SETUP_COMPLETE.md for detailed instructions${NC}"
echo ""
echo -e "${BLUE}🚀 Ready to deploy? Run:${NC}"
echo -e "   ${GREEN}docker-compose -f docker-compose-auth.yml up -d${NC}"
