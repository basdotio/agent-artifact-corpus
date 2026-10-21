"""Regression test: client lookup must not call FIC API more than once
when build_entity_from_client is invoked, even though the function
internally fans out to get_client_by_id and get_ei_code_for_client.

Pre-cache baseline: 2 API calls per build_entity_from_client(client_id).
Post-cache target: 1 API call. Test fails if > 1.
"""

import importlib
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


def _mock_client_response(client_payload):
    response = MagicMock()
    response.data.to_dict.return_value = client_payload
    return response


def test_build_entity_calls_api_once(server_module):
    server = server_module
    response = _mock_client_response({
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
    })

    with patch.object(server.clients_api, "get_client", return_value=response) as m:
        entity = server.build_entity_from_client(client_id=5)

    assert entity is not None
    assert entity["id"] == 5
    assert entity["ei_code"] == "ABCDEF1"
    assert m.call_count == 1, (
        f"build_entity_from_client should fan out to one API call after caching, "
        f"got {m.call_count}"
    )


def test_repeated_build_entity_uses_cache(server_module):
    server = server_module
    response = _mock_client_response({
        "id": 5,
        "name": "Acme",
        "ei_code": "X",
        "certified_email": "",
    })

    with patch.object(server.clients_api, "get_client", return_value=response) as m:
        for _ in range(5):
            server.build_entity_from_client(client_id=5)

    assert m.call_count == 1, (
        f"5 invocations on the same client_id should produce exactly 1 API call, "
        f"got {m.call_count}"
    )


def test_different_clients_each_fetch_once(server_module):
    server = server_module

    def fake_get_client(company_id, client_id):
        return _mock_client_response({
            "id": client_id,
            "name": f"Client-{client_id}",
            "ei_code": "Z",
            "certified_email": "",
        })

    with patch.object(server.clients_api, "get_client", side_effect=fake_get_client) as m:
        server.build_entity_from_client(client_id=5)
        server.build_entity_from_client(client_id=7)
        server.build_entity_from_client(client_id=5)
        server.build_entity_from_client(client_id=7)

    assert m.call_count == 2, (
        f"two distinct client_ids should yield 2 API calls (each cached after first), "
        f"got {m.call_count}"
    )


def test_get_ei_code_uses_cached_client(server_module):
    server = server_module
    response = _mock_client_response({
        "id": 9,
        "ei_code": "FOO123",
        "certified_email": "",
    })

    with patch.object(server.clients_api, "get_client", return_value=response) as m:
        server.get_client_by_id(client_id=9)
        ei = server.get_ei_code_for_client(client_id=9)

    assert ei == "FOO123"
    assert m.call_count == 1


def test_cache_disabled_disables_dedup(server_module, monkeypatch):
    monkeypatch.setenv("FIC_CACHE_DISABLED", "1")
    server = server_module
    response = _mock_client_response({
        "id": 5,
        "ei_code": "X",
        "certified_email": "",
    })

    with patch.object(server.clients_api, "get_client", return_value=response) as m:
        server.build_entity_from_client(client_id=5)

    assert m.call_count == 2, (
        f"with cache disabled, build_entity_from_client should produce 2 API calls "
        f"(get_client_by_id + get_ei_code_for_client → get_client_by_id), got {m.call_count}"
    )
