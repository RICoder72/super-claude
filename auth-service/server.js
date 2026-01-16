const express = require('express');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Configuration
const JWT_SECRET = process.env.JWT_SECRET || 'change-me';
const JWT_ISSUER = process.env.JWT_ISSUER || 'super-claude';
const JWT_AUDIENCE = process.env.JWT_AUDIENCE || 'super-claude-mcp';
const CLIENT_ID = process.env.OAUTH_CLIENT_ID || 'super-claude-client';
const CLIENT_SECRET = process.env.OAUTH_CLIENT_SECRET || 'change-me';
const TOKEN_EXPIRY = process.env.TOKEN_EXPIRY || '180d';

// Store authorization codes temporarily (in production, use Redis)
const authCodes = new Map();

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'super-claude-auth' });
});

// OAuth Authorization Endpoint (auto-approves for this personal MCP)
app.get('/authorize', (req, res) => {
    const { client_id, redirect_uri, response_type, state, code_challenge, code_challenge_method } = req.query;

    console.log(`[AUTH] Authorize request - client_id: ${client_id}, response_type: ${response_type}, redirect_uri: ${redirect_uri}`);

    // Validate
    if (response_type !== 'code') {
        return res.status(400).json({ error: 'unsupported_response_type' });
    }

    // Generate authorization code
    const code = crypto.randomBytes(32).toString('hex');
    
    // Store code with metadata (expires in 5 minutes)
    authCodes.set(code, {
        clientId: client_id,
        redirectUri: redirect_uri,
        codeChallenge: code_challenge,
        codeChallengeMethod: code_challenge_method,
        expiresAt: Date.now() + 5 * 60 * 1000
    });

    console.log(`[AUTH] Authorization code issued: ${code.substring(0, 8)}...`);

    // Redirect back with code
    const redirectUrl = new URL(redirect_uri);
    redirectUrl.searchParams.set('code', code);
    if (state) redirectUrl.searchParams.set('state', state);

    res.redirect(redirectUrl.toString());
});

// OAuth Token Endpoint
app.post('/token', (req, res) => {
    const { grant_type, client_id, client_secret, code, redirect_uri, code_verifier } = req.body;

    console.log(`[AUTH] Token request - client_id: ${client_id}, grant_type: ${grant_type}`);

    if (grant_type === 'authorization_code') {
        // Validate authorization code
        const authCode = authCodes.get(code);
        
        if (!authCode) {
            console.log('[AUTH] Invalid or expired authorization code');
            return res.status(400).json({ error: 'invalid_grant', error_description: 'Invalid authorization code' });
        }

        // Check expiration
        if (Date.now() > authCode.expiresAt) {
            authCodes.delete(code);
            console.log('[AUTH] Authorization code expired');
            return res.status(400).json({ error: 'invalid_grant', error_description: 'Authorization code expired' });
        }

        // Verify PKCE if used
        if (authCode.codeChallenge) {
            if (!code_verifier) {
                return res.status(400).json({ error: 'invalid_grant', error_description: 'Code verifier required' });
            }
            
            let expectedChallenge;
            if (authCode.codeChallengeMethod === 'S256') {
                expectedChallenge = crypto.createHash('sha256')
                    .update(code_verifier)
                    .digest('base64url');
            } else {
                expectedChallenge = code_verifier;
            }
            
            if (expectedChallenge !== authCode.codeChallenge) {
                console.log('[AUTH] PKCE verification failed');
                return res.status(400).json({ error: 'invalid_grant', error_description: 'PKCE verification failed' });
            }
        }

        // Delete used code
        authCodes.delete(code);

    } else if (grant_type === 'client_credentials') {
        // Validate client credentials
        if (client_id !== CLIENT_ID || client_secret !== CLIENT_SECRET) {
            console.log('[AUTH] Invalid client credentials');
            return res.status(401).json({ error: 'invalid_client', error_description: 'Invalid client credentials' });
        }
    } else {
        return res.status(400).json({ error: 'unsupported_grant_type' });
    }

    // Generate JWT
    const now = Math.floor(Date.now() / 1000);
    const payload = {
        sub: client_id || 'claude-user',
        scope: 'read write admin',
        iss: JWT_ISSUER,
        aud: JWT_AUDIENCE,
        iat: now,
        jti: crypto.randomUUID()
    };

    const token = jwt.sign(payload, JWT_SECRET, { 
        expiresIn: TOKEN_EXPIRY,
        algorithm: 'HS256'
    });

    const decoded = jwt.decode(token);
    console.log(`[AUTH] Token issued for ${client_id}, expires: ${new Date(decoded.exp * 1000).toISOString()}`);

    res.json({
        access_token: token,
        token_type: 'Bearer',
        expires_in: decoded.exp - now,
        scope: 'read write admin'
    });
});

// Auth validation endpoint (for nginx auth_request)
app.get('/auth', (req, res) => {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        console.log('[AUTH] Missing or invalid Authorization header');
        res.set('WWW-Authenticate', 'Bearer');
        return res.status(401).json({ error: 'missing_token' });
    }

    const token = authHeader.substring(7);

    try {
        const decoded = jwt.verify(token, JWT_SECRET, {
            issuer: JWT_ISSUER,
            audience: JWT_AUDIENCE,
            algorithms: ['HS256']
        });

        res.set('X-User-ID', decoded.sub);
        res.set('X-User-Scope', decoded.scope);
        res.status(200).send('OK');
    } catch (error) {
        console.log(`[AUTH] Token validation failed: ${error.message}`);
        res.set('WWW-Authenticate', 'Bearer error="invalid_token"');
        return res.status(401).json({ error: 'invalid_token', message: error.message });
    }
});

// OAuth Protected Resource Metadata
app.get('/.well-known/oauth-protected-resource', (req, res) => {
    const host = req.headers.host || 'localhost';
    res.json({
        resource: `https://${host}`,
        authorization_servers: [`https://${host}`],
        scopes_supported: ['read', 'write', 'admin'],
        bearer_methods_supported: ['header']
    });
});

// OAuth Authorization Server Metadata  
app.get('/.well-known/oauth-authorization-server', (req, res) => {
    const host = req.headers.host || 'localhost';
    res.json({
        issuer: `https://${host}`,
        authorization_endpoint: `https://${host}/authorize`,
        token_endpoint: `https://${host}/token`,
        token_endpoint_auth_methods_supported: ['client_secret_post', 'none'],
        grant_types_supported: ['authorization_code', 'client_credentials'],
        code_challenge_methods_supported: ['S256', 'plain'],
        scopes_supported: ['read', 'write', 'admin'],
        response_types_supported: ['code', 'token']
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`[AUTH] Super Claude Auth Service running on port ${PORT}`);
    console.log(`[AUTH] Client ID: ${CLIENT_ID}`);
});
