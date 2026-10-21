"""Unit tests for the list_cost_centers tool and the fetch_cost_centers
helper. The helper is wrapped by the @cache.cached decorator, so the
underlying SDK call must happen at most once per (company_id, ttl)
window.
"""

import asyncio
import importlib
import json
import sys

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def server_module(tmp_path, monkeypatch):
    monkeypatch.setenv("FIC_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("FIC_CACHE_DISABLED", raising=False)
    monkeypatch.setenv("FIC_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("FIC_COMPANY_ID", "100")
    monkeypatch.setenv("FIC_SENDER_EMAIL", "test@example.invalid")

    for mod in ("server", "cache"):
        if mod in sys.modules:
            del sys.modules[mod]

    server = importlib.import_module("server")
    yield server


def _mock_response(centers):
    response = MagicMock()
    response.data = list(centers) if centers is not None else None
    return response


def test_fetch_cost_centers_returns_list(server_module):
    server = server_module
    response = _mock_response(["Project Alpha", "Project Beta"])

    with patch.object(server.info_api, "list_cost_centers", return_value=response):
        result = server.fetch_cost_centers(company_id=100)

    assert result == ["Project Alpha", "Project Beta"]


def test_fetch_cost_centers_caches_repeated_calls(server_module):
    server = server_module
    response = _mock_response(["X"])

    with patch.object(server.info_api, "list_cost_centers", return_value=response) as m:
        for _ in range(5):
            server.fetch_cost_centers(company_id=100)

    assert m.call_count == 1


def test_fetch_cost_centers_per_company_isolation(server_module):
    server = server_module

    def by_company(company_id):
        if company_id == 100:
            return _mock_response(["A"])
        return _mock_response(["B"])

    with patch.object(server.info_api, "list_cost_centers", side_effect=by_company) as m:
        a = server.fetch_cost_centers(company_id=100)
        b = server.fetch_cost_centers(company_id=200)
        a_again = server.fetch_cost_centers(company_id=100)

    assert a == ["A"]
    assert b == ["B"]
    assert a_again == ["A"]
    assert m.call_count == 2


def test_fetch_cost_centers_empty_data(server_module):
    server = server_module
    response = _mock_response(None)

    with patch.object(server.info_api, "list_cost_centers", return_value=response):
        result = server.fetch_cost_centers(company_id=100)

    assert result == []


def test_fetch_cost_centers_handles_exception(server_module):
    server = server_module

    with patch.object(server.info_api, "list_cost_centers", side_effect=Exception("boom")):
        result = server.fetch_cost_centers(company_id=100)

    assert result == []


def test_list_cost_centers_tool_returns_union_of_endpoints(server_module):
    """list_cost_centers MCP tool dispatch returns the union of the two
    FIC endpoints (cost + revenue), deduplicated and sorted."""
    server = server_module
    cost_resp = _mock_response(["Alpha", "Shared"])
    rev_resp = _mock_response(["Beta", "Shared"])

    with patch.object(server.info_api, "list_cost_centers", return_value=cost_resp), \
         patch.object(server.info_api, "list_revenue_centers", return_value=rev_resp):
        result = asyncio.run(server.call_tool("list_cost_centers", {}))

    payload = json.loads(result[0].text)
    assert payload == ["Alpha", "Beta", "Shared"]


def test_fetch_revenue_centers_separate_from_cost(server_module):
    """fetch_revenue_centers calls info_api.list_revenue_centers, NOT
    info_api.list_cost_centers. Each helper has its own cache."""
    server = server_module
    cost_resp = _mock_response(["Cost-Only"])
    rev_resp = _mock_response(["Revenue-Only"])

    with patch.object(server.info_api, "list_cost_centers", return_value=cost_resp) as mc, \
         patch.object(server.info_api, "list_revenue_centers", return_value=rev_resp) as mr:
        cost = server.fetch_cost_centers(company_id=100)
        revenue = server.fetch_revenue_centers(company_id=100)

    assert cost == ["Cost-Only"]
    assert revenue == ["Revenue-Only"]
    assert mc.call_count == 1
    assert mr.call_count == 1


def test_revenue_center_validation_against_revenue_list_only(server_module):
    """A name that exists only in revenue_centers is accepted on issued
    documents; a name only in cost_centers is rejected on issued."""
    server = server_module
    # revenue-only name is valid for issued documents
    cost_resp = _mock_response(["CostOnly"])
    rev_resp = _mock_response(["RevenueOnly"])

    fake_client = MagicMock()
    fake_client.data.to_dict.return_value = {
        "id": 5, "name": "Test", "ei_code": "X", "certified_email": "",
    }
    created = MagicMock()
    created.data.to_dict.return_value = {
        "id": 1, "number": 1, "type": "invoice", "date": "2026-05-11",
    }

    with patch.object(server.info_api, "list_cost_centers", return_value=cost_resp), \
         patch.object(server.info_api, "list_revenue_centers", return_value=rev_resp), \
         patch.object(server.clients_api, "get_client", return_value=fake_client), \
         patch.object(server.issued_api, "create_issued_document", return_value=created):
        good = asyncio.run(server.call_tool("create_invoice", {
            "client_id": 5,
            "items": [{"name": "X", "qty": 1, "net_price": 100, "vat_rate": 22}],
            "revenue_center": "RevenueOnly",
        }))
        bad = asyncio.run(server.call_tool("create_invoice", {
            "client_id": 5,
            "items": [{"name": "X", "qty": 1, "net_price": 100, "vat_rate": 22}],
            "revenue_center": "CostOnly",
        }))

    good_payload = json.loads(good[0].text)
    bad_payload = json.loads(bad[0].text)
    assert good_payload["success"] is True
    assert bad_payload["success"] is False
    assert "CostOnly" in bad_payload["error"]
