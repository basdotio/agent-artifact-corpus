# Database Patterns & Migrations

## Neon Serverless PostgreSQL Setup

### Connection String Format
```
postgresql://user:password@ep-cool-demo-123.us-east-1.neon.tech/neondb?sslmode=require
```

### Critical: Connection Pooling for Serverless

```python
from sqlmodel import create_engine
from sqlalchemy.pool import NullPool

# NEVER use QueuePool or StaticPool with Neon serverless
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Essential: one connection per request
    connect_args={
        "connect_timeout": 5,
        "application_name": "my_app"
    }
)
```

## SQLModel Model Patterns

### Complete User Model Example

```python
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, field_validator
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    full_name: str = Field(min_length=1, max_length=255)
    is_active: bool = Field(default=True, index=True)
    role: UserRole = Field(default=UserRole.USER, index=True)

class User(UserBase, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(min_length=60)
    email_verified: bool = Field(default=False)
    profile_picture_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    
    # Relationships
    payments: list["Payment"] = Relationship(
        back_populates="user",
        cascade_delete=True
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user",
        cascade_delete=True
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "role": "user"
            }
        }

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*' for c in v):
            raise ValueError('Password must contain special character')
        return v

class UserResponse(UserBase):
    id: int
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
```

### Order Model with Relationships

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    
    order: Optional["Order"] = Relationship(back_populates="items")

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    total_amount: float = Field(gt=0)
    
    shipping_address: str
    billing_address: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="orders")
    items: list[OrderItem] = Relationship(back_populates="order", cascade_delete=True)
    payment: Optional["Payment"] = Relationship(back_populates="order")
```

## Database Migrations with Alembic

### Initial Setup

```bash
alembic init migrations
```

### Configuration (migrations/env.py)

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import *  # Import all models
from app.config import settings

target_metadata = SQLModel.metadata

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Create Migrations

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Create user table"

# Manual migration
alembic revision -m "Add user email verification"
```

### Migration Example

```python
# migrations/versions/001_create_users.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.Index('ix_users_email', 'email'),
        sa.Index('ix_users_created_at', 'created_at'),
    )

def downgrade():
    op.drop_table('users')
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current
```

## Query Patterns

### Basic CRUD Operations

```python
from sqlmodel import Session, select

# Create
user = User(email="test@example.com", full_name="Test User", hashed_password="...")
session.add(user)
session.commit()
session.refresh(user)

# Read - by ID
user = session.get(User, 1)

# Read - by field
user = session.exec(select(User).where(User.email == "test@example.com")).first()

# Read - all with pagination
statement = select(User).offset(0).limit(10)
users = session.exec(statement).all()

# Read - with filter and sort
users = session.exec(
    select(User)
    .where(User.is_active == True)
    .order_by(User.created_at.desc())
).all()

# Update
user.full_name = "Updated Name"
user.updated_at = datetime.utcnow()
session.add(user)
session.commit()

# Delete (hard)
session.delete(user)
session.commit()

# Delete (soft)
user.deleted_at = datetime.utcnow()
session.add(user)
session.commit()
```

### Advanced Query Patterns

```python
from sqlalchemy import and_, or_

# Complex filters
users = session.exec(
    select(User).where(
        and_(
            User.is_active == True,
            User.created_at >= datetime(2024, 1, 1)
        )
    )
).all()

# OR conditions
users = session.exec(
    select(User).where(
        or_(
            User.role == "admin",
            User.created_at >= datetime(2024, 1, 1)
        )
    )
).all()

# Count records
count = session.query(User).filter(User.is_active == True).count()

# Distinct values
roles = session.exec(select(User.role).distinct()).all()

# Aggregations (requires SQLAlchemy imports)
from sqlalchemy import func
total = session.exec(select(func.count(User.id))).first()
```

### Relationship Loading

```python
# Eager loading with selectinload
from sqlalchemy.orm import selectinload

orders = session.exec(
    select(Order)
    .options(selectinload(Order.items), selectinload(Order.user))
).all()

# Lazy loading (default)
order = session.get(Order, 1)
items = order.items  # Triggers query
```

## Indexing Strategy

### Index Creation

```python
# Field-level index
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)  # Creates unique index
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    role: str = Field(index=True)  # Creates regular index

# Multi-column index in migration
def upgrade():
    op.create_index('ix_orders_user_status', 'orders', ['user_id', 'status'])
```

### Recommended Indexes

```
Users table:
  - email (unique)
  - created_at
  - is_active
  - deleted_at

Orders table:
  - user_id
  - status
  - created_at
  - (user_id, status) composite

Payments table:
  - user_id
  - status
  - stripe_payment_id (unique)
  - created_at
```

## Transactions & Error Handling

```python
from contextlib import contextmanager

@contextmanager
def transactional_session():
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage
with transactional_session() as session:
    user = User(email="test@example.com", ...)
    session.add(user)
    # Auto commits if no exception
```

## Backup & Maintenance

### Neon Specific Features

```bash
# Connection pooling managed by Neon
# Automatic backups (14-day retention)
# Point-in-time recovery available

# Export data
pg_dump \
  postgresql://user:password@ep-cool-demo.us-east-1.neon.tech/neondb \
  > backup.sql

# Import data
psql \
  postgresql://user:password@ep-cool-demo.us-east-1.neon.tech/neondb \
  < backup.sql
```

## Performance Tips

1. **Connection pooling**: Use NullPool for serverless, QueuePool for dedicated
2. **Batch operations**: Use bulk_insert_mappings() for large inserts
3. **Avoid N+1 queries**: Use selectinload() for relationships
4. **Index hot tables**: Users, orders, payments
5. **Monitor query performance**: Use EXPLAIN ANALYZE
6. **Archive old data**: Move historical data to archive tables
7. **Vacuum regularly**: Postgres VACUUM ANALYZE on large tables

## Security Best Practices

1. **Parameterized queries**: Always use SQLModel/SQLAlchemy (prevents SQL injection)
2. **Row-level security**: Implement in middleware/service layer
3. **Sensitive data**: Never log passwords, tokens, or PII
4. **Encryption**: Use pgcrypto extension for sensitive columns
5. **Backups**: Store backups separately from production database
6. **Access control**: Restrict database user permissions