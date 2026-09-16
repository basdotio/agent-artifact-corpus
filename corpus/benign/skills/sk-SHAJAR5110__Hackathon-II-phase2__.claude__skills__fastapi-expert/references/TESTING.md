# Testing Guide

## Test Setup

### Installation

```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock httpx
```

### Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

## Test Fixtures

### Database Fixtures (tests/conftest.py)

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
import os

from app.main import app
from app.dependencies.database import get_session
from app.models.user import User
from app.dependencies.auth import hash_password

@pytest.fixture(name="session")
def session_fixture():
    """Create test database session"""
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
    """Create test client with session dependency override"""
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create test user"""
    user = User(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password=hash_password("Test123!@#"),
        email_verified=True,
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create admin user"""
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=hash_password("Admin123!@#"),
        email_verified=True,
        is_active=True,
        role="admin"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="auth_token")
def auth_token_fixture(test_user: User):
    """Get auth token for test user"""
    from app.dependencies.auth import create_tokens
    tokens = create_tokens(test_user.id)
    return tokens["access_token"]
```

## Unit Tests

### Authentication Tests

```python
# tests/test_auth.py
import pytest
from fastapi import status
from app.models.user import User

@pytest.mark.unit
class TestAuthentication:
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser@example.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser@example.com",
                "password": "WrongPassword123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_success(self, client):
        """Test successful registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "NewPass123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",
                "full_name": "Another User",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "weak"  # Too short, no uppercase, no digit
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

### User API Tests

```python
# tests/test_users.py
import pytest
from fastapi import status

@pytest.mark.unit
class TestUserAPI:
    
    def test_list_users_requires_auth(self, client):
        """Test that list users requires authentication"""
        response = client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_users_success(self, client, auth_token, test_user):
        """Test listing users with auth"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/users/", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert any(u["email"] == test_user.email for u in data)
    
    def test_get_user_success(self, client, auth_token, test_user):
        """Test getting single user"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
    
    def test_get_user_not_found(self, client, auth_token):
        """Test getting non-existent user"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/users/9999", headers=headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_own_user(self, client, auth_token, test_user):
        """Test updating own user info"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=headers,
            json={
                "email": test_user.email,
                "full_name": "Updated Name",
                "password": "NewPass123!@#"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Updated Name"
    
    def test_update_other_user_forbidden(self, client, session, auth_token, test_user):
        """Test that regular user can't update other users"""
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hashed",
            is_active=True
        )
        session.add(other_user)
        session.commit()
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.put(
            f"/api/v1/users/{other_user.id}",
            headers=headers,
            json={"full_name": "Hacked Name"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
```

## Integration Tests

```python
# tests/test_integration.py
import pytest
from fastapi import status

@pytest.mark.integration
class TestUserFlow:
    """Test complete user workflow"""
    
    def test_register_login_access_flow(self, client):
        """Test complete user flow: register, login, access protected"""
        # Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flow@example.com",
                "full_name": "Flow User",
                "password": "FlowPass123!@#"
            }
        )
        assert register_response.status_code == status.HTTP_200_OK
        
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "flow@example.com",
                "password": "FlowPass123!@#"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        protected_response = client.get("/api/v1/users/", headers=headers)
        assert protected_response.status_code == status.HTTP_200_OK
```

## Mocking Tests

```python
# tests/test_external_services.py
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
class TestPaymentIntegration:
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_stripe, client, auth_token):
        """Test checkout session creation"""
        
        # Mock Stripe response
        mock_stripe.return_value = MagicMock(
            id="cs_test_123",
            url="https://checkout.stripe.com"
        )
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post(
            "/api/v1/payments/checkout",
            headers=headers,
            json={
                "amount": 1000,
                "currency": "usd",
                "description": "Test payment"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert "url" in data
        
        # Verify mock was called
        mock_stripe.assert_called_once()
```

## Performance Tests

```python
# tests/test_performance.py
import pytest
import time

@pytest.mark.slow
class TestPerformance:
    
    def test_list_users_performance(self, client, auth_token, session):
        """Test list users endpoint performance"""
        # Create many users
        from app.models.user import User
        from app.dependencies.auth import hash_password
        
        users = [
            User(
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                hashed_password=hash_password("Test123!@#"),
                is_active=True
            )
            for i in range(100)
        ]
        session.add_all(users)
        session.commit()
        
        # Measure performance
        headers = {"Authorization": f"Bearer {auth_token}"}
        start = time.time()
        response = client.get("/api/v1/users/?limit=100", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        assert elapsed < 0.5  # Should complete in less than 500ms
```

## Coverage Report

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

## Continuous Testing

```bash
# Run tests on file changes
pytest-watch

# Run tests with different Python versions
tox
```

## Example Test Output

```
tests/test_auth.py::TestAuthentication::test_login_success PASSED
tests/test_auth.py::TestAuthentication::test_login_invalid_password PASSED
tests/test_users.py::TestUserAPI::test_list_users_requires_auth PASSED
tests/test_users.py::TestUserAPI::test_list_users_success PASSED

======================== 4 passed in 0.42s =========================
Name                    Stmts   Miss  Cover
app/__init__.py              2      0   100%
app/models/user.py          15      0   100%
app/routes/users.py         45      2    96%
TOTAL                      120      5    96%
```