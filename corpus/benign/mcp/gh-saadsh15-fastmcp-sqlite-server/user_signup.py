import hashlib
from pathlib import Path
from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Index, select, or_, func
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()
sa_engine = create_engine("sqlite:///arzonama.db")
metadata = MetaData()
users_table = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("full_name", String, nullable=False),
    Column("email", String, nullable=False),
    Column("password", String(255), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_premium", Boolean, nullable=False, default=False)
)
Index("ix_user_email", users_table.c.email)
metadata.create_all(sa_engine, checkfirst=True)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "signup.html"

# Schema to receive user credentials from frontend form
class UserCredentials(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

#add user to database
def add_user_to_db(first_name: str, last_name: str, email: str, password: str):
    full_name = f"{first_name.strip()} {last_name.strip()}".strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        with sa_engine.begin() as conn:
            query = select(users_table).where(users_table.c.email == email)
            result = conn.execute(query)
            if result.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

            #insert user into database
            conn.execute(users_table.insert().values(full_name=full_name, email=email, password=hashed_password))

        return {"message": "User registered successfully"}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred")

# GET endpoint: serve the HTML signup page from template file
@router.get("/signup")
def get_signup_page():
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup page template not found")
    return FileResponse(TEMPLATE_PATH, media_type="text/html")

# POST endpoint: handle user registration form submission
@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(credentials: UserCredentials):
    return add_user_to_db(
        first_name=credentials.first_name,
        last_name=credentials.last_name,
        email=credentials.email,
        password=credentials.password
    )

app = FastAPI()
app.include_router(router)