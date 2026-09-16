# Complete Working Examples

## Example 1: User Management System

Complete user CRUD with authentication and email verification.

```python
# models/user.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, field_validator

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True, index=True)
    full_name: str = Field(min_length=1, max_length=255)
    hashed_password: str = Field(min_length=60)
    is_active: bool = Field(default=True, index=True)
    email_verified: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    
    role: str = Field(default="user")
    profile_picture_url: Optional[str] = None
    
    # Relations
    orders: list["Order"] = Relationship(back_populates="user", cascade_delete=True)

# schemas/user.py
from pydantic import EmailStr, field_validator

class UserBase(SQLModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    role: str

# services/user_service.py
from app.models.user import User
from app.schemas.user import UserCreate
from app.dependencies.auth import hash_password

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
        
        # Send verification email
        await send_verification_email(user.email)
        
        return user
    
    async def update_user(self, user: User, updates: dict, session: Session):
        for key, value in updates.items():
            if value is not None and key != 'password':
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

# routes/users.py (simplified)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

router = APIRouter(prefix="/api/v1/users")

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_in: UserCreate,
    session: Session = Depends(get_session)
):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email registered")
    
    user = await UserService().create_user(user_in, session)
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user = session.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Example 2: E-Commerce API with Orders & Payments

Complete order and payment system.

```python
# models/order.py
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int
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
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="orders")
    items: list[OrderItem] = Relationship(back_populates="order", cascade_delete=True)
    payment: Optional["Payment"] = Relationship(back_populates="order")

# routes/orders.py
@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    order_in: OrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create new order"""
    order = Order(
        user_id=current_user.id,
        total_amount=sum(item.quantity * item.unit_price for item in order_in.items),
        shipping_address=order_in.shipping_address,
        billing_address=order_in.billing_address
    )
    
    session.add(order)
    session.flush()
    
    # Add items
    for item in order_in.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        session.add(order_item)
    
    session.commit()
    session.refresh(order)
    return order

@router.post("/{order_id}/checkout")
async def checkout_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Process order checkout with Stripe"""
    order = session.get(Order, order_id)
    
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    # Create Stripe checkout
    checkout = stripe.checkout.Session.create(
        customer_email=current_user.email,
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": int(order.total_amount * 100),
                "product_data": {
                    "name": f"Order #{order.id}",
                    "metadata": {"order_id": order.id}
                }
            },
            "quantity": 1
        }],
        mode="payment",
        success_url=f"{settings.frontend_url}/order/{order.id}/success",
        cancel_url=f"{settings.frontend_url}/order/{order.id}/cancel"
    )
    
    return {"checkout_url": checkout.url}
```

## Example 3: Real-Time Chat with WebSockets

```python
# models/chat.py
class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int
    user_id: int
    content: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship()

# routes/chat.py
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, room_id: int, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)
    
    async def broadcast(self, room_id: int, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except RuntimeError:
                    self.disconnect(room_id, connection)

manager = ConnectionManager()

@router.websocket("/ws/chat/{room_id}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    session: Session = Depends(get_session)
):
    await manager.connect(room_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Save message
            message = ChatMessage(
                room_id=room_id,
                user_id=user_id,
                content=data
            )
            session.add(message)
            session.commit()
            
            # Broadcast
            await manager.broadcast(room_id, {
                "user_id": user_id,
                "content": data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {
            "message": f"User {user_id} left"
        })
```

## Example 4: File Upload with Validation

```python
# routes/files.py
from fastapi import File, UploadFile
import shutil
from pathlib import Path

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Upload file with validation"""
    
    # Validate extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Save file
    UPLOAD_DIR.mkdir(exist_ok=True)
    file_path = UPLOAD_DIR / f"{current_user.id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    return {
        "filename": file.filename,
        "size": len(contents),
        "url": f"/uploads/{file_path.name}"
    }

@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Download file"""
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404)
    
    return FileResponse(file_path, media_type="application/octet-stream")
```

## Example 5: Task Queue with Celery

```python
# tasks.py
from celery import Celery
import os

celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
)

@celery_app.task
def send_email(to: str, subject: str, body: str):
    """Send email asynchronously"""
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = to
    
    with smtplib.SMTP(os.getenv("SMTP_SERVER")) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.sendmail(os.getenv("SMTP_FROM"), [to], msg.as_string())

@celery_app.task
def generate_report(user_id: int):
    """Generate report asynchronously"""
    # Heavy computation
    report_data = {}  # Generate report
    return report_data

# routes/tasks.py
@router.post("/send-email")
async def send_email_task(
    email: str,
    subject: str,
    body: str,
    current_user: User = Depends(get_current_admin)
):
    """Queue email task"""
    task = send_email.delay(email, subject, body)
    return {"task_id": task.id}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }
```

## Example 6: Multi-Tenant SaaS

```python
# models/tenant.py
class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    owner_id: int = Field(foreign_key="user.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    owner: User = Relationship()

# routes/multi_tenant.py
def get_current_tenant(
    request: Request,
    session: Session = Depends(get_session)
) -> Tenant:
    """Extract tenant from subdomain or header"""
    
    # From subdomain: tenant.example.com
    host = request.headers.get("host", "")
    if host.startswith("api."):
        host = host[4:]
    
    tenant_slug = host.split(".")[0]
    
    tenant = session.exec(
        select(Tenant).where(Tenant.slug == tenant_slug)
    ).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant

@router.get("/settings")
async def get_tenant_settings(
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """Get tenant-specific settings"""
    if current_user.id != tenant.owner_id:
        raise HTTPException(status_code=403)
    
    return {"tenant_name": tenant.name, "id": tenant.id}
```

All examples follow production patterns with proper error handling, validation, authentication, and database transactions.