"""End-to-end mock-only scenario for cost/revenue centers integration.

Covers the full v1.9.0 cost-center surface area via call_tool dispatch:
- list_cost_centers
- create_invoice / create_credit_note / create_proforma with revenue_center
- convert_proforma_to_invoice with revenue_center
- update_document with revenue_center
- duplicate_invoice with revenue_center
- get_invoice and list_invoices expose revenue_center
- create_received_document with cost_center
- get_received_document and list_received_documents expose cost_center
- validation: unknown revenue_center / cost_center is rejected

No real FIC API calls. All SDK methods are mocked. Safe to run in CI.
"""

import asyncio
import importlib
import json
import sys

import pytest
from unittest.mock import MagicMock, patch


KNOWN_CENTERS = ["Project Alpha", "Project Beta"]


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

    list_cc_response = MagicMock()
    list_cc_response.data = list(KNOWN_CENTERS)
    list_rc_response = MagicMock()
    list_rc_response.data = list(KNOWN_CENTERS)

    client_response = MagicMock()
    client_response.data.to_dict.return_value = {
        "id": 5,
        "name": "Acme",
        "vat_number": "01234567890",
        "tax_code": "",
        "address_street": "Via Roma 1",
        "address_city": "Genova",
        "address_postal_code": "16100",
        "address_province": "GE",
        "country": "Italia",
        "ei_code": "ABCDEF1",
        "certified_email": "",
    }

    with patch.object(server.info_api, "list_cost_centers", return_value=list_cc_response), \
         patch.object(server.info_api, "list_revenue_centers", return_value=list_rc_response), \
         patch.object(server.clients_api, "get_client", return_value=client_response):
        yield server


def _run(coro):
    return asyncio.run(coro)


def _mock_issued_doc(doc_id=42, number=1, doc_type="invoice", rc_center=None):
    payload = {
        "id": doc_id,
        "number": number,
        "type": doc_type,
        "date": "2026-05-10",
        "entity": {"id": 5, "name": "Acme"},
        "visible_subject": "Test",
        "items_list": [{
            "name": "Item",
            "qty": 1,
            "net_price": 100.0,
            "gross_price": 122.0,
            "vat": {"id": 0, "value": 22},
        }],
        "payments_list": [{
            "amount": 122.0,
            "due_date": "2026-06-10",
            "status": "not_paid",
        }],
        "ei_status": None,
    }
    if rc_center:
        payload["rc_center"] = rc_center
    response = MagicMock()
    response.data.to_dict.return_value = payload
    return response


def _mock_received_doc(doc_id=99, rc_center=None):
    payload = {
        "id": doc_id,
        "type": "expense",
        "date": "2026-05-10",
        "entity": {"name": "Supplier Srl", "vat_number": "98765432109"},
        "description": "Office rent",
        "category": "rent",
        "amount_net": 500.0,
        "amount_vat": 110.0,
        "amount_gross": 610.0,
        "items_list": [],
        "payments_list": [],
    }
    if rc_center:
        payload["rc_center"] = rc_center
    response = MagicMock()
    response.data.to_dict.return_value = payload
    return response


def test_list_cost_centers_returns_union(server_module):
    """list_cost_centers MCP tool returns union of cost + revenue centers,
    deduplicated and sorted."""
    server = server_module
    result = _run(server.call_tool("list_cost_centers", {}))
    payload = json.loads(result[0].text)
    assert payload == sorted(KNOWN_CENTERS)


def test_list_cost_centers_dedups_overlap(server_module, monkeypatch):
    """If a name appears in both cost and revenue lists, the tool dedups it."""
    server = server_module
    cost = MagicMock()
    cost.data = ["Shared", "OnlyCost"]
    rev = MagicMock()
    rev.data = ["Shared", "OnlyRevenue"]
    # invalidate caches from the previous fixture call
    import cache as cache_mod
    cache_mod.invalidate_all(100)

    with patch.object(server.info_api, "list_cost_centers", return_value=cost), \
         patch.object(server.info_api, "list_revenue_centers", return_value=rev):
        result = _run(server.call_tool("list_cost_centers", {}))
    payload = json.loads(result[0].text)
    assert payload == ["OnlyCost", "OnlyRevenue", "Shared"]


