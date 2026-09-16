# Payment Integration Guide

## Stripe Integration

### Installation & Setup

```bash
pip install stripe
```

### Configuration

```python
# app/config.py
import stripe
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str
    stripe_api_version: str = "2023-10-16"

settings = Settings()
stripe.api_key = settings.stripe_secret_key
stripe.api_version = settings.stripe_api_version
```

### Payment Models

```python
# app/models/payment.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    STRIPE = "stripe"
    JAZZ_CASH = "jazz_cash"
    EASY_PAISA = "easy_paisa"

class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    amount: float = Field(gt=0)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, index=True)
    payment_method: PaymentMethod
    
    # Payment provider identifiers
    stripe_payment_id: Optional[str] = Field(default=None, unique=True, index=True)
    stripe_customer_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    
    jazz_cash_reference: Optional[str] = Field(default=None, unique=True)
    easy_paisa_reference: Optional[str] = Field(default=None, unique=True)
    
    # Metadata
    description: Optional[str] = None
    metadata: Optional[dict] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Relationships
    user: User = Relationship(back_populates="payments")
    order: Optional["Order"] = Relationship(back_populates="payment")

class PaymentCreate(SQLModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="usd")
    description: Optional[str] = None
    metadata: Optional[dict] = None

class PaymentResponse(SQLModel):
    id: int
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    created_at: datetime
```

### Stripe Checkout Session

```python
# app/routes/payments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
import stripe
from app.models.payment import Payment, PaymentCreate, PaymentStatus, PaymentMethod
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_session
from app.config import settings

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

class CheckoutSessionRequest(SQLModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="usd")
    description: str
    success_url: str
    cancel_url: str

@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create Stripe checkout session"""
    
    try:
        # Get or create Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            session.add(current_user)
            session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": request.currency.lower(),
                    "unit_amount": int(request.amount * 100),
                    "product_data": {
                        "name": request.description,
                    }
                },
                "quantity": 1
            }],
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={"user_id": current_user.id}
        )
        
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            amount=request.amount,
            currency=request.currency,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            stripe_payment_id=checkout_session.id,
            description=request.description
        )
        session.add(payment)
        session.commit()
        
        return {
            "session_id": checkout_session.id,
            "url": checkout_session.url,
            "payment_id": payment.id
        }
        
    except stripe.error.CardError as e:
        raise HTTPException(status_code=402, detail=f"Card error: {e.user_message}")
    except stripe.error.StripeAPIError as e:
        raise HTTPException(status_code=500, detail="Payment processing error")
```

### Webhook Handler

```python
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        await handle_checkout_completed(event["data"]["object"], session)
    
    # Handle payment_intent.succeeded
    elif event["type"] == "payment_intent.succeeded":
        await handle_payment_succeeded(event["data"]["object"], session)
    
    # Handle charge.refunded
    elif event["type"] == "charge.refunded":
        await handle_charge_refunded(event["data"]["object"], session)
    
    # Handle charge.dispute.created
    elif event["type"] == "charge.dispute.created":
        await handle_dispute_created(event["data"]["object"], session)
    
    logger.info(f"Processed webhook: {event['type']}")
    return {"status": "received"}

async def handle_checkout_completed(checkout_session: dict, session: Session):
    """Process successful checkout"""
    
    payment = session.exec(
        select(Payment).where(Payment.stripe_payment_id == checkout_session["id"])
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found for session: {checkout_session['id']}")
        return
    
    payment.status = PaymentStatus.PROCESSING
    payment.stripe_charge_id = checkout_session.get("payment_intent")
    session.add(payment)
    session.commit()
    
    # Update order status if exists
    if payment.order:
        payment.order.status = "processing"
        session.add(payment.order)
        session.commit()
    
    # Send confirmation email
    await send_payment_confirmation_email(payment)

async def handle_payment_succeeded(payment_intent: dict, session: Session):
    """Update payment when intent succeeds"""
    
    payment = session.exec(
        select(Payment).where(Payment.stripe_payment_id == payment_intent["id"])
    ).first()
    
    if payment:
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        session.add(payment)
        session.commit()

async def handle_charge_refunded(charge: dict, session: Session):
    """Handle refund"""
    
    payment = session.exec(
        select(Payment).where(Payment.stripe_charge_id == charge["id"])
    ).first()
    
    if payment:
        payment.status = PaymentStatus.REFUNDED
        session.add(payment)
        session.commit()

async def handle_dispute_created(dispute: dict, session: Session):
    """Log dispute for manual review"""
    logger.warning(f"Dispute created: {dispute['id']} - Amount: {dispute['amount']}")
```

