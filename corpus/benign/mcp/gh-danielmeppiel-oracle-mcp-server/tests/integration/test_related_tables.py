import pytest
from db_context import DatabaseContext

pytestmark = pytest.mark.asyncio

async def test_related_tables_directions(db_context_read_only: DatabaseContext):
    # categories <- items (items has FK to categories)
    rel_categories = await db_context_read_only.get_related_tables("CATEGORIES")
    # categories should have no referenced tables (it references none) but should have referencing table ITEMS
    assert isinstance(rel_categories, dict)
    assert "referenced_tables" in rel_categories and "referencing_tables" in rel_categories
    assert "ITEMS" in [t.upper() for t in rel_categories["referencing_tables"]]

    rel_items = await db_context_read_only.get_related_tables("ITEMS")
    # items should reference categories, and categories should appear in referenced_tables
    assert "CATEGORIES" in [t.upper() for t in rel_items["referenced_tables"]]