def test_create_invoice_with_revenue_center(server_module):
    server = server_module
    created = _mock_issued_doc(rc_center="Project Alpha")

    with patch.object(server.issued_api, "create_issued_document", return_value=created) as m:
        result = _run(server.call_tool("create_invoice", {
            "client_id": 5,
            "items": [{"name": "Item", "qty": 1, "net_price": 100.0, "vat_rate": 22}],
            "revenue_center": "Project Alpha",
        }))

    payload = json.loads(result[0].text)
    assert payload["success"] is True
    assert payload["revenue_center"] == "Project Alpha"

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Alpha"


def test_create_invoice_rejects_unknown_revenue_center(server_module):
    server = server_module

    with patch.object(server.issued_api, "create_issued_document") as m:
        result = _run(server.call_tool("create_invoice", {
            "client_id": 5,
            "items": [{"name": "Item", "qty": 1, "net_price": 100.0, "vat_rate": 22}],
            "revenue_center": "Unknown Center",
        }))

    payload = json.loads(result[0].text)
    assert payload["success"] is False
    assert "Unknown Center" in payload["error"]
    assert m.call_count == 0


def test_create_credit_note_with_revenue_center(server_module):
    server = server_module
    created = _mock_issued_doc(doc_type="credit_note", rc_center="Project Beta")

    with patch.object(server.issued_api, "create_issued_document", return_value=created) as m:
        _run(server.call_tool("create_credit_note", {
            "client_id": 5,
            "items": [{"name": "Refund", "qty": 1, "net_price": 50.0, "vat_rate": 22}],
            "revenue_center": "Project Beta",
        }))

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Beta"
    assert body["type"] == "credit_note"


def test_create_proforma_with_revenue_center(server_module):
    server = server_module
    created = _mock_issued_doc(doc_type="proforma", rc_center="Project Alpha")

    with patch.object(server.issued_api, "create_issued_document", return_value=created) as m:
        _run(server.call_tool("create_proforma", {
            "client_id": 5,
            "items": [{"name": "Item", "qty": 1, "net_price": 100.0, "vat_rate": 22}],
            "revenue_center": "Project Alpha",
        }))

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Alpha"


def test_get_invoice_exposes_revenue_center(server_module):
    server = server_module
    response = _mock_issued_doc(rc_center="Project Alpha")

    with patch.object(server.issued_api, "get_issued_document", return_value=response):
        result = _run(server.call_tool("get_invoice", {"document_id": 42}))

    payload = json.loads(result[0].text)
    assert payload["revenue_center"] == "Project Alpha"


def test_list_invoices_includes_revenue_center(server_module):
    server = server_module
    doc1 = MagicMock()
    doc1.to_dict.return_value = {
        "id": 1, "number": 1, "date": "2026-01-01", "entity": {"name": "C1"},
        "subject": "", "visible_subject": "", "rc_center": "Project Alpha",
        "items_list": [], "payments_list": [],
    }
    doc2 = MagicMock()
    doc2.to_dict.return_value = {
        "id": 2, "number": 2, "date": "2026-01-15", "entity": {"name": "C2"},
        "subject": "", "visible_subject": "",
        "items_list": [], "payments_list": [],
    }
    list_response = MagicMock()
    list_response.data = [doc1, doc2]

    with patch.object(server.issued_api, "list_issued_documents", return_value=list_response):
        result = _run(server.call_tool("list_invoices", {"year": 2026}))

    invoices = json.loads(result[0].text)
    assert invoices[0]["revenue_center"] == "Project Alpha"
    assert "revenue_center" not in invoices[1]


def test_update_document_validates_revenue_center(server_module):
    server = server_module
    orig = _mock_issued_doc(rc_center="Project Alpha")

    with patch.object(server.issued_api, "get_issued_document", return_value=orig), \
         patch.object(server.issued_api, "modify_issued_document") as m:
        result = _run(server.call_tool("update_document", {
            "document_id": 42,
            "revenue_center": "Bogus",
        }))

    payload = json.loads(result[0].text)
    assert payload["success"] is False
    assert m.call_count == 0


