import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Index, inspect, select, func, or_, text
from sqlalchemy.exc import SQLAlchemyError

# Initialize FastMCP Server
mcp = FastMCP(
    "Arzonama-DB-Manager",
    instructions="FastMCP server providing MCP tools and HTTP routes for managing the SQLite database"
)

# Database Connection
DB_PATH = Path(__file__).parent / "arzonama.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
metadata = MetaData()
user_table = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("full_name", String, nullable=False),
    Column("email", String, nullable=False),
    Column("password", String(255), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_premium", Boolean, nullable=False, default=False)
)
Index("ix_user_email", user_table.c.email)
metadata.create_all(engine, checkfirst=True)

def _serialize_row(row_dict: dict[str, Any]) -> dict[str, Any]:
    """Helper to convert non-JSON serializable types like datetime into strings."""
    serialized = {}
    for k, v in row_dict.items():
        if isinstance(v, datetime):
            serialized[k] = v.isoformat()
        else:
            serialized[k] = v
    return serialized

# ============================================================================
# Core Database Logic (Used by both FastMCP Tools and Custom HTTP Handlers)
# ============================================================================

def get_stats_logic() -> dict[str, Any]:
    """Calculates database stats and table summaries."""
    with engine.connect() as conn:
        total_users = conn.execute(select(func.count(user_table.c.id))).scalar() or 0
        premium_users = conn.execute(
            select(func.count(user_table.c.id)).where(user_table.c.is_premium == True)
        ).scalar() or 0
        newest_user = conn.execute(
            select(user_table.c.created_at).order_by(user_table.c.id.desc()).limit(1)
        ).scalar()

        file_size_bytes = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    return {
        "database": "arzonama.db",
        "file_size_mb": file_size_mb,
        "total_users": total_users,
        "premium_users": premium_users,
        "standard_users": total_users - premium_users,
        "newest_signup": newest_user.isoformat() if isinstance(newest_user, datetime) else str(newest_user) if newest_user else None
    }

def inspect_schema_logic() -> dict[str, Any]:
    """Inspects SQLite schema, tables, columns, indexes, and primary keys."""
    insp = inspect(engine)
    tables_info = {}

    for table_name in insp.get_table_names():
        columns = []
        for col in insp.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "primary_key": bool(col.get("primary_key", False)),
                "default": str(col.get("default")) if col.get("default") is not None else None
            })
        indexes = []
        for idx in insp.get_indexes(table_name):
            indexes.append({
                "name": idx.get("name"),
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False)
            })

        tables_info[table_name] = {
            "columns": columns,
            "indexes": indexes
        }

    return {"tables": tables_info}

def list_users_logic(limit: int = 50, offset: int = 0, search: str = "", is_premium: Optional[bool] = None) -> dict[str, Any]:
    """Lists users with filtering and pagination."""
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    conditions = []
    if search:
        search_filter = f"%{search}%"
        conditions.append(or_(
            user_table.c.full_name.ilike(search_filter),
            user_table.c.email.ilike(search_filter)
        ))
    if is_premium is not None:
        conditions.append(user_table.c.is_premium == is_premium)

    query = select(
        user_table.c.id,
        user_table.c.full_name,
        user_table.c.email,
        user_table.c.created_at,
        user_table.c.is_premium
    ).order_by(user_table.c.id.desc()).limit(limit).offset(offset)

    count_query = select(func.count(user_table.c.id))

    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)

    with engine.connect() as conn:
        total = conn.execute(count_query).scalar() or 0
        rows = conn.execute(query).fetchall()
        items = [_serialize_row(dict(r._mapping)) for r in rows]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

def get_user_logic(user_id: int) -> Optional[dict[str, Any]]:
    """Retrieves a single user by ID."""
    query = select(
        user_table.c.id,
        user_table.c.full_name,
        user_table.c.email,
        user_table.c.created_at,
        user_table.c.is_premium
    ).where(user_table.c.id == user_id)

    with engine.connect() as conn:
        row = conn.execute(query).fetchone()
        if not row:
            return None
        return _serialize_row(dict(row._mapping))

def create_user_logic(full_name: str, email: str, password: str, is_premium: bool = False) -> dict[str, Any]:
    """Creates a new user record with SHA-256 hashed password."""
    email = email.strip().lower()
    full_name = full_name.strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    with engine.begin() as conn:
        existing = conn.execute(select(user_table.c.id).where(user_table.c.email == email)).first()
        if existing:
            raise ValueError(f"User with email '{email}' already exists.")

        result = conn.execute(
            user_table.insert().values(
                full_name=full_name,
                email=email,
                password=hashed_password,
                is_premium=is_premium
            )
        )
        new_id = result.inserted_primary_key[0]

    return {
        "message": "User created successfully",
        "user_id": new_id,
        "full_name": full_name,
        "email": email,
        "is_premium": is_premium
    }

