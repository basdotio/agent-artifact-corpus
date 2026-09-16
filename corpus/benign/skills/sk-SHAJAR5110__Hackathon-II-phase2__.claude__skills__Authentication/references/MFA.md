# Multi-Factor Authentication (MFA)

## TOTP (Time-based One-Time Password)

### Setup

```bash
pip install pyotp qrcode
npm install speakeasy qrcode
```

### Generate Secret

```python
import pyotp

def generate_totp_secret():
    secret = pyotp.random_base32()
    return secret

def get_provisioning_uri(secret, email, issuer="MyApp"):
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)

# User scans QR code with Google Authenticator
def get_qr_code(secret, email):
    uri = get_provisioning_uri(secret, email)
    qr = qrcode.QRCode()
    qr.add_data(uri)
    qr.make()
    return qr
```

### Verify Token

```python
def verify_totp(secret, token):
    totp = pyotp.TOTP(secret)
    # Allow for time drift (30 seconds)
    return totp.verify(token, valid_window=1)

@app.post("/auth/mfa/verify")
async def verify_mfa(
    token: str,
    current_user: User = Depends(get_current_user)
):
    if not verify_totp(current_user.totp_secret, token):
        raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    return {"message": "MFA verified"}
```

## Email/SMS OTP

### Email OTP

```python
from random import randint

def generate_otp():
    return str(randint(100000, 999999))

def send_otp_email(email: str, otp: str):
    # Using SendGrid or similar
    message = f"Your OTP is: {otp}"
    send_email(to=email, subject="Your OTP", body=message)

@app.post("/auth/mfa/send-otp")
async def send_otp(
    current_user: User = Depends(get_current_user)
):
    otp = generate_otp()
    
    # Store OTP with expiration (5 minutes)
    store_otp(current_user.id, otp, expires_in=300)
    
    # Send via email
    send_otp_email(current_user.email, otp)
    
    return {"message": "OTP sent"}

@app.post("/auth/mfa/verify-otp")
async def verify_otp(
    otp: str,
    current_user: User = Depends(get_current_user)
):
    if not verify_otp_token(current_user.id, otp):
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    # Mark OTP as used
    mark_otp_used(current_user.id, otp)
    
    return {"message": "OTP verified"}
```

### SMS OTP (Twilio)

```python
from twilio.rest import Client

account_sid = "xxx"
auth_token = "xxx"
client = Client(account_sid, auth_token)

def send_sms_otp(phone: str, otp: str):
    message = client.messages.create(
        body=f"Your OTP is: {otp}",
        from_="+1234567890",
        to=phone
    )
    return message.sid

@app.post("/auth/mfa/send-sms")
async def send_sms_otp(
    current_user: User = Depends(get_current_user)
):
    otp = generate_otp()
    store_otp(current_user.id, otp, expires_in=300)
    send_sms_otp(current_user.phone, otp)
    
    return {"message": "OTP sent via SMS"}
```

## Backup Codes

```python
import secrets

def generate_backup_codes(count=10):
    codes = [secrets.token_hex(4) for _ in range(count)]
    return codes

def hash_backup_code(code: str):
    return hashlib.sha256(code.encode()).hexdigest()

@app.post("/auth/mfa/setup")
async def setup_mfa(
    current_user: User = Depends(get_current_user)
):
    # Generate TOTP secret
    secret = generate_totp_secret()
    
    # Generate backup codes
    codes = generate_backup_codes()
    hashed_codes = [hash_backup_code(code) for code in codes]
    
    # Store in database
    store_mfa_setup(
        current_user.id,
        totp_secret=secret,
        backup_codes=hashed_codes
    )
    
    return {
        "secret": secret,
        "backup_codes": codes,  # Only show once!
        "qr_code_uri": get_provisioning_uri(secret, current_user.email)
    }

@app.post("/auth/mfa/verify-backup")
async def verify_backup_code(
    code: str,
    current_user: User = Depends(get_current_user)
):
    hashed = hash_backup_code(code)
    
    if not verify_backup_code(current_user.id, hashed):
        raise HTTPException(status_code=401, detail="Invalid backup code")
    
    # Mark as used
    mark_backup_code_used(current_user.id, hashed)
    
    return {"message": "Backup code verified"}
```

## WebAuthn/FIDO2

```python
from webauthn import (
    generate_registration_data,
    verify_registration_response,
    generate_authentication_data,
    verify_authentication_response
)

@app.post("/auth/webauthn/register")
async def register_webauthn(
    credential: RegistrationResponse,
    current_user: User = Depends(get_current_user)
):
    # Verify credential
    verified = verify_registration_response(
        credential=credential,
        expected_challenge=get_stored_challenge(current_user.id),
        expected_origin="https://yourdomain.com",
        expected_rp_id="yourdomain.com"
    )
    
    # Store credential
    store_webauthn_credential(
        current_user.id,
        credential_id=verified.credential_id,
        credential_public_key=verified.credential_public_key
    )
    
    return {"message": "WebAuthn registered"}

@app.post("/auth/webauthn/authenticate")
async def authenticate_webauthn(
    assertion: AuthenticationResponse
):
    # Find credential
    credential = find_credential_by_id(assertion.credential_id)
    
    # Verify assertion
    verified = verify_authentication_response(
        credential=assertion,
        credential_public_key=credential.public_key,
        expected_challenge=get_stored_challenge(credential.user_id)
    )
    
    # Create session
    token = create_access_token({"sub": str(credential.user_id)})
    
    return {"access_token": token}
```

## Risk-Based Authentication

Require stronger MFA for sensitive operations:

```python
@app.post("/auth/sensitive-action")
async def sensitive_action(
    current_user: User = Depends(get_current_user),
    mfa_verified: bool = Depends(check_mfa)
):
    """Require MFA for sensitive operations"""
    # Only accessible if MFA verified in this session
    ...

def check_mfa(request: Request):
    # Check if user verified MFA in last 5 minutes
    mfa_timestamp = request.session.get("mfa_verified_at")
    
    if not mfa_timestamp:
        raise HTTPException(status_code=401, detail="MFA required")
    
    if datetime.utcnow() - mfa_timestamp > timedelta(minutes=5):
        raise HTTPException(status_code=401, detail="MFA expired")
    
    return True
```

## MFA Recovery

```python
@app.post("/auth/mfa/recovery")
async def initiate_mfa_recovery(email: str):
    """Send recovery code to email"""
    user = get_user_by_email(email)
    
    recovery_code = secrets.token_urlsafe(32)
    store_recovery_code(user.id, recovery_code)
    
    send_email(
        to=email,
        subject="Account Recovery",
        body=f"Recovery code: {recovery_code}"
    )
    
    return {"message": "Recovery code sent"}

@app.post("/auth/mfa/recover")
async def recover_account(
    email: str,
    recovery_code: str
):
    """Use recovery code to bypass MFA"""
    user = get_user_by_email(email)
    
    if not verify_recovery_code(user.id, recovery_code):
        raise HTTPException(status_code=401, detail="Invalid recovery code")
    
    # Issue temporary token (limited privileges)
    token = create_access_token({
        "sub": str(user.id),
        "limited": True
    })
    
    return {
        "access_token": token,
        "message": "Requires MFA reset"
    }
```