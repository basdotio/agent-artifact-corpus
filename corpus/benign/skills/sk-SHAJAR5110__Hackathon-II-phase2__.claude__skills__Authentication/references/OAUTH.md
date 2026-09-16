# OAuth2 & Social Login

## OAuth2 Flow

### Authorization Code Flow (Most Common)

```
1. User clicks "Login with Google"
2. Redirect to Google's authorization endpoint
3. User logs in and grants permission
4. Google redirects back with authorization code
5. Backend exchanges code for access token
6. Backend gets user info from Google
7. Create/update user in database
8. Issue session/JWT token to user
9. Redirect to app dashboard
```

## Google OAuth2

### Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add redirect URI: `https://yourdomain.com/api/auth/google/callback`

### Environment Variables

```bash
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback
```

### Implementation - FastAPI

```python
# routes/oauth.py
from google.auth.transport import requests
from google.oauth2 import id_token
from fastapi import HTTPException
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@app.post("/auth/google")
async def google_login(token: str):
    """
    Frontend sends Google ID token
    Backend verifies and creates user
    """
    try:
        # Verify token
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user info
        email = idinfo.get("email")
        name = idinfo.get("name")
        picture = idinfo.get("picture")
        
        # Create or get user
        user = await get_or_create_user(
            email=email,
            name=name,
            picture=picture,
            provider="google"
        )
        
        # Create session
        access_token = create_access_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "user": user
        }
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Implementation - Next.js Frontend

```typescript
// components/GoogleLogin.tsx
import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';

export function GoogleLoginButton() {
    const [loading, setLoading] = useState(false);
    
    async function handleGoogleSuccess(credentialResponse: any) {
        setLoading(true);
        try {
            const response = await fetch('/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: credentialResponse.credential })
            });
            
            const data = await response.json();
            
            // Store token
            localStorage.setItem('access_token', data.access_token);
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            console.error('Login failed:', error);
        } finally {
            setLoading(false);
        }
    }
    
    return (
        <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => console.error('Login failed')}
        />
    );
}
```

## GitHub OAuth2

### Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `https://yourdomain.com/api/auth/github/callback`

### Environment Variables

```bash
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_REDIRECT_URI=https://yourdomain.com/api/auth/github/callback
```

### Implementation - Express.js

```javascript
// routes/oauth.js
const axios = require('axios');

async function getGitHubUser(accessToken) {
    const response = await axios.get('https://api.github.com/user', {
        headers: { Authorization: `Bearer ${accessToken}` }
    });
    return response.data;
}

async function getGitHubUserEmail(accessToken) {
    const response = await axios.get('https://api.github.com/user/emails', {
        headers: { Authorization: `Bearer ${accessToken}` }
    });
    
    // Return primary email
    const primary = response.data.find(e => e.primary);
    return primary?.email;
}

app.get('/auth/github/callback', async (req, res) => {
    const { code } = req.query;
    
    try {
        // Exchange code for access token
        const tokenResponse = await axios.post(
            'https://github.com/login/oauth/access_token',
            {
                client_id: process.env.GITHUB_CLIENT_ID,
                client_secret: process.env.GITHUB_CLIENT_SECRET,
                code
            },
            { headers: { Accept: 'application/json' } }
        );
        
        const { access_token } = tokenResponse.data;
        
        // Get user info
        const gitHubUser = await getGitHubUser(access_token);
        const email = await getGitHubUserEmail(access_token);
        
        // Create or get user
        const user = await getOrCreateUser({
            email,
            name: gitHubUser.name,
            picture: gitHubUser.avatar_url,
            provider: 'github',
            providerId: gitHubUser.id
        });
        
        // Create session
        const sessionToken = createToken(user.id);
        
        // Redirect to app
        res.redirect(`/dashboard?token=${sessionToken}`);
        
    } catch (error) {
        console.error('GitHub OAuth error:', error);
        res.redirect(`/login?error=${error.message}`);
    }
});
```

## Multiple OAuth Providers

### NextAuth.js (Recommended for Next.js)

```typescript
// lib/auth.ts
import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";
import DiscordProvider from "next-auth/providers/discord";

export const authOptions = {
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID!,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET!
        }),
        GitHubProvider({
            clientId: process.env.GITHUB_CLIENT_ID!,
            clientSecret: process.env.GITHUB_CLIENT_SECRET!
        }),
        DiscordProvider({
            clientId: process.env.DISCORD_CLIENT_ID!,
            clientSecret: process.env.DISCORD_CLIENT_SECRET!
        })
    ],
    callbacks: {
        async jwt({ token, account, profile }) {
            if (account) {
                token.accessToken = account.access_token;
                token.provider = account.provider;
            }
            if (profile) {
                token.picture = profile.image || profile.avatar_url;
            }
            return token;
        },
        
        async session({ session, token }) {
            session.user.id = token.sub;
            session.user.image = token.picture;
            return session;
        }
    }
};

export default NextAuth(authOptions);
```

### Usage in Next.js

```typescript
// components/LoginPage.tsx
import { signIn } from "next-auth/react";

export function LoginPage() {
    return (
        <div>
            <button onClick={() => signIn("google")}>
                Sign in with Google
            </button>
            
            <button onClick={() => signIn("github")}>
                Sign in with GitHub
            </button>
            
            <button onClick={() => signIn("discord")}>
                Sign in with Discord
            </button>
        </div>
    );
}
```

## Account Linking

Allow users to connect multiple OAuth providers:

```python
# FastAPI
class LinkedAccount(Base):
    __tablename__ = "linked_accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)  # google, github, discord
    provider_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

@app.post("/auth/link/{provider}")
async def link_account(
    provider: str,
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Link additional OAuth provider to existing account"""
    
    # Verify provider token
    user_info = verify_provider_token(provider, token)
    
    # Check if already linked
    existing = db.query(LinkedAccount).filter(
        LinkedAccount.provider == provider,
        LinkedAccount.provider_id == user_info['id']
    ).first()
    
    if existing and existing.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Account already linked")
    
    # Link account
    linked = LinkedAccount(
        user_id=current_user.id,
        provider=provider,
        provider_id=user_info['id']
    )
    db.add(linked)
    db.commit()
    
    return {"message": "Account linked"}
```

## Security Considerations

✅ **Always verify tokens server-side**
✅ **Use HTTPS for all OAuth flows**
✅ **Store provider IDs, not tokens**
✅ **Use state parameter for CSRF protection**
✅ **Validate redirect URLs**
✅ **Handle token expiration**
✅ **Rate limit OAuth endpoints**
✅ **Audit OAuth connections**