def update_user_logic(user_id: int, full_name: Optional[str] = None, email: Optional[str] = None, is_premium: Optional[bool] = None, password: Optional[str] = None) -> dict[str, Any]:
    """Updates user information."""
    values_to_update = {}
    if full_name is not None:
        values_to_update["full_name"] = full_name.strip()
    if email is not None:
        values_to_update["email"] = email.strip().lower()
    if is_premium is not None:
        values_to_update["is_premium"] = is_premium
    if password is not None:
        values_to_update["password"] = hashlib.sha256(password.encode()).hexdigest()

    if not values_to_update:
        return {"message": "No fields to update", "user_id": user_id}

    with engine.begin() as conn:
        existing = conn.execute(select(user_table.c.id).where(user_table.c.id == user_id)).first()
        if not existing:
            raise LookupError(f"User with ID {user_id} not found.")

        if "email" in values_to_update:
            email_check = conn.execute(
                select(user_table.c.id).where(
                    (user_table.c.email == values_to_update["email"]) & (user_table.c.id != user_id)
                )
            ).first()
            if email_check:
                raise ValueError(f"Email '{values_to_update['email']}' is already in use by another user.")

        conn.execute(
            user_table.update().where(user_table.c.id == user_id).values(**values_to_update)
        )

    return {
        "message": "User updated successfully",
        "user_id": user_id,
        "updated_fields": list(values_to_update.keys())
    }

def delete_user_logic(user_id: int) -> dict[str, Any]:
    """Deletes a user by ID."""
    with engine.begin() as conn:
        existing = conn.execute(select(user_table.c.id).where(user_table.c.id == user_id)).first()
        if not existing:
            raise LookupError(f"User with ID {user_id} not found.")

        conn.execute(user_table.delete().where(user_table.c.id == user_id))

    return {"message": "User deleted successfully", "user_id": user_id}

def execute_readonly_query_logic(sql_query: str) -> dict[str, Any]:
    """Safely executes read-only SELECT queries."""
    clean_sql = sql_query.strip()
    first_word = clean_sql.split()[0].upper() if clean_sql else ""

    if first_word not in ("SELECT", "PRAGMA", "EXPLAIN"):
        raise ValueError("Only read-only queries (SELECT, PRAGMA, EXPLAIN) are allowed.")

    with engine.connect() as conn:
        result = conn.execute(text(clean_sql))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchmany(100)]  # Cap at 100 rows for safety

    # Format datetimes
    formatted_rows = []
    for row in rows:
        formatted_row = [v.isoformat() if isinstance(v, datetime) else v for v in row]
        formatted_rows.append(formatted_row)

    return {
        "query": clean_sql,
        "columns": columns,
        "rows": formatted_rows,
        "row_count": len(formatted_rows)
    }

# ============================================================================
# FastMCP Tools (Callable by LLMs and MCP clients over MCP protocol)
# ============================================================================

@mcp.tool()
def get_database_stats() -> dict[str, Any]:
    """Get high-level statistics about the SQLite database (user count, premium users, file size)."""
    return get_stats_logic()

@mcp.tool()
def inspect_database_schema() -> dict[str, Any]:
    """Inspect tables, column names, data types, indexes, and constraints in the database."""
    return inspect_schema_logic()

@mcp.tool()
def list_users(limit: int = 20, offset: int = 0, search: str = "", is_premium: Optional[bool] = None) -> dict[str, Any]:
    """Search and paginate through users in the database by full_name or email."""
    return list_users_logic(limit=limit, offset=offset, search=search, is_premium=is_premium)

@mcp.tool()
def get_user_by_id(user_id: int) -> dict[str, Any]:
    """Retrieve full details of a specific user by their numerical ID."""
    user = get_user_logic(user_id)
    if not user:
        return {"error": f"User {user_id} not found"}
    return user

@mcp.tool()
def create_new_user(full_name: str, email: str, password: str, is_premium: bool = False) -> dict[str, Any]:
    """Add a new user to the database with hashed password."""
    try:
        return create_user_logic(full_name=full_name, email=email, password=password, is_premium=is_premium)
    except ValueError as e:
        return {"error": str(e)}

