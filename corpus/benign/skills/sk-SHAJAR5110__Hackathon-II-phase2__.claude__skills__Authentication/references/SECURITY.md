# Security Hardening Guide

## Password Security

### Password Requirements

```
✅ Minimum 8 characters
✅ At least 1 uppercase letter
✅ At least 1 lowercase letter
✅ At least 1 number
✅ At least 1 special character (!@#$%^&*.-_)
```

### Password Validation

```python
# Python
import re

def validate_password(password: str) -> bool:
    if len(password) < 8:
        raise ValueError("Min 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Need uppercase")
    if not re.search(r"[a-z]", password):
        raise ValueError("Need lowercase")
    if not re.search(r"[0-9]", password):
        raise ValueError("Need digit")
    if not re.search(r"[!@#$%^&*.\-_]", password):
        raise ValueError("Need special char")
    return True
```

```javascript
// JavaScript
function validatePassword(password) {
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*.-_])[A-Za-z\d!@#$%^&*.-_]{8,}$/;
    return regex.test(password);
}
```

## Bcrypt Configuration

### Recommended Settings

```python
# Cost factor: 10-12
# Time: 100-500ms per hash
# Salt: Automatic

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 10-12 recommended
)
```

```javascript
// JavaScript - Cost factor 10-12
const SALT_ROUNDS = 12;
const hash = await bcrypt.hash(password, SALT_ROUNDS);
```

## Token Security

### Access Token

```
Duration: 15-30 minutes
Usage: API requests
Storage: Memory or HTTP-Only cookie
Rotation: On refresh
```

### Refresh Token

```
Duration: 7-30 days
Usage: Get new access token
Storage: HTTP-Only cookie
Rotation: Each use (optional but recommended)
Revocation: Supported via database
```

### Token Rotation Strategy

```python
# When using refresh token, issue new refresh token
async def refresh_access_token(refresh_token: str):
    user_id = verify_refresh_token(refresh_token)
    
    # Mark old token as used
    invalidate_refresh_token(refresh_token)
    
    # Issue new tokens
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    
    return new_access, new_refresh
```

## HTTP-Only Cookies

### Correct Configuration

```python
# FastAPI
response.set_cookie(
    key="token",
    value=token,
    httpOnly=True,        # Critical: prevents JS access (XSS)
    secure=True,          # HTTPS only
    sameSite="strict",    # CSRF protection
    max_age=3600,        # Expiration
    path="/",
    domain="yourdomain.com"
)
```

```javascript
// Express.js
res.cookie("token", token, {
    httpOnly: true,      // Critical
    secure: true,        // HTTPS
    sameSite: "strict",  // CSRF
    maxAge: 3600000,    // Milliseconds
    path: "/"
});
```

### Why HTTP-Only?

- ✅ Prevents XSS attacks from stealing tokens
- ✅ Automatically sent with requests
- ✅ Cannot be accessed by JavaScript
- ✅ Protects against token theft

## CSRF Protection

### Token-Based CSRF

```python
# Generate CSRF token
import secrets
csrf_token = secrets.token_urlsafe(32)

# Store in database/session
store_csrf_token(user_id, csrf_token)

# Send in form or header
return {
    "csrf_token": csrf_token
}

# Verify on state-changing requests
def verify_csrf(request):
    if request.method in ["POST", "PUT", "DELETE"]:
        token = request.form.get("csrf_token")
        stored = get_csrf_token(request.session.user_id)
        if token != stored:
            raise HTTPException("CSRF token invalid")
```

### Double Submit Cookies

```javascript
// Generate token
const csrfToken = crypto.randomBytes(32).toString('hex');

// Set in cookie and form
res.cookie('XSRF-TOKEN', csrfToken, {
    httpOnly: false,  // Accessible to JS for forms
    secure: true,
    sameSite: 'strict'
});

// Verify: token from header must match cookie
app.use((req, res, next) => {
    if (req.method in ['POST', 'PUT', 'DELETE']) {
        const token = req.headers['x-xsrf-token'];
        const cookie = req.cookies['XSRF-TOKEN'];
        if (token !== cookie) {
            return res.status(403).json({ error: 'CSRF invalid' });
        }
    }
    next();
});
```

## Rate Limiting

### Login Endpoint (Critical!)

```python
# FastAPI with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    # Max 5 attempts per minute per IP
    ...
```

