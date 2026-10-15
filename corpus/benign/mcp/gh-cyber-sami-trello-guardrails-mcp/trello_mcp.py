#!/usr/bin/env python3
"""
Trello MCP server built with FastMCP.

Lets an MCP client (Claude Desktop, Claude Code, ...) read and organise Trello
boards by name. Nothing in Trello is ever hard-deleted: cards and lists can only
be archived, which Trello lets you undo.

Credentials are read from, in order:
  1. TRELLO_API_KEY and TRELLO_TOKEN environment variables
  2. the JSON file named by TRELLO_CONFIG
  3. ~/.config/trello-mcp/config.json
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

API_BASE = "https://api.trello.com/1"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "trello-mcp" / "config.json"
TIMEOUT_SECONDS = 30


# --- Config ---

def load_credentials() -> tuple[str, str]:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if key and token:
        return key, token

    path = Path(os.environ.get("TRELLO_CONFIG", DEFAULT_CONFIG_PATH)).expanduser()
    if not path.exists():
        raise RuntimeError(
            "Trello credentials not found. Set TRELLO_API_KEY and TRELLO_TOKEN, "
            f"or create {path} (see config.example.json)."
        )
    cfg = json.loads(path.read_text())
    try:
        return cfg["api_key"], cfg["token"]
    except KeyError as e:
        raise RuntimeError(f"{path} is missing the {e} field.") from None


# --- HTTP ---

def trello_request(method: str, path: str, params: dict | None = None) -> Any:
    """Call the Trello REST API. Credentials go in the Authorization header, never the URL."""
    key, token = load_credentials()
    url = f"{API_BASE}{path}"
    body = None
    if params and method in ("POST", "PUT"):
        body = urllib.parse.urlencode(params).encode()
    elif params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f'OAuth oauth_consumer_key="{key}", oauth_token="{token}"')
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        hints = {
            401: "Check that the API key and token are valid and not revoked.",
            404: "The item may have been archived or you may not have access to it.",
            429: "Trello rate limit hit. Wait a few seconds and try again.",
        }
        raise RuntimeError(f"Trello API error {e.code} on {method} {path}: {detail} {hints.get(e.code, '')}".strip()) from None


def trello_get(path: str, params: dict | None = None) -> Any:
    return trello_request("GET", path, params)


def trello_post(path: str, params: dict | None = None) -> Any:
    return trello_request("POST", path, params)


def trello_put(path: str, params: dict | None = None) -> Any:
    return trello_request("PUT", path, params)


# --- Name resolution ---

def resolve(items: list[dict], query: str, kind: str) -> dict:
    """
    Pick one item by name: exact match first (case-insensitive), then a unique
    partial match. Never guesses between several candidates; the error lists
    them so the agent can retry with a more specific name.
    """
    q = query.strip().casefold()
    exact = [i for i in items if i["name"].casefold() == q]
    if len(exact) == 1:
        return exact[0]
    candidates = exact or [i for i in items if q in i["name"].casefold()]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        names = [c["name"] for c in candidates]
        raise ValueError(f"{len(names)} {kind}s match '{query}': {names}. Use a more specific name.")
    names = [i["name"] for i in items if i["name"]]
    raise ValueError(f"No {kind} matches '{query}'. Available: {names}")


def describe(item: dict, query: str) -> str:
    """Name the item that was actually used, and the query if it differed."""
    if item["name"].casefold() == query.strip().casefold():
        return f"'{item['name']}'"
    return f"'{item['name']}' (matched from '{query}')"


def find_board(name: str) -> dict:
    return resolve(trello_get("/members/me/boards", {"fields": "id,name", "filter": "open"}), name, "board")


def find_list(board_id: str, name: str) -> dict:
    return resolve(trello_get(f"/boards/{board_id}/lists", {"fields": "id,name"}), name, "list")


def find_card(board_id: str, name: str) -> dict:
    return resolve(trello_get(f"/boards/{board_id}/cards", {"fields": "id,name"}), name, "card")


def find_label(board_id: str, name: str) -> dict:
    return resolve(trello_get(f"/boards/{board_id}/labels", {"fields": "id,name"}), name, "label")


# --- MCP Server ---

mcp = FastMCP("Trello")


@mcp.tool()
def get_boards() -> str:
    """List all open Trello boards the user has access to."""
    boards = trello_get("/members/me/boards", {"fields": "id,name", "filter": "open"})
    lines = [f"- {b['name']}" for b in boards]
    return "Your Trello boards:\n" + "\n".join(lines)


@mcp.tool()
def get_lists(board_name: str) -> str:
    """Get all open lists on a Trello board."""
    board = find_board(board_name)
    lists = trello_get(f"/boards/{board['id']}/lists", {"fields": "id,name"})
    lines = [f"- {l['name']}" for l in lists]
    return f"Lists on {describe(board, board_name)}:\n" + "\n".join(lines)


@mcp.tool()
def get_cards(board_name: str, list_name: str) -> str:
    """Get all cards in a specific list on a board."""
    board = find_board(board_name)
    lst = find_list(board["id"], list_name)
    cards = trello_get(f"/lists/{lst['id']}/cards", {"fields": "id,name,desc,due,url"})
    where = f"{describe(lst, list_name)} on {describe(board, board_name)}"
    if not cards:
        return f"No cards in {where}."
    lines = []
    for c in cards:
        line = f"- {c['name']}"
        if c.get("due"):
            line += f" [due: {c['due'][:10]}]"
        if c.get("desc"):
            line += f"\n  {c['desc'][:100]}"
        lines.append(line)
    return f"Cards in {where}:\n" + "\n".join(lines)


@mcp.tool()
def get_card_details(board_name: str, card_name: str) -> str:
    """Get full details of a specific card including description, due date, and comments."""
    board = find_board(board_name)
    match = find_card(board["id"], card_name)
    card = trello_get(f"/cards/{match['id']}", {"fields": "name,desc,due,url"})
    actions = trello_get(f"/cards/{match['id']}/actions", {"filter": "commentCard"})
    result = f"**{card['name']}**\nURL: {card['url']}\n"
    if card.get("due"):
        result += f"Due: {card['due'][:10]}\n"
    if card.get("desc"):
        result += f"Description: {card['desc']}\n"
    if actions:
        result += "\nComments:\n"
        for a in actions:
            result += f"  - {a['memberCreator']['fullName']}: {a['data']['text']}\n"
    return result


@mcp.tool()
def create_card(board_name: str, list_name: str, card_name: str, description: str = "") -> str:
    """Create a new card in a list on a board."""
    board = find_board(board_name)
    lst = find_list(board["id"], list_name)
    data = {"idList": lst["id"], "name": card_name}
    if description:
        data["desc"] = description
    card = trello_post("/cards", data)
    return (f"Created card '{card['name']}' in {describe(lst, list_name)} "
            f"on {describe(board, board_name)}.\nURL: {card['url']}")


@mcp.tool()
def create_list(board_name: str, list_name: str) -> str:
    """Create a new list on a Trello board."""
    board = find_board(board_name)
    lst = trello_post("/lists", {"name": list_name, "idBoard": board["id"]})
    return f"Created list '{lst['name']}' on {describe(board, board_name)}."


@mcp.tool()
def archive_list(board_name: str, list_name: str) -> str:
    """Archive (close) a list on a Trello board. Archived lists can be restored in Trello."""
    board = find_board(board_name)
    lst = find_list(board["id"], list_name)
    trello_put(f"/lists/{lst['id']}", {"closed": "true"})
    return f"Archived list {describe(lst, list_name)} on {describe(board, board_name)}."


@mcp.tool()
def move_card(board_name: str, card_name: str, target_list_name: str) -> str:
    """Move a card to a different list on the same board."""
    board = find_board(board_name)
    card = find_card(board["id"], card_name)
    lst = find_list(board["id"], target_list_name)
    trello_put(f"/cards/{card['id']}", {"idList": lst["id"]})
    return f"Moved {describe(card, card_name)} to {describe(lst, target_list_name)} on {describe(board, board_name)}."


@mcp.tool()
def update_card(board_name: str, card_name: str, new_name: str = "", new_description: str = "", due_date: str = "") -> str:
    """Update a card's name, description, or due date (ISO 8601, e.g. 2026-05-15). Leave fields empty to keep them unchanged."""
    data = {}
    if new_name:
        data["name"] = new_name
    if new_description:
        data["desc"] = new_description
    if due_date:
        data["due"] = due_date
    if not data:
        return "Nothing to update. Provide at least one field to change."
    board = find_board(board_name)
    card = find_card(board["id"], card_name)
    trello_put(f"/cards/{card['id']}", data)
    return f"Updated card {describe(card, card_name)} on {describe(board, board_name)}."


