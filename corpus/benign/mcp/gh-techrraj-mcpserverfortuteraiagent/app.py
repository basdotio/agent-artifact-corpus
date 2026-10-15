"""FastAPI multi-department RAG web app."""
import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv

from db import (
    init_db, insert_document, insert_embedding,
    search_similar, get_stats, chunk_text,
    create_user, get_user_by_email, list_all_users, delete_user,
    list_documents, delete_document, save_message, get_history, create_session,
    list_departments, create_department, get_department_by_id,
)
from llm_client import get_embedding, rag_query
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin,
)

load_dotenv()
init_db()


# ============================================================
# Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    if not get_user_by_email(admin_email):
        create_user(admin_email, hash_password(admin_password), role="admin", department_id=None)
        print(f"[OK] Default admin created: {admin_email} / {admin_password}")
    else:
        print(f"[OK] Admin user already exists: {admin_email}")
    yield
    print("[INFO] Shutting down...")


app = FastAPI(title="MCP RAG Web", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============================================================
# Models
# ============================================================
class RegisterRequest(BaseModel):
    email: str
    password: str
    department_id: int


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class CreateDepartmentRequest(BaseModel):
    name: str
    description: str = ""


# ============================================================
# Pages — using NEW Starlette 1.7 TemplateResponse API
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html")


# ============================================================
# Auth
# ============================================================
@app.post("/auth/register")
async def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(400, "Email already registered")
    if not get_department_by_id(req.department_id):
        raise HTTPException(400, "Invalid department")
    uid = create_user(
        req.email, hash_password(req.password),
        role="user", department_id=req.department_id
    )
    token = create_access_token({"sub": req.email})
    return {"access_token": token, "token_type": "bearer", "user_id": uid}


@app.post("/auth/login")
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@app.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "department_id": user["department_id"],
        "department_name": user["department_name"],
    }


# ============================================================
# Departments (public — for register page)
# ============================================================
@app.get("/departments")
async def departments():
    return {"departments": list_departments()}


# ============================================================
# Chat
# ============================================================
@app.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    sid = create_session(req.session_id)
    save_message(sid, "user", req.question)

    if user["role"] == "admin":
        dept_filter = None
    else:
        dept_filter = user["department_id"]

    docs = search_similar(
        get_embedding(req.question), top_k=5, department_id=dept_filter
    )

    if not docs:
        dept_name = user["department_name"] or "your department"
        answer = f"No relevant information found in the {dept_name} knowledge base. Please contact your admin to upload documents."
        sources = []
    else:
        answer = rag_query(req.question, docs)
        sources = [
            {"source": d["source"], "similarity": d["similarity"]}
            for d in docs
        ]

    save_message(sid, "assistant", answer)
    return {"answer": answer, "sources": sources, "session_id": sid}


@app.get("/chat/history/{session_id}")
async def history(session_id: str, user: dict = Depends(get_current_user)):
    return {"messages": get_history(session_id)}


# ============================================================
# Documents
# ============================================================
@app.get("/documents")
async def documents(department_id: int = None, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        department_id = user["department_id"]
    return {"documents": list_documents(department_id=department_id)}


@app.post("/documents/upload")
async def upload_document(
    content: str = Form(...),
    source: str = Form("manual"),
    department_id: int = Form(...),
    user: dict = Depends(get_current_user),
):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")

    if not get_department_by_id(department_id):
        raise HTTPException(400, "Invalid department")

    chunks = chunk_text(content)
    imported = 0
    for i, chunk in enumerate(chunks):
        doc_id = insert_document(
            chunk, source,
            {"chunk_index": i, "total_chunks": len(chunks)},
            department_id=department_id
        )
        insert_embedding(doc_id, get_embedding(chunk))
        imported += 1

    return {"imported": imported, "total_chunks": len(chunks)}


@app.delete("/documents/{doc_id}")
async def remove_document(doc_id: int, user: dict = Depends(require_admin)):
    delete_document(doc_id)
    return {"deleted": doc_id}


# ============================================================
# Admin
# ============================================================
@app.get("/admin/users")
async def admin_users(user: dict = Depends(require_admin)):
    return {"users": list_all_users()}


@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise HTTPException(400, "Cannot delete yourself")
    delete_user(user_id)
    return {"deleted": user_id}


@app.get("/admin/departments")
async def admin_list_departments(user: dict = Depends(require_admin)):
    return {"departments": list_departments()}


@app.post("/admin/departments")
async def admin_create_department(req: CreateDepartmentRequest,
                                  user: dict = Depends(require_admin)):
    dept_id = create_department(req.name, req.description)
    if not dept_id:
        raise HTTPException(400, "Department already exists")
    return {"id": dept_id, "name": req.name}


@app.get("/admin/stats")
async def admin_stats(department_id: int = None, user: dict = Depends(require_admin)):
    return get_stats(department_id=department_id)


# ============================================================
# Entry
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)