```javascript
// Express with express-rate-limit
const rateLimit = require("express-rate-limit");

const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,  // 15 minutes
    max: 5,                     // 5 requests
    message: "Too many login attempts",
    standardHeaders: true,
    legacyHeaders: false
});

app.post("/login", loginLimiter, async (req, res) => {
    // ...
});
```

### API Rate Limiting

```python
# General API limit: 100 requests per minute per user

@app.get("/api/data")
@limiter.limit("100/minute")
async def get_data(request: Request, ...):
    ...
```

## SQL Injection Prevention

### Always Use Parameterized Queries

```python
# ✅ SAFE - Parameterized
user = db.query(User).filter(User.email == email).first()

# ❌ UNSAFE - String concatenation
user = db.query(f"SELECT * FROM users WHERE email = '{email}'")
```

```javascript
// ✅ SAFE - Prepared statement
db.query("SELECT * FROM users WHERE email = ?", [email]);

// ❌ UNSAFE - String concatenation
db.query(`SELECT * FROM users WHERE email = '${email}'`);
```

## XSS Prevention

### Content Security Policy (CSP)

```python
# FastAPI
@app.middleware("http")
async def add_csp(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:"
    )
    return response
```

```javascript
// Express
app.use((req, res, next) => {
    res.setHeader(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    );
    next();
});
```

### Input Sanitization

```python
# Always sanitize user input
from html import escape

def sanitize_input(user_input: str) -> str:
    return escape(user_input.strip())

# Or use libraries
from bleach import clean
safe_html = clean(user_input, tags=[], strip=True)
```

## Secure Headers

### All Required Headers

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response
```

## Secret Management

### Never Hardcode Secrets

```python
# ✅ SAFE - Environment variable
SECRET_KEY = os.getenv("SECRET_KEY")

# ❌ UNSAFE - Hardcoded
SECRET_KEY = "my-secret-key"
```

### .env File (Never commit!)

```bash
# .env
DATABASE_URL=...
JWT_SECRET=...
STRIPE_KEY=...

# .gitignore
.env
.env.local
.env.*.local
```

### Secrets in Production

```bash
# Use managed secrets (AWS Secrets Manager, HashiCorp Vault, etc.)
aws secretsmanager get-secret-value --secret-id my-secret
```

## Session Security

### Session Configuration

```python
# Secure session setup
from datetime import timedelta

session_config = {
    'session_type': 'filesystem',
    'permanent_session_lifetime': timedelta(minutes=30),
    'session_cookie_secure': True,
    'session_cookie_httponly': True,
    'session_cookie_samesite': 'Strict',
    'session_cookie_name': '__session'
}
```

### Session Cleanup

```python
# Clean expired sessions regularly
import schedule
import time

def cleanup_sessions():
    expired = db.query(Session).filter(
        Session.expires_at < datetime.utcnow()
    ).all()
    
    for session in expired:
        db.delete(session)
    db.commit()

schedule.every().hour.do(cleanup_sessions)
```

## Logging & Monitoring

### What to Log

```python
# ✅ Log these events
- Login attempts (successful and failed)
- Failed authentication (with IP)
- Password changes
- Permission changes
- Admin actions

# ❌ Never log these
- Passwords
- Credit cards
- API keys
- Tokens
- PII (unless required)
```

### Secure Logging

```python
import logging

# Configure logging
logging.basicConfig(
    filename='security.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log events (no sensitive data)
logger.info(f"Login attempt from IP: {request.client.host}")
logger.warning(f"Failed login for email: {email}")
```

## Audit Trail

### Track All Changes

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    resource = Column(String)
    changes = Column(JSON)
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Log on every important action
def log_audit(user_id: int, action: str, resource: str, changes: dict, ip: str):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        changes=changes,
        ip_address=ip
    )
    db.add(audit)
    db.commit()
```

## Security Checklist

Before deployment:

- [ ] Passwords hashed with bcrypt (rounds: 12)
- [ ] HTTPS/TLS enabled
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] CSRF protection active
- [ ] XSS protection (CSP headers)
- [ ] SQL injection prevention (parameterized queries)
- [ ] HTTP-Only cookies used
- [ ] Secure headers set
- [ ] Secrets in environment variables
- [ ] Audit logging configured
- [ ] Access control implemented
- [ ] Session timeout configured
- [ ] Token expiration set
- [ ] Refresh token rotation enabled
- [ ] Email verification required
- [ ] Password requirements enforced
- [ ] Account lockout after failed attempts
- [ ] Security monitoring enabled
- [ ] Incident response plan ready