@mcp.tool()
def update_user(user_id: int, full_name: Optional[str] = None, email: Optional[str] = None, is_premium: Optional[bool] = None) -> dict[str, Any]:
    """Update user information such as full_name, email, or premium membership."""
    try:
        return update_user_logic(user_id=user_id, full_name=full_name, email=email, is_premium=is_premium)
    except (ValueError, LookupError) as e:
        return {"error": str(e)}

@mcp.tool()
def delete_user(user_id: int) -> dict[str, Any]:
    """Remove a user from the database by ID."""
    try:
        return delete_user_logic(user_id)
    except LookupError as e:
        return {"error": str(e)}

@mcp.tool()
def run_readonly_sql(sql_query: str) -> dict[str, Any]:
    """Execute a read-only SELECT or PRAGMA SQL query to inspect data safely."""
    try:
        return execute_readonly_query_logic(sql_query)
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# Custom HTTP Endpoints (Direct REST API routes on FastMCP server)
# ============================================================================

@mcp.custom_route("/db/stats", methods=["GET"])
async def http_get_stats(request: Request) -> JSONResponse:
    """HTTP GET: Return database statistics."""
    return JSONResponse(get_stats_logic())

@mcp.custom_route("/db/schema", methods=["GET"])
async def http_get_schema(request: Request) -> JSONResponse:
    """HTTP GET: Return database schema introspection."""
    return JSONResponse(inspect_schema_logic())

@mcp.custom_route("/db/users", methods=["GET"])
async def http_list_users(request: Request) -> JSONResponse:
    """HTTP GET: Paginated list and search of users."""
    limit = int(request.query_params.get("limit", 50))
    offset = int(request.query_params.get("offset", 0))
    search = request.query_params.get("search", "")
    is_premium_param = request.query_params.get("is_premium")
    is_premium = None
    if is_premium_param is not None:
        is_premium = is_premium_param.lower() in ("true", "1")

    data = list_users_logic(limit=limit, offset=offset, search=search, is_premium=is_premium)
    return JSONResponse(data)

@mcp.custom_route("/db/users/{user_id:int}", methods=["GET"])
async def http_get_user(request: Request) -> JSONResponse:
    """HTTP GET: Fetch single user by ID."""
    user_id = int(request.path_params["user_id"])
    user = get_user_logic(user_id)
    if not user:
        return JSONResponse({"detail": f"User with ID {user_id} not found"}, status_code=404)
    return JSONResponse(user)

@mcp.custom_route("/db/users", methods=["POST"])
async def http_create_user(request: Request) -> JSONResponse:
    """HTTP POST: Create a new user."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    full_name = body.get("full_name")
    email = body.get("email")
    password = body.get("password")
    is_premium = bool(body.get("is_premium", False))

    if not full_name or not email or not password:
        return JSONResponse({"detail": "full_name, email, and password are required"}, status_code=400)

    try:
        result = create_user_logic(full_name=full_name, email=email, password=password, is_premium=is_premium)
        return JSONResponse(result, status_code=201)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    except SQLAlchemyError:
        return JSONResponse({"detail": "Database error occurred"}, status_code=500)

@mcp.custom_route("/db/users/{user_id:int}", methods=["PATCH", "PUT"])
async def http_update_user(request: Request) -> JSONResponse:
    """HTTP PATCH/PUT: Update user details."""
    user_id = int(request.path_params["user_id"])
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    try:
        result = update_user_logic(
            user_id=user_id,
            full_name=body.get("full_name"),
            email=body.get("email"),
            is_premium=body.get("is_premium"),
            password=body.get("password")
        )
        return JSONResponse(result)
    except LookupError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    except SQLAlchemyError:
        return JSONResponse({"detail": "Database error occurred"}, status_code=500)

@mcp.custom_route("/db/users/{user_id:int}", methods=["DELETE"])
async def http_delete_user(request: Request) -> JSONResponse:
    """HTTP DELETE: Remove user by ID."""
    user_id = int(request.path_params["user_id"])
    try:
        result = delete_user_logic(user_id)
        return JSONResponse(result)
    except LookupError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except SQLAlchemyError:
        return JSONResponse({"detail": "Database error occurred"}, status_code=500)

@mcp.custom_route("/db/query", methods=["POST"])
async def http_execute_query(request: Request) -> JSONResponse:
    """HTTP POST: Execute safe read-only SQL query."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    sql_query = body.get("query")
    if not sql_query:
        return JSONResponse({"detail": "'query' field is required"}, status_code=400)

    try:
        result = execute_readonly_query_logic(sql_query)
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)
    except SQLAlchemyError as e:
        return JSONResponse({"detail": f"SQL execution error: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    # Allows running standalone: python mcp_server.py
    mcp.run(transport="http", port=8001)
