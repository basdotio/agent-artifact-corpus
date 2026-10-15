"""Smoke tests. No network: the Trello API is replaced with a fake."""

import asyncio
import io
import json
import urllib.error

import pytest

import trello_mcp

BOARDS = [{"id": "b1", "name": "Game Jam"}, {"id": "b2", "name": "Home"}]
LISTS = [{"id": "l1", "name": "To Do"}, {"id": "l2", "name": "Done"}, {"id": "l3", "name": "Not Done"}]
CARDS = [
    {"id": "c1", "name": "Fix dialogue bug"},
    {"id": "c2", "name": "Write intro scene"},
    {"id": "c3", "name": "Write outro scene"},
]


@pytest.fixture(autouse=True)
def creds(monkeypatch):
    monkeypatch.setenv("TRELLO_API_KEY", "k" * 32)
    monkeypatch.setenv("TRELLO_TOKEN", "t" * 64)


@pytest.fixture
def fake_api(monkeypatch):
    calls = []

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        if path == "/members/me/boards":
            return BOARDS
        if path.endswith("/lists"):
            return LISTS
        if path.endswith("/cards"):
            return CARDS
        return {}

    monkeypatch.setattr(trello_mcp, "trello_request", fake_request)
    return calls


# --- resolve() ---

def test_exact_match_ignores_case():
    assert trello_mcp.resolve(LISTS, "done", "list")["id"] == "l2"


def test_exact_match_wins_over_partial():
    # "Done" is also a substring of "Not Done", but the exact match is used.
    assert trello_mcp.resolve(LISTS, "Done", "list")["id"] == "l2"


def test_unique_partial_match():
    assert trello_mcp.resolve(CARDS, "dialogue", "card")["id"] == "c1"


def test_ambiguous_partial_match_refuses():
    with pytest.raises(ValueError, match="2 cards match 'scene'"):
        trello_mcp.resolve(CARDS, "scene", "card")


def test_duplicate_exact_names_refuse():
    dupes = [{"id": "a", "name": "Bug"}, {"id": "b", "name": "bug"}]
    with pytest.raises(ValueError, match="2 cards match"):
        trello_mcp.resolve(dupes, "bug", "card")


def test_no_match_lists_available_names():
    with pytest.raises(ValueError, match=r"Available: \['To Do', 'Done', 'Not Done'\]"):
        trello_mcp.resolve(LISTS, "Backlog", "list")


# --- tools ---

def call_tool(name, **args):
    async def run():
        from fastmcp import Client
        async with Client(trello_mcp.mcp) as client:
            result = await client.call_tool(name, args)
            return result.content[0].text

    return asyncio.run(run())


def test_move_card_reports_what_was_matched(fake_api):
    out = call_tool("move_card", board_name="jam", card_name="dialogue", target_list_name="Done")
    assert "'Fix dialogue bug' (matched from 'dialogue')" in out
    assert "'Game Jam' (matched from 'jam')" in out
    assert ("PUT", "/cards/c1", {"idList": "l2"}) in fake_api


def test_server_exposes_expected_tools():
    async def names():
        from fastmcp import Client
        async with Client(trello_mcp.mcp) as client:
            return {t.name for t in await client.list_tools()}

    assert asyncio.run(names()) == {
        "get_boards", "get_lists", "get_cards", "get_card_details", "create_card",
        "create_list", "archive_list", "move_card", "update_card", "add_comment",
        "create_label", "add_label", "archive_card", "search_cards",
    }


def test_no_delete_calls_anywhere():
    source = open(trello_mcp.__file__).read()
    assert '"DELETE"' not in source


# --- HTTP layer ---

def test_credentials_go_in_header_not_url(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        return io.BytesIO(json.dumps([]).encode())

    monkeypatch.setattr(trello_mcp.urllib.request, "urlopen", fake_urlopen)
    trello_mcp.trello_get("/members/me/boards", {"fields": "id,name"})
    assert "k" * 32 not in seen["url"] and "t" * 64 not in seen["url"]
    assert "token" not in seen["url"]
    assert seen["auth"] == f'OAuth oauth_consumer_key="{"k" * 32}", oauth_token="{"t" * 64}"'


def test_http_error_becomes_readable_message(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"invalid token"))

    monkeypatch.setattr(trello_mcp.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="401.*invalid token.*not revoked"):
        trello_mcp.trello_get("/members/me/boards")


def test_missing_credentials_message(monkeypatch, tmp_path):
    monkeypatch.delenv("TRELLO_API_KEY")
    monkeypatch.setenv("TRELLO_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(RuntimeError, match="TRELLO_API_KEY"):
        trello_mcp.load_credentials()


def test_config_file_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("TRELLO_API_KEY")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"api_key": "file-key", "token": "file-token"}))
    monkeypatch.setenv("TRELLO_CONFIG", str(cfg))
    assert trello_mcp.load_credentials() == ("file-key", "file-token")
