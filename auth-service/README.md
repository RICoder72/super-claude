# Super Claude Authentication Service

A lightweight JWT authentication service for securing Super Claude MCP endpoints with OAuth 2.1 compliance.

## Features

- 🔐 **JWT Bearer Token Authentication** - Industry standard token-based auth
- 🚀 **OAuth 2.1 Compliant** - Proper error responses and metadata endpoints
- 🔄 **Nginx Integration** - Uses auth_request for seamless proxy authentication
- 🎫 **Token Management** - Generate, verify, and manage JWT tokens
- 📊 **Health Monitoring** - Built-in health checks and logging

## Architecture

```
Claude MCP Client
       ↓ (Bearer Token)
   Nginx Router
       ↓ (auth_request)
   Auth Service ← JWT Validation
       ↓ (if valid)
   Super Claude MCP
```

## Endpoints

### Authentication
- `GET /auth` - Internal auth validation for nginx auth_request
- `POST /token` - Generate JWT tokens (for development/testing)

### OAuth Metadata (MCP Spec Compliance)
- `GET /.well-known/oauth-protected-resource` - Protected resource metadata
- `GET /.well-known/oauth-authorization-server` - Authorization server metadata

### Health
- `GET /health` - Service health check

## JWT Token Format

```json
{
  "sub": "claude-user",        // User ID
  "scope": "read,write",       // Permissions
  "iss": "super-claude",       // Issuer
  "aud": "super-claude-mcp",   // Audience
  "iat": 1640995200,           // Issued at
  "exp": 1641081600,           // Expires at
  "jti": "unique-token-id"     // Token ID
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET` | Secret key for signing JWTs | `your-super-secret-key-change-this-in-production` |
| `JWT_ISSUER` | Token issuer identifier | `super-claude` |
| `JWT_AUDIENCE` | Token audience identifier | `super-claude-mcp` |
| `PORT` | Service port | `3000` |
| `NODE_ENV` | Environment mode | `development` |

## Scopes

- `read` - Read access to MCP tools and resources
- `write` - Write access to MCP tools and resources
- `admin` - Full administrative access

## CLI Utilities

The `jwt-utils.js` script provides token management:

```bash
# Generate token
node jwt-utils.js generate [userId] [scope] [expiresIn]

# Verify token
node jwt-utils.js verify <token>

# Generate new JWT secret
node jwt-utils.js secret
```

## Docker Integration

The service is designed to run alongside the Super Claude MCP in a Docker Compose setup:

```yaml
super-claude-auth:
  build:
    context: ./auth-service
  environment:
    - JWT_SECRET=${JWT_SECRET}
    - JWT_ISSUER=${JWT_ISSUER}
    - JWT_AUDIENCE=${JWT_AUDIENCE}
```

## Security Considerations

1. **Change the default JWT secret** before production deployment
2. **Use HTTPS** in production to protect bearer tokens in transit
3. **Set appropriate token expiration** based on security requirements
4. **Monitor token usage** through nginx access logs
5. **Rotate JWT secrets** periodically for enhanced security

## Error Handling

The service returns OAuth 2.1 compliant error responses:

- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Valid token but insufficient permissions
- `500 Internal Server Error` - Service errors

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Run in production mode
npm start
```

## Testing

Use the included test script to verify functionality:

```bash
./test-auth.sh
```

## Integration with Claude

Configure Claude MCP client with the authorization token:

```json
{
  "type": "url",
  "url": "https://your-domain.com:8080/mcp",
  "name": "super-claude",
  "authorization_token": "eyJhbGciOiJIUzI1NiIs..."
}
```
