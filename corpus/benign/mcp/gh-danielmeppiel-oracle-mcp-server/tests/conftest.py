import os
import pytest
import pytest_asyncio
from pathlib import Path

from db_context import DatabaseContext

ORACLE_CONN_ENV = "ORACLE_CONNECTION_STRING"
DEFAULT_CONN = os.getenv(ORACLE_CONN_ENV)

# We purposely do not spin Docker here; assume test DB is already running via docker-compose.
# Tests that require the database will be skipped automatically if connection string is absent.


@pytest.fixture(scope="session")
def oracle_connection_string():
    if not DEFAULT_CONN:
        pytest.skip(f"Environment variable {ORACLE_CONN_ENV} not set; integration tests skipped.")
    return DEFAULT_CONN

@pytest_asyncio.fixture(scope="function")
async def db_context_read_only(oracle_connection_string, tmp_path_factory):
    """Function-scoped to ensure all asyncio primitives (locks, pool) are bound
    to the same event loop as the awaiting test. Session scope previously caused
    'Future attached to a different loop' when pytest-asyncio created a new loop
    per test while reusing the same DatabaseContext instance."""
    cache_dir = tmp_path_factory.mktemp("cache")
    ctx = DatabaseContext(
        connection_string=oracle_connection_string,
        cache_path=Path(cache_dir / "schema_cache.json"),
        read_only=True,
        target_schema=os.getenv("TARGET_SCHEMA") or None,
    )
    await ctx.initialize()
    try:
        yield ctx
    finally:
        await ctx.close()

@pytest_asyncio.fixture(scope="function")
async def db_context_write_enabled(oracle_connection_string, tmp_path_factory):
    """Function-scoped variant for write-enabled context for same loop-safety reasons."""
    cache_dir = tmp_path_factory.mktemp("cache_write")
    ctx = DatabaseContext(
        connection_string=oracle_connection_string,
        cache_path=Path(cache_dir / "schema_cache.json"),
        read_only=False,
        target_schema=os.getenv("TARGET_SCHEMA") or None,
    )
    await ctx.initialize()
    try:
        yield ctx
    finally:
        await ctx.close()
