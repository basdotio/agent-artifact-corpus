# API Routes & Patterns

## RESTful API Design

### Standard HTTP Methods

- **GET** - Retrieve resource (safe, idempotent)
- **POST** - Create new resource (not idempotent)
- **PUT** - Replace entire resource (idempotent)
- **PATCH** - Partial update (idempotent)
- **DELETE** - Delete resource (idempotent)

### Status Codes

- **200 OK** - Successful GET, PUT, PATCH
- **201 Created** - Successful POST
- **204 No Content** - Successful DELETE
- **400 Bad Request** - Invalid input
- **401 Unauthorized** - Missing/invalid auth
- **403 Forbidden** - Authorized but no access
- **404 Not Found** - Resource doesn't exist
- **409 Conflict** - Duplicate resource
- **422 Unprocessable Entity** - Validation error
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

## Complete Route Examples

### User Management Routes

```python
# app/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from sqlmodel import Session, select
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.dependencies.auth import get_current_user, get_current_admin
from app.dependencies.database import get_session
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
user_service = UserService()

# List Users
@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users",
    description="Get paginated list of users"
)
async def list_users(
    skip: int = Query(0, ge=0, description="Skip n records"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
    role: str | None = Query(None, description="Filter by role"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of users with pagination and filtering.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return (1-100)
    - **role**: Filter by user role (optional)
    """
    statement = select(User).where(User.deleted_at == None)
    
    if role:
        statement = statement.where(User.role == role)
    
    statement = statement.offset(skip).limit(limit)
    users = session.exec(statement).all()
    return users

# Get Single User
@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        200: {"description": "User found"},
        401: {"description": "Unauthorized"},
        404: {"description": "User not found"}
    }
)
async def get_user(
    user_id: int = Query(..., gt=0, description="User ID"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    user = session.get(User, user_id)
    
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# Create User
@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user"
)
async def create_user(
    user_in: UserCreate,
    session: Session = Depends(get_session)
):
    """Create new user account"""
    # Check email uniqueness
    existing = session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create user
    user = await user_service.create_user(user_in, session)
    return user

# Update User
@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user"
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update user information"""
    # Authorization check
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = session.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = await user_service.update_user(user, user_in, session)
    return user

# Partial Update (PATCH)
@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Partially update user"
)
async def patch_user(
    user_id: int,
    updates: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Partially update user fields"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only provided fields
    for field, value in updates.items():
        if value is not None:
            setattr(user, field, value)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# Delete User
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user"
)
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin)
):
    """Delete user (admin only)"""
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete
    user.deleted_at = datetime.utcnow()
    session.add(user)
    session.commit()
```

## Error Handling

### Unified Error Response

```python
from pydantic import BaseModel
from typing import Any

class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    request_id: str | None = None
    timestamp: str | None = None

# Custom exception
class APIException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

# Exception handler
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "request_id": request.headers.get("x-request-id")
        }
    )

# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )
```

## Pagination Pattern

```python
from pydantic import BaseModel

class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 10

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    skip: int
    limit: int
    pages: int

def paginate(
    query,
    skip: int = 0,
    limit: int = 10,
    session: Session = None
):
    """Generic pagination utility"""
    total = session.query(query).count()
    items = session.exec(
        query.offset(skip).limit(limit)
    ).all()
    
    pages = (total + limit - 1) // limit
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "pages": pages
    }
```

## Filtering & Sorting

```python
from enum import Enum

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

@router.get("/")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    session: Session = Depends(get_session)
):
    """List items with search, filter, and sort"""
    
    statement = select(Item)
    
    # Search
    if search:
        statement = statement.where(
            or_(
                Item.name.ilike(f"%{search}%"),
                Item.description.ilike(f"%{search}%")
            )
        )
    
    # Sort
    sort_column = getattr(Item, sort_by, Item.created_at)
    if sort_order == SortOrder.DESC:
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())
    
    # Pagination
    statement = statement.offset(skip).limit(limit)
    
    items = session.exec(statement).all()
    return items
```

## Bulk Operations

```python
@router.post("/bulk/create")
async def bulk_create_items(
    items: List[ItemCreate],
    session: Session = Depends(get_session)
):
    """Create multiple items"""
    new_items = [Item(**item.dict()) for item in items]
    
    session.add_all(new_items)
    session.commit()
    
    for item in new_items:
        session.refresh(item)
    
    return new_items

@router.post("/bulk/update")
async def bulk_update_items(
    updates: List[dict],
    session: Session = Depends(get_session)
):
    """Update multiple items"""
    updated_items = []
    
    for update in updates:
        item_id = update.pop("id")
        item = session.get(Item, item_id)
        
        if item:
            for key, value in update.items():
                setattr(item, key, value)
            updated_items.append(item)
    
    session.add_all(updated_items)
    session.commit()
    
    return updated_items

@router.post("/bulk/delete")
async def bulk_delete_items(
    item_ids: List[int],
    session: Session = Depends(get_session)
):
    """Delete multiple items"""
    items = session.exec(
        select(Item).where(Item.id.in_(item_ids))
    ).all()
    
    for item in items:
        session.delete(item)
    
    session.commit()
    return {"deleted": len(items)}
```

## Export/Download Endpoints

```python
from fastapi.responses import StreamingResponse
import csv
import io

@router.get("/export/csv")
async def export_csv(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin)
):
    """Export users as CSV"""
    
    users = session.exec(select(User)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["ID", "Email", "Full Name", "Role", "Created At"])
    
    # Write data
    for user in users:
        writer.writerow([
            user.id,
            user.email,
            user.full_name,
            user.role,
            user.created_at.isoformat()
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
```

## Versioning

```python
from fastapi import APIRouter

# API v1
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/users")
async def list_users_v1(...):
    # V1 implementation
    pass

# API v2 (future)
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/users")
async def list_users_v2(...):
    # V2 implementation with new schema
    pass

app.include_router(v1_router)
app.include_router(v2_router)
```

## OpenAPI Documentation

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="My API",
        version="1.0.0",
        description="Complete API documentation",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://yourdomain.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```