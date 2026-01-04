#!/usr/bin/env node

const jwt = require('jsonwebtoken');
const crypto = require('crypto');

// Default configuration
const DEFAULT_SECRET = process.env.JWT_SECRET || 'your-super-secret-key-change-this-in-production';
const DEFAULT_ISSUER = process.env.JWT_ISSUER || 'super-claude';
const DEFAULT_AUDIENCE = process.env.JWT_AUDIENCE || 'super-claude-mcp';

function generateToken(options = {}) {
    const {
        secret = DEFAULT_SECRET,
        issuer = DEFAULT_ISSUER,
        audience = DEFAULT_AUDIENCE,
        userId = 'claude-user',
        scope = 'read,write',
        expiresIn = '1h'
    } = options;

    const payload = {
        sub: userId,
        scope: scope,
        iss: issuer,
        aud: audience,
        iat: Math.floor(Date.now() / 1000),
        jti: crypto.randomUUID() // Unique token ID
    };

    const token = jwt.sign(payload, secret, { 
        expiresIn: expiresIn,
        algorithm: 'HS256'
    });

    return token;
}

function verifyToken(token, secret = DEFAULT_SECRET) {
    try {
        const decoded = jwt.verify(token, secret, {
            issuer: DEFAULT_ISSUER,
            audience: DEFAULT_AUDIENCE,
            algorithms: ['HS256']
        });
        return { valid: true, payload: decoded };
    } catch (error) {
        return { valid: false, error: error.message };
    }
}

function generateSecret() {
    return crypto.randomBytes(32).toString('hex');
}

// CLI functionality
if (require.main === module) {
    const command = process.argv[2];
    
    switch (command) {
        case 'generate':
        case 'gen':
            const userId = process.argv[3] || 'claude-user';
            const scope = process.argv[4] || 'read,write';
            const expiresIn = process.argv[5] || '1h';
            
            const token = generateToken({ userId, scope, expiresIn });
            const decoded = jwt.decode(token);
            
            const issuedAt = new Date(decoded.iat * 1000).toISOString();
            const expiresAt = new Date(decoded.exp * 1000).toISOString();
            const daysValid = Math.round((decoded.exp - decoded.iat) / 86400);
            
            console.log('🔑 Generated JWT Token:');
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(`Token: ${token}`);
            console.log('');
            console.log('📋 Token Details:');
            console.log(`User ID:   ${decoded.sub}`);
            console.log(`Scope:     ${decoded.scope}`);
            console.log(`Issuer:    ${decoded.iss}`);
            console.log(`Audience:  ${decoded.aud}`);
            console.log(`Issued:    ${issuedAt}`);
            console.log(`Expires:   ${expiresAt}`);
            console.log(`Valid for: ${daysValid} days`);
            console.log(`Token ID:  ${decoded.jti}`);
            console.log('');
            console.log('🔧 For Claude MCP config, add:');
            console.log(`"authorization_token": "${token}"`);
            console.log('');
            console.log('📝 To record in Super Claude state, use token_record tool with:');
            console.log(`   subject:    ${decoded.sub}`);
            console.log(`   issued_at:  ${issuedAt}`);
            console.log(`   expires_at: ${expiresAt}`);
            break;
            
        case 'verify':
            const tokenToVerify = process.argv[3];
            if (!tokenToVerify) {
                console.error('❌ Error: Please provide a token to verify');
                console.log('Usage: node jwt-utils.js verify <token>');
                process.exit(1);
            }
            
            const result = verifyToken(tokenToVerify);
            if (result.valid) {
                console.log('✅ Token is valid');
                console.log('');
                console.log('Payload:');
                console.log(`  User ID:  ${result.payload.sub}`);
                console.log(`  Scope:    ${result.payload.scope}`);
                console.log(`  Issued:   ${new Date(result.payload.iat * 1000).toISOString()}`);
                console.log(`  Expires:  ${new Date(result.payload.exp * 1000).toISOString()}`);
                
                const now = Math.floor(Date.now() / 1000);
                const remaining = result.payload.exp - now;
                if (remaining > 0) {
                    const daysRemaining = Math.floor(remaining / 86400);
                    console.log(`  Status:   ✅ ${daysRemaining} days remaining`);
                } else {
                    console.log(`  Status:   ❌ Expired ${Math.abs(Math.floor(remaining / 86400))} days ago`);
                }
            } else {
                console.log('❌ Token is invalid');
                console.log('Error:', result.error);
            }
            break;
            
        case 'secret':
            const newSecret = generateSecret();
            console.log('🔐 Generated JWT Secret:');
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(newSecret);
            console.log('');
            console.log('💡 Add this to your environment:');
            console.log(`JWT_SECRET=${newSecret}`);
            break;
            
        default:
            console.log('🔑 Super Claude JWT Utilities');
            console.log('');
            console.log('Commands:');
            console.log('  generate|gen [userId] [scope] [expiresIn] - Generate a new JWT token');
            console.log('  verify <token>                           - Verify a JWT token');
            console.log('  secret                                   - Generate a new JWT secret');
            console.log('');
            console.log('Examples:');
            console.log('  node jwt-utils.js generate claude-user "read,write,admin" 180d');
            console.log('  node jwt-utils.js verify eyJhbGciOiJIUzI1NiIs...');
            console.log('  node jwt-utils.js secret');
    }
}

module.exports = { generateToken, verifyToken, generateSecret };
