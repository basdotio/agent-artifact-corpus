"""PostgreSQL + pgvector database operations with multi-department support."""
import os
import uuid
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================================
# Init
# ============================================================
def init_db():
    """Create all tables and default data."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Departments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                department_id INTEGER REFERENCES departments(id),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Documents
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                source VARCHAR(255),
                metadata JSONB DEFAULT '{}',
                department_id INTEGER REFERENCES departments(id),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Embeddings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                embedding halfvec(2048),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # HNSW index
        conn.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx
            ON embeddings
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

        # Conversations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS conv_session_idx ON conversations(session_id)
        """)

        # Default departments
        defaults = [
            ("Legal", "Legal documents, contracts, case law"),
            ("Medical", "Medical records, symptoms, treatments"),
            ("HR", "HR policies, leave, benefits"),
            ("Engineering", "Technical docs, APIs, architecture"),
            ("Sales", "Product info, pricing, customer FAQs"),
            ("General", "General knowledge base"),
        ]
        for name, desc in defaults:
            conn.execute(
                "INSERT INTO departments (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                (name, desc)
            )

    print("[OK] Database initialized")


# ============================================================
# Chunking
# ============================================================
def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Sentence-aware chunking with overlap."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        boundary = -1
        for i in range(end, max(start + chunk_size // 2, end - 200), -1):
            if text[i] in '.!?\n':
                boundary = i + 1
                break

        actual_end = boundary if boundary > start else end
        chunks.append(text[start:actual_end].strip())
        start = actual_end - chunk_overlap
        if start <= 0:
            start = actual_end

    return [c for c in chunks if c]


# ============================================================
# Documents
# ============================================================
def insert_document(content: str, source: str = "", metadata: dict = None,
                    department_id: int = None) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(
            "INSERT INTO documents (content, source, metadata, department_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (content, source, Jsonb(metadata or {}), department_id)
        )
        doc_id = cur.fetchone()[0]
        conn.commit()
        return doc_id


def insert_embedding(document_id: int, embedding: list[float]):
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        conn.execute(
            "INSERT INTO embeddings (document_id, embedding) VALUES (%s, %s)",
            (document_id, embedding)
        )
        conn.commit()


def list_documents(department_id: int = None) -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        if department_id is not None:
            cur = conn.execute("""
                SELECT d.id, d.content, d.source, d.metadata, d.department_id, dep.name, d.created_at
                FROM documents d
                LEFT JOIN departments dep ON dep.id = d.department_id
                WHERE d.department_id = %s
                ORDER BY d.created_at DESC LIMIT 200
            """, (department_id,))
        else:
            cur = conn.execute("""
                SELECT d.id, d.content, d.source, d.metadata, d.department_id, dep.name, d.created_at
                FROM documents d
                LEFT JOIN departments dep ON dep.id = d.department_id
                ORDER BY d.created_at DESC LIMIT 200
            """)
        return [
            {"id": r[0], "content": r[1][:200], "source": r[2], "metadata": r[3],
             "department_id": r[4], "department": r[5], "created_at": str(r[6])}
            for r in cur.fetchall()
        ]


def delete_document(doc_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()


# ============================================================
# Search
# ============================================================
def search_similar(query_embedding: list[float], top_k: int = 5,
                   min_score: float = 0.0, source_filter: str = None,
                   department_id: int = None) -> list[dict]:
    """Vector search with optional department filter."""
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)

        conditions = ["1 - (e.embedding <=> %s::halfvec) >= %s"]
        params = [query_embedding, min_score]

        if source_filter:
            conditions.append("d.source = %s")
            params.append(source_filter)

        if department_id is not None:
            conditions.append("d.department_id = %s")
            params.append(department_id)

        where_clause = " AND ".join(conditions)
        params.extend([query_embedding, top_k])

        cur = conn.execute(f"""
            SELECT d.id, d.content, d.source, d.metadata, d.department_id,
                   1 - (e.embedding <=> %s::halfvec) AS similarity
            FROM embeddings e
            JOIN documents d ON d.id = e.document_id
            WHERE {where_clause}
            ORDER BY e.embedding <=> %s::halfvec
            LIMIT %s
        """, [query_embedding] + params)

        return [
            {"id": r[0], "content": r[1], "source": r[2], "metadata": r[3],
             "department_id": r[4], "similarity": float(r[5])}
            for r in cur.fetchall()
        ]


def get_stats(department_id: int = None) -> dict:
    with psycopg.connect(DATABASE_URL) as conn:
        if department_id is not None:
            doc_count = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE department_id = %s", (department_id,)
            ).fetchone()[0]
            emb_count = conn.execute("""
                SELECT COUNT(*) FROM embeddings e
                JOIN documents d ON d.id = e.document_id
                WHERE d.department_id = %s
            """, (department_id,)).fetchone()[0]
        else:
            doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            emb_count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        return {"document_count": doc_count, "embedding_count": emb_count}


# ============================================================
# Departments
# ============================================================
def list_departments() -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute("SELECT id, name, description FROM departments ORDER BY name")
        return [{"id": r[0], "name": r[1], "description": r[2]} for r in cur.fetchall()]


def create_department(name: str, description: str = "") -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(
            "INSERT INTO departments (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING RETURNING id",
            (name, description)
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def get_department_by_id(dept_id: int) -> dict | None:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute("SELECT id, name, description FROM departments WHERE id = %s", (dept_id,))
        row = cur.fetchone()
        return {"id": row[0], "name": row[1], "description": row[2]} if row else None


# ============================================================
# Users
# ============================================================
def create_user(email: str, password_hash: str, role: str = "user",
                department_id: int = None) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, role, department_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, password_hash, role, department_id)
        )
        uid = cur.fetchone()[0]
        conn.commit()
        return uid


def get_user_by_email(email: str) -> dict | None:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute("""
            SELECT u.id, u.email, u.password_hash, u.role, u.department_id, d.name
            FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE u.email = %s
        """, (email,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "email": row[1], "password_hash": row[2],
            "role": row[3], "department_id": row[4], "department_name": row[5],
        }


def list_all_users() -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute("""
            SELECT u.id, u.email, u.role, d.name, u.created_at
            FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            ORDER BY u.created_at DESC
        """)
        return [
            {"id": r[0], "email": r[1], "role": r[2], "department": r[3], "created_at": str(r[4])}
            for r in cur.fetchall()
        ]


def delete_user(user_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()


# ============================================================
# Conversations
# ============================================================
def save_message(session_id: str, role: str, content: str):
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
        conn.commit()


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = %s ORDER BY created_at LIMIT %s",
            (session_id, limit)
        )
        return [{"role": r[0], "content": r[1]} for r in cur.fetchall()]


def create_session(session_id: str = None) -> str:
    return session_id or str(uuid.uuid4())