### Refund Implementation

```python
@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Issue refund for a payment"""
    
    payment = session.get(Payment, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Only allow refunds within 90 days
    if (datetime.utcnow() - payment.created_at).days > 90:
        raise HTTPException(status_code=400, detail="Refund period expired")
    
    # Only owner or admin can refund
    if current_user.id != payment.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        refund = stripe.Refund.create(
            charge=payment.stripe_charge_id,
            reason="requested_by_customer",
            metadata={"payment_id": payment.id}
        )
        
        payment.status = PaymentStatus.REFUNDED
        payment.metadata = payment.metadata or {}
        payment.metadata["refund_id"] = refund.id
        session.add(payment)
        session.commit()
        
        return {"refund_id": refund.id, "amount": refund.amount / 100}
        
    except stripe.error.StripeAPIError as e:
        logger.error(f"Refund failed: {e}")
        raise HTTPException(status_code=500, detail="Refund failed")
```

## JazzCash Integration (Pakistan)

### Setup

```python
# app/services/jazz_cash_service.py
import hmac
import hashlib
import requests
from datetime import datetime
from app.config import settings

class JazzCashService:
    def __init__(self):
        self.merchant_id = settings.jazz_cash_merchant_id
        self.password = settings.jazz_cash_password
        self.base_url = "https://secure.jazzcash.com.pk/ApplicationAPI/API/"
        self.test_url = "https://sandbox.jazzcash.com.pk/ApplicationAPI/API/"
    
    def _generate_signature(self, auth_code: str, amount: str) -> str:
        """Generate JazzCash signature"""
        plain_text = f"{self.merchant_id}{auth_code}{amount}{self.password}"
        return hashlib.sha256(plain_text.encode()).hexdigest()
    
    def create_payment_request(
        self,
        user_id: int,
        amount: float,
        phone: str,
        description: str
    ) -> dict:
        """Create JazzCash payment request"""
        
        from app.models.payment import Payment
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        auth_code = "AUTH_" + timestamp
        amount_str = str(int(amount * 100))  # Convert to paisa
        
        signature = self._generate_signature(auth_code, amount_str)
        
        payload = {
            "pp_merchant_id": self.merchant_id,
            "pp_auth_code": auth_code,
            "pp_amount": amount_str,
            "pp_bill_reference": f"ORDER_{user_id}_{timestamp}",
            "pp_description": description,
            "pp_return_url": settings.jazz_cash_return_url,
            "pp_notify_url": settings.jazz_cash_notify_url,
            "pp_sign": signature,
            "pp_txn_datetime": timestamp,
            "pp_language": "en"
        }
        
        return {
            "form_url": self.test_url if settings.environment == "development" else self.base_url,
            "payload": payload
        }
    
    def verify_transaction(self, transaction_id: str) -> dict:
        """Verify JazzCash transaction status"""
        
        payload = {
            "pp_merchant_id": self.merchant_id,
            "pp_txn_id": transaction_id,
            "pp_language": "en"
        }
        
        signature = hashlib.sha256(
            f"{self.merchant_id}{transaction_id}{self.password}".encode()
        ).hexdigest()
        payload["pp_sign"] = signature
        
        try:
            response = requests.post(
                self.test_url + "TransactionStatus.php" if settings.environment == "development" else self.base_url + "TransactionStatus.php",
                data=payload,
                timeout=10
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"JazzCash verification error: {e}")
            return {"error": str(e)}
```

### JazzCash Payment Endpoint

```python
@router.post("/jazz-cash/initiate")
async def initiate_jazz_cash_payment(
    request: PaymentCreate,
    phone: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Initiate JazzCash payment"""
    
    from app.services.jazz_cash_service import JazzCashService
    
    service = JazzCashService()
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=request.amount,
        currency="pkr",
        payment_method=PaymentMethod.JAZZ_CASH,
        status=PaymentStatus.PENDING,
        description=request.description
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    
    # Generate JazzCash form
    form_data = service.create_payment_request(
        current_user.id,
        request.amount,
        phone,
        request.description
    )
    
    return {
        "payment_id": payment.id,
        "form_url": form_data["form_url"],
        "payload": form_data["payload"]
    }

@router.post("/jazz-cash/notify")
async def jazz_cash_notify(
    request: Request,
    session: Session = Depends(get_session)
):
    """Handle JazzCash notification"""
    
    data = await request.json()
    
    payment = session.exec(
        select(Payment).where(Payment.jazz_cash_reference == data.get("pp_txn_id"))
    ).first()
    
    if not payment:
        return {"status": "error"}
    
    status_code = data.get("pp_response_code")
    
    if status_code == "000":  # Success
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
    else:
        payment.status = PaymentStatus.FAILED
    
    session.add(payment)
    session.commit()
    
    return {"status": "received"}
```

