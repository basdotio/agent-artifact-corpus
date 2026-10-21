import os, jwt
SECRET = os.environ["JWT_SECRET"]
def current_user(token: str) -> str:
    return jwt.decode(token, SECRET, algorithms=["HS256"])["sub"]
