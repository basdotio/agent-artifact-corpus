#!/usr/bin/env python3
"""
FastAPI Project Boilerplate Generator

Generates a complete production-ready FastAPI project structure with all
necessary files, configurations, and examples.

Usage:
    python generate_boilerplate.py --name my_project [--path ./projects]
"""

import argparse
import os
from pathlib import Path
from typing import Dict

PROJECT_STRUCTURE = {
    "app": {
        "__init__.py": "",
        "main.py": "main",
        "config.py": "config",
        "models": {
            "__init__.py": "",
            "user.py": "user_model",
        },
        "schemas": {
            "__init__.py": "",
            "user.py": "user_schema",
        },
        "routes": {
            "__init__.py": "",
            "auth.py": "auth_routes",
            "users.py": "user_routes",
        },
        "services": {
            "__init__.py": "",
            "user_service.py": "user_service",
        },
        "dependencies": {
            "__init__.py": "",
            "database.py": "database_dep",
            "auth.py": "auth_dep",
        },
        "middleware": {
            "__init__.py": "",
            "security.py": "security_middleware",
        },
        "utils": {
            "__init__.py": "",
            "validators.py": "validators",
        },
    },
    "tests": {
        "__init__.py": "",
        "conftest.py": "conftest",
        "test_auth.py": "test_auth",
        "test_users.py": "test_users",
    },
    "migrations": {},
}

TEMPLATES = {
    "main": '''"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import auth, users

# Create app
app = FastAPI(
    title="My API",
    description="Production-grade API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
''',

    "config": '''"""Application Configuration"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    db_echo: bool = False
    
    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # App
    debug: bool = False
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
''',

    "user_model": '''"""User Database Model"""
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from pydantic import EmailStr

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True, index=True)
    full_name: str = Field(min_length=1, max_length=255)
    hashed_password: str = Field(min_length=60)
    is_active: bool = Field(default=True, index=True)
    email_verified: bool = Field(default=False)
    
    role: str = Field(default="user", index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

class UserCreate(SQLModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)

class UserResponse(SQLModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
''',

    "user_schema": '''"""User Pydantic Schemas"""
from pydantic import EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

class UserResponse(SQLModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
''',

    "auth_routes": '''"""Authentication Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.user import User
from app.schemas.user import UserResponse
from app.dependencies.database import get_session
from app.dependencies.auth import (
    hash_password, verify_password, create_tokens, get_current_user
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login")
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """Login endpoint"""
    user = session.exec(
        select(User).where(User.email == credentials.username)
    ).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    tokens = create_tokens(user.id)
    return {**tokens, "user": UserResponse.from_orm(user)}

@router.post("/register")
async def register(
    email: str,
    full_name: str,
    password: str,
    session: Session = Depends(get_session)
):
    """Register endpoint"""
    existing = session.exec(
        select(User).where(User.email == email)
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse.from_orm(user)

@router.get("/me", response_model=UserResponse)
async def get_current(
    current_user: User = Depends(get_current_user)
):
    """Get current user"""
    return current_user
''',

    "user_routes": '''"""User Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from sqlmodel import Session, select
from app.models.user import User
from app.schemas.user import UserResponse
from app.dependencies.database import get_session
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List users"""
    users = session.exec(
        select(User).where(User.deleted_at == None).offset(skip).limit(limit)
    ).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
''',

    "user_service": '''"""User Business Logic"""
from sqlmodel import Session
from app.models.user import User, UserCreate
from app.dependencies.auth import hash_password
from datetime import datetime

class UserService:
    async def create_user(self, user_in: UserCreate, session: Session):
        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=hash_password(user_in.password)
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    
    async def update_user(self, user: User, updates: dict, session: Session):
        for key, value in updates.items():
            if value is not None:
                setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
''',

    "database_dep": '''"""Database Dependency"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import NullPool
from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    poolclass=NullPool if "neon" in settings.database_url else None
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
''',

    "auth_dep": '''"""Authentication Dependency"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from app.config import settings
from app.models.user import User
from app.dependencies.database import get_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_tokens(user_id: int):
    access_payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    }
    access_token = jwt.encode(
        access_payload, settings.secret_key, algorithm=settings.algorithm
    )
    
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    }
    refresh_token = jwt.encode(
        refresh_payload, settings.secret_key, algorithm=settings.algorithm
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = session.exec(select(User).where(User.id == int(user_id))).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
''',

    "security_middleware": '''"""Security Middleware"""
from fastapi import Request

async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
''',

    "validators": '''"""Validation Utilities"""
from pydantic import field_validator

def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Must contain uppercase")
    if not any(c.isdigit() for c in password):
        raise ValueError("Must contain digit")
    return password
''',

    "conftest": '''"""Test Configuration"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from app.main import app
from app.dependencies.database import get_session
from app.models.user import User
from app.dependencies.auth import hash_password

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=hash_password("Test123!@#"),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
''',

    "test_auth": '''"""Authentication Tests"""
import pytest

def test_login(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "Test123!@#"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_register(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "full_name": "New User", "password": "New123!@#"}
    )
    assert response.status_code == 200
''',

    "test_users": '''"""User Endpoint Tests"""
import pytest

def test_list_users(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 200

def test_get_user(client, auth_token, test_user):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get(f"/api/v1/users/{test_user.id}", headers=headers)
    assert response.status_code == 200
''',
}

