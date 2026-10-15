import yaml
import bcrypt
from yaml.loader import SafeLoader

USERS_FILE = "users.yaml"

def load_users():
    with open(USERS_FILE, "r") as f:
        return yaml.load(f, Loader=SafeLoader)

def save_users(config):
    with open(USERS_FILE, "w") as f:
        yaml.dump(config, f)

def register_user(username, name, email, password, role="applicant"):
    config = load_users()
    if "credentials" not in config:
        config["credentials"] = {"usernames": {}}
    if username in config["credentials"]["usernames"]:
        raise ValueError(f"Username '{username}' already exists!")
    
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    config["credentials"]["usernames"][username] = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role
    }
    # Ensure cookie section exists
    if "cookie" not in config:
        config["cookie"] = {
            "name": "credit-auth",
            "key": "credit-risk-app",
            "expiry_days": 1
        }
    save_users(config)
    return True

def verify_password(plain_password, hashed_password):
    """Verify a plain password against the hashed one."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())