def test_update_document_keeps_existing_revenue_center(server_module):
    server = server_module
    orig = _mock_issued_doc(rc_center="Project Alpha")
    modified = _mock_issued_doc(rc_center="Project Alpha")

    with patch.object(server.issued_api, "get_issued_document", return_value=orig), \
         patch.object(server.issued_api, "modify_issued_document", return_value=modified) as m:
        _run(server.call_tool("update_document", {
            "document_id": 42,
            "visible_subject": "Updated",
        }))

    body = m.call_args.kwargs["modify_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Alpha"


def test_duplicate_invoice_inherits_revenue_center(server_module):
    server = server_module
    source = _mock_issued_doc(rc_center="Project Alpha")
    created = _mock_issued_doc(doc_id=43, number=2, rc_center="Project Alpha")

    with patch.object(server.issued_api, "get_issued_document", return_value=source), \
         patch.object(server.issued_api, "create_issued_document", return_value=created) as m:
        _run(server.call_tool("duplicate_invoice", {
            "source_document_id": 42,
            "new_date": "2026-06-01",
        }))

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Alpha"


def test_duplicate_invoice_overrides_revenue_center(server_module):
    server = server_module
    source = _mock_issued_doc(rc_center="Project Alpha")
    created = _mock_issued_doc(doc_id=43, number=2, rc_center="Project Beta")

    with patch.object(server.issued_api, "get_issued_document", return_value=source), \
         patch.object(server.issued_api, "create_issued_document", return_value=created) as m:
        _run(server.call_tool("duplicate_invoice", {
            "source_document_id": 42,
            "new_date": "2026-06-01",
            "revenue_center": "Project Beta",
        }))

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Beta"


def test_convert_proforma_with_revenue_center(server_module):
    server = server_module
    proforma = _mock_issued_doc(doc_id=10, number=1, doc_type="proforma")
    invoice = _mock_issued_doc(doc_id=11, number=2, doc_type="invoice", rc_center="Project Alpha")

    with patch.object(server.issued_api, "get_issued_document", return_value=proforma), \
         patch.object(server.issued_api, "create_issued_document", return_value=invoice) as m, \
         patch.object(server.issued_api, "delete_issued_document"):
        _run(server.call_tool("convert_proforma_to_invoice", {
            "document_id": 10,
            "revenue_center": "Project Alpha",
        }))

    body = m.call_args.kwargs["create_issued_document_request"]["data"]
    assert body["rc_center"] == "Project Alpha"


def test_create_received_document_with_cost_center(server_module):
    server = server_module
    created = _mock_received_doc(rc_center="Project Beta")

    with patch.object(server.received_api, "create_received_document", return_value=created) as m:
        result = _run(server.call_tool("create_received_document", {
            "supplier_name": "Supplier Srl",
            "supplier_vat_number": "98765432109",
            "amount_net": 500.0,
            "amount_vat": 110.0,
            "category": "rent",
            "description": "Office rent",
            "cost_center": "Project Beta",
        }))

    payload = json.loads(result[0].text)
    assert payload["success"] is True
    assert payload["cost_center"] == "Project Beta"

    body = m.call_args.kwargs["create_received_document_request"]["data"]
    assert body["rc_center"] == "Project Beta"


def test_create_received_document_rejects_unknown_cost_center(server_module):
    server = server_module

    with patch.object(server.received_api, "create_received_document") as m:
        result = _run(server.call_tool("create_received_document", {
            "supplier_name": "Supplier Srl",
            "amount_net": 100.0,
            "cost_center": "Bogus",
        }))

    payload = json.loads(result[0].text)
    assert payload["success"] is False
    assert "Bogus" in payload["error"]
    assert m.call_count == 0


def test_get_received_document_exposes_cost_center(server_module):
    server = server_module
    response = _mock_received_doc(rc_center="Project Alpha")

    with patch.object(server.received_api, "get_received_document", return_value=response):
        result = _run(server.call_tool("get_received_document", {"document_id": 99}))

    payload = json.loads(result[0].text)
    assert payload["cost_center"] == "Project Alpha"
    assert payload["supplier"] == "Supplier Srl"


def test_list_received_documents_includes_cost_center(server_module):
    server = server_module
    doc1 = MagicMock()
    doc1.to_dict.return_value = {
        "id": 1, "number": "F-1", "date": "2026-01-01",
        "entity": {"name": "Supplier A"}, "description": "",
        "amount_gross": 100, "rc_center": "Project Alpha",
    }
    doc2 = MagicMock()
    doc2.to_dict.return_value = {
        "id": 2, "number": "F-2", "date": "2026-01-15",
        "entity": {"name": "Supplier B"}, "description": "",
        "amount_gross": 200,
    }
    list_response = MagicMock()
    list_response.data = [doc1, doc2]

    with patch.object(server.received_api, "list_received_documents", return_value=list_response):
        result = _run(server.call_tool("list_received_documents", {"year": 2026}))

    docs = json.loads(result[0].text)
    assert docs[0]["cost_center"] == "Project Alpha"
    assert "cost_center" not in docs[1]