def create_directory_structure(base_path: Path, structure: Dict):
    """Recursively create directory structure"""
    for name, content in structure.items():
        path = base_path / name
        
        if isinstance(content, dict):
            path.mkdir(exist_ok=True)
            create_directory_structure(path, content)
        else:
            if isinstance(content, str) and content in TEMPLATES:
                path.write_text(TEMPLATES[content])
            else:
                path.write_text(content)

def create_requirements():
    """Generate requirements.txt"""
    return """fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlmodel==0.0.14
sqlalchemy==2.0.23
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
psycopg[binary]==3.17.0
stripe==7.4.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
httpx==0.25.1
slowapi==0.1.9
redis==5.0.1
"""

def create_env_example():
    """Generate .env.example"""
    return """# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# Security
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# App
DEBUG=False
ENVIRONMENT=development
"""

def create_dockerfile():
    """Generate Dockerfile"""
    return """FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY main.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

def create_gitignore():
    """Generate .gitignore"""
    return """.env
.env.local
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
venv/
.DS_Store
.vscode/
.idea/
"""

def main():
    parser = argparse.ArgumentParser(
        description="Generate FastAPI project boilerplate"
    )
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--path", default=".", help="Output path")
    
    args = parser.parse_args()
    
    project_path = Path(args.path) / args.name
    
    if project_path.exists():
        print(f"❌ Project directory already exists: {project_path}")
        return
    
    print(f"🚀 Creating FastAPI project: {args.name}")
    
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create structure
    create_directory_structure(project_path, PROJECT_STRUCTURE)
    
    # Create additional files
    (project_path / "requirements.txt").write_text(create_requirements())
    (project_path / ".env.example").write_text(create_env_example())
    (project_path / "Dockerfile").write_text(create_dockerfile())
    (project_path / ".gitignore").write_text(create_gitignore())
    (project_path / "README.md").write_text(f"# {args.name}\n\nFastAPI Project\n")
    
    # Create alembic directory
    migrations_path = project_path / "migrations"
    migrations_path.mkdir(exist_ok=True)
    (migrations_path / "versions").mkdir(exist_ok=True)
    
    print(f"✅ Project created at: {project_path}")
    print("\nNext steps:")
    print(f"  cd {project_path}")
    print("  cp .env.example .env  # Configure database URL")
    print("  python -m venv venv")
    print("  source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
    print("  pip install -r requirements.txt")
    print("  uvicorn main:app --reload")

if __name__ == "__main__":
    main()