@mcp.tool()
def add_comment(board_name: str, card_name: str, comment: str) -> str:
    """Add a comment to a card."""
    board = find_board(board_name)
    card = find_card(board["id"], card_name)
    trello_post(f"/cards/{card['id']}/actions/comments", {"text": comment})
    return f"Added comment to {describe(card, card_name)} on {describe(board, board_name)}."


@mcp.tool()
def create_label(board_name: str, label_name: str, color: str = "") -> str:
    """Create a new label on a Trello board. Color must be one of: yellow, purple, blue, red, green, orange, black, sky, pink, lime, or empty for no color."""
    board = find_board(board_name)
    data = {"name": label_name}
    if color:
        data["color"] = color
    label = trello_post(f"/boards/{board['id']}/labels", data)
    return f"Created label '{label['name']}' ({label.get('color') or 'no color'}) on {describe(board, board_name)}."


@mcp.tool()
def add_label(board_name: str, card_name: str, label_name: str) -> str:
    """Add an existing label to a card by label name."""
    board = find_board(board_name)
    card = find_card(board["id"], card_name)
    label = find_label(board["id"], label_name)
    trello_post(f"/cards/{card['id']}/idLabels", {"value": label["id"]})
    return f"Added label {describe(label, label_name)} to {describe(card, card_name)} on {describe(board, board_name)}."


@mcp.tool()
def archive_card(board_name: str, card_name: str) -> str:
    """Archive (close) a card on a board. Archived cards can be restored in Trello."""
    board = find_board(board_name)
    card = find_card(board["id"], card_name)
    trello_put(f"/cards/{card['id']}", {"closed": "true"})
    return f"Archived {describe(card, card_name)} on {describe(board, board_name)}."


@mcp.tool()
def search_cards(query: str) -> str:
    """Search for cards across all boards by keyword (max 20 results)."""
    results = trello_get("/search", {"query": query, "modelTypes": "cards", "cards_limit": "20", "card_fields": "name,url"})
    cards = results.get("cards", [])
    if not cards:
        return f"No cards found matching '{query}'."
    lines = [f"- {c['name']}\n  {c['url']}" for c in cards]
    return f"Cards matching '{query}':\n" + "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