## EasyPaisa Integration (Pakistan)

### Setup

```python
# app/services/easy_paisa_service.py
import requests
import json
from datetime import datetime
from app.config import settings

class EasyPaisaService:
    def __init__(self):
        self.store_id = settings.easy_paisa_store_id
        self.store_password = settings.easy_paisa_store_password
        self.base_url = "https://easypaisaapi.easypaisa.com.pk"
        self.test_url = "https://sandbox.easypaisa.com.pk"
    
    def initiate_payment(
        self,
        amount: float,
        phone: str,
        order_id: str,
        customer_name: str
    ) -> dict:
        """Initiate EasyPaisa payment"""
        
        url = f"{self.test_url if settings.environment == 'development' else self.base_url}/api/Payment/InitiatePayment"
        
        payload = {
            "storeId": self.store_id,
            "storeName": "MyStore",
            "amount": int(amount * 100),  # In paisas
            "mobileNumber": phone,
            "transactionId": order_id,
            "transactionDetails": f"Payment for {order_id}",
            "customerName": customer_name,
            "customerEmail": "",
            "notificationURL": settings.easy_paisa_notify_url,
            "transactionRefId": "",
            "sessionId": ""
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=(self.store_id, self.store_password),
                timeout=10
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"EasyPaisa error: {e}")
            return {"error": str(e)}
    
    def verify_transaction(self, transaction_id: str) -> dict:
        """Verify EasyPaisa transaction"""
        
        url = f"{self.test_url if settings.environment == 'development' else self.base_url}/api/Payment/GetTransactionStatus"
        
        payload = {
            "storeId": self.store_id,
            "transactionId": transaction_id
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=(self.store_id, self.store_password),
                timeout=10
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"EasyPaisa verification error: {e}")
            return {"error": str(e)}
```

### EasyPaisa Payment Endpoint

```python
@router.post("/easy-paisa/initiate")
async def initiate_easy_paisa_payment(
    request: PaymentCreate,
    phone: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Initiate EasyPaisa payment"""
    
    from app.services.easy_paisa_service import EasyPaisaService
    
    service = EasyPaisaService()
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=request.amount,
        currency="pkr",
        payment_method=PaymentMethod.EASY_PAISA,
        status=PaymentStatus.PENDING,
        description=request.description
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    
    # Initiate EasyPaisa payment
    result = service.initiate_payment(
        request.amount,
        phone,
        f"ORD_{payment.id}_{datetime.utcnow().timestamp()}",
        current_user.full_name
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail="Failed to initiate payment")
    
    payment.easy_paisa_reference = result.get("transactionId")
    session.add(payment)
    session.commit()
    
    return result

@router.post("/easy-paisa/notify")
async def easy_paisa_notify(
    request: Request,
    session: Session = Depends(get_session)
):
    """Handle EasyPaisa notification"""
    
    data = await request.json()
    
    payment = session.exec(
        select(Payment).where(Payment.easy_paisa_reference == data.get("transactionId"))
    ).first()
    
    if not payment:
        return {"status": "error"}
    
    if data.get("transactionStatus") == "success":
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
    else:
        payment.status = PaymentStatus.FAILED
    
    session.add(payment)
    session.commit()
    
    return {"status": "received"}
```

## Payment Status Tracking

```python
@router.get("/payments/{payment_id}")
async def get_payment_status(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get payment status"""
    
    payment = session.get(Payment, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # For Stripe, check actual status
    if payment.payment_method == PaymentMethod.STRIPE and payment.stripe_payment_id:
        try:
            session_data = stripe.checkout.Session.retrieve(payment.stripe_payment_id)
            if session_data.payment_status == "paid" and payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                session.add(payment)
                session.commit()
        except stripe.error.StripeAPIError:
            pass
    
    return PaymentResponse.from_orm(payment)
```

## Error Handling

```python
class PaymentError(Exception):
    def __init__(self, message: str, payment_id: int = None):
        self.message = message
        self.payment_id = payment_id
        super().__init__(self.message)

@app.exception_handler(PaymentError)
async def payment_error_handler(request: Request, exc: PaymentError):
    logger.error(f"Payment error for payment {exc.payment_id}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message}
    )
```