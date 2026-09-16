import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_task_list_minimal_fields():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        res = await ac.get('/tasks?type=task&status=in_progress&limit=5&fields=hid,title,status,updated_at')
    assert res.status_code in (200, 204)
