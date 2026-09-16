# Cryptography Guide

## Symmetric Encryption
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"secret")
```

## Hashing
```python
import hashlib
h = hashlib.sha256(b"password").hexdigest()
```

## Best Practices
- Use AES-256-GCM for encryption
- Use Argon2id for password hashing
- Never roll your own crypto
