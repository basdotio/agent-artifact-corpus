# Security & Authentication Guide

## Authentication System

### JWT Token Management

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings
from sqlmodel import Session, select
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: int
    scopes: list[str] = []

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_tokens(user_id: int, scopes: list[str] = []) -> dict:
    """Create access and refresh tokens"""
    
    # Access token (short-lived, 15-30 minutes)
    access_payload = {
        "sub": str(user_id),
        "type": "access",
        "scopes": scopes,
        "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    }
    access_token = jwt.encode(
        access_payload,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    # Refresh token (long-lived, 7-30 days)
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    }
    refresh_token = jwt.encode(
        refresh_payload,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """Validate and return current authenticated user"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
            
        token_data = TokenData(user_id=int(user_id), scopes=payload.get("scopes", []))
        
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.id == token_data.user_id)).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User inactive")
    
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user has admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

async def get_current_moderator(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user has moderator or admin role"""
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required"
        )
    return current_user
```

### Token Refresh Endpoint

```python
# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.models.user import User
from app.models.token import RefreshToken
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    session: Session = Depends(get_session)
):
    """Refresh expired access token using refresh token"""
    
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Verify refresh token in database (revocation check)
    db_refresh = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == int(user_id),
            RefreshToken.token == request.refresh_token,
            RefreshToken.revoked == False
        )
    ).first()
    
    if not db_refresh:
        raise HTTPException(status_code=401, detail="Refresh token revoked or invalid")
    
    user = session.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    tokens = create_tokens(user.id)
    return TokenResponse(**tokens)
```

### Login Endpoint with Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Rate limit: 5 attempts per minute
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """Authenticate user and return tokens"""
    
    user = session.exec(
        select(User).where(User.email == credentials.username)
    ).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        # Avoid timing attacks by hashing even on user not found
        hash_password("dummy_password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    
    # Create tokens
    tokens = create_tokens(user.id)
    
    # Store refresh token in database
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token=tokens["refresh_token"],
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    )
    session.add(refresh_token_record)
    session.commit()
    
    return TokenResponse(**tokens)

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Revoke refresh tokens (logout)"""
    
    refresh_tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False
        )
    ).all()
    
    for token in refresh_tokens:
        token.revoked = True
    
    session.add_all(refresh_tokens)
    session.commit()
    
    return {"message": "Logged out successfully"}
```

## Password Management

### Secure Password Reset Flow

```python
from app.services.email_service import send_password_reset_email
from app.models.password_reset import PasswordResetToken
import secrets

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    session: Session = Depends(get_session)
):
    """Request password reset email"""
    
    user = session.exec(select(User).where(User.email == email)).first()
    
    # Don't reveal if user exists (security best practice)
    if not user:
        return {"message": "If email exists, reset link sent"}
    
    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    reset_payload = {
        "sub": str(user.id),
        "type": "password-reset",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    
    encoded_token = jwt.encode(
        reset_payload,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    # Store token in database
    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password(reset_token),
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    session.add(reset_record)
    session.commit()
    
    # Send email
    reset_url = f"{settings.frontend_url}/reset-password?token={encoded_token}"
    await send_password_reset_email(user.email, reset_url)
    
    return {"message": "If email exists, reset link sent"}

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        return v

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetRequest,
    session: Session = Depends(get_session)
):
    """Reset password with valid token"""
    
    try:
        payload = jwt.decode(
            request.token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "password-reset":
            raise HTTPException(status_code=400, detail="Invalid token")
            
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    # Update password
    user.hashed_password = hash_password(request.new_password)
    session.add(user)
    
    # Revoke all refresh tokens (force re-login on all devices)
    refresh_tokens = session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    ).all()
    for token in refresh_tokens:
        token.revoked = True
    
    session.add_all(refresh_tokens)
    session.commit()
    
    return {"message": "Password reset successfully"}
```

## Authorization Patterns

### Role-Based Access Control (RBAC)

```python
from enum import Enum

class Permission(str, Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    READ_PAYMENTS = "read:payments"
    WRITE_PAYMENTS = "write:payments"

# Define role permissions
ROLE_PERMISSIONS = {
    "admin": [
        Permission.READ_USERS,
        Permission.WRITE_USERS,
        Permission.DELETE_USERS,
        Permission.READ_PAYMENTS,
        Permission.WRITE_PAYMENTS,
    ],
    "moderator": [
        Permission.READ_USERS,
        Permission.READ_PAYMENTS,
    ],
    "user": [
        Permission.READ_PAYMENTS,  # Only own payments
    ],
}

async def check_permission(
    required_permission: Permission,
    current_user: User = Depends(get_current_user)
):
    """Check if user has required permission"""
    user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    if required_permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    return current_user

# Usage
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(check_permission(Permission.DELETE_USERS)),
    session: Session = Depends(get_session)
):
    # Only admin can reach here
    user = session.get(User, user_id)
    session.delete(user)
    session.commit()
    return {"message": "User deleted"}
```

### Resource-Based Authorization

```python
async def check_resource_ownership(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Verify user owns the resource"""
    resource = session.get(Payment, resource_id)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Admin can access any resource
    if current_user.role == "admin":
        return resource
    
    # Regular users can only access own resources
    if resource.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return resource

@router.get("/payments/{payment_id}")
async def get_payment(
    payment: Payment = Depends(check_resource_ownership)
):
    return payment
```

## Security Headers & CORS

### Middleware Setup

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZIPMiddleware

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Never use ["*"] in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=3600,  # Cache preflight requests
)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts  # ["yourdomain.com", "api.yourdomain.com"]
)

# Gzip compression
app.add_middleware(GZIPMiddleware, minimum_size=1000)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Content Security
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    # HSTS - enforce HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Privacy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), microphone=()"
    
    return response
```

## SQL Injection Prevention

### SQLModel/SQLAlchemy Protection

```python
# ✅ SAFE - Uses parameterized queries
user = session.exec(
    select(User).where(User.email == email)  # Parameter binding
).first()

# ❌ UNSAFE - String interpolation (never do this)
user = session.exec(f"SELECT * FROM users WHERE email = '{email}'").first()
```

## Input Validation

### Comprehensive Field Validation

```python
from pydantic import Field, field_validator, EmailStr

class UserCreate(SQLModel):
    email: EmailStr  # Built-in email validation
    full_name: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z\s'-]+$"  # Only letters, spaces, hyphens, apostrophes
    )
    password: str = Field(
        min_length=8,
        max_length=128
    )
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if v.count("  ") > 0:
            raise ValueError("Double spaces not allowed")
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        if not any(c in '!@#$%^&*.-_' for c in v):
            raise ValueError('Must contain special character')
        return v
```

## Rate Limiting

### Implement Brute Force Protection

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to app
@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...

# Custom limiter by user ID
def get_user_limiter():
    return Limiter(key_func=lambda r: get_current_user().id)

@app.post("/api/v1/auth/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, ...):
    ...
```

## HTTPS & SSL/TLS

### Enforcement

```python
# Redirect HTTP to HTTPS
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app.add_middleware(HTTPSRedirectMiddleware)

# Environment-based
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

## Secrets Management

### Environment Variables (Never Hardcode)

```bash
# .env (NEVER commit to git)
SECRET_KEY=your-secret-key-min-32-chars
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
DATABASE_PASSWORD=...
EMAIL_PASSWORD=...
```

### .gitignore

```
.env
.env.local
.env.*.local
secrets/
```

## Logging Security Events

```python
import logging

logger = logging.getLogger(__name__)

# Log security events
logger.warning(f"Failed login attempt for email: {email}")
logger.warning(f"Unauthorized access attempt to resource: {resource_id}")
logger.info(f"User {user_id} logged out")

# NEVER log sensitive data
# logger.debug(f"Password: {password}")  # ❌ NEVER
# logger.debug(f"Token: {token}")  # ❌ NEVER
```

## Security Checklist

- ✅ Passwords hashed with bcrypt (min 10 rounds)
- ✅ JWT tokens with short expiration (15-30 min)
- ✅ Refresh tokens stored in database with revocation
- ✅ CORS configured strictly for frontend domain only
- ✅ HTTPS enforced with HSTS headers
- ✅ SQL injection prevented with parameterized queries
- ✅ Rate limiting on authentication endpoints
- ✅ CSRF protection (FastAPI default with session cookies)
- ✅ Input validation on all endpoints
- ✅ Secrets in environment variables
- ✅ Security headers middleware
- ✅ Logging without sensitive data
- ✅ Regular dependency updates
- ✅ Password reset with secure tokens
- ✅ Session timeout on inactivity