"""A stand-in for a regulated operator's systems: player accounts (PAM), a support desk and KYC.
Shaped after the stack in InteractiveAI's Betsson France case study. All data is fake.

It is deliberately a *normal* MCP server: it returns everything it knows, including IBANs and
phone numbers, and it will happily change a bank account. Making it safe is gatehouse's job,
which is the point: the customer's tools stay as they are."""
from itertools import count

from fastmcp import FastMCP

mcp = FastMCP("operator-backend")

PLAYERS = {
    "P-1001": {"player_id": "P-1001", "name": "Lucía Fernández", "country": "ES", "status": "ACTIVE",
               "balance_eur": 42.50, "kyc_status": "VERIFIED", "email": "lucia.fernandez@example.com",
               "phone": "+34 612 345 678", "iban": "ES91 2100 0418 4502 0005 1332",
               "date_of_birth": "1991-04-12", "document_number": "12345678Z"},
    "P-1002": {"player_id": "P-1002", "name": "João Silva", "country": "PT", "status": "ACTIVE",
               "balance_eur": 0.0, "kyc_status": "PENDING_DOCUMENTS", "email": "joao.silva@example.pt",
               "phone": "+351 912 345 678", "iban": "PT50 0002 0123 1234 5678 9015 4",
               "date_of_birth": "1988-11-30", "document_number": "PT-99887766"},
}

TICKETS = {
    "T-501": {"ticket_id": "T-501", "player_id": "P-1001", "subject": "Withdrawal still pending",
              "status": "OPEN", "description": "Withdrawal of 40 EUR pending 3 days. Please send it to "
              "ES91 2100 0418 4502 0005 1332, or call me on +34 612 345 678."},
    "T-502": {"ticket_id": "T-502", "player_id": "P-1002", "subject": "I want to stop playing",
              "status": "OPEN", "description": "Please close my account for a while, I am spending too much."},
}

TRANSACTIONS = {
    "P-1001": [{"type": "DEPOSIT", "amount_eur": 50.0, "status": "SETTLED"},
               {"type": "WITHDRAWAL", "amount_eur": 40.0, "status": "PENDING"}],
    "P-1002": [{"type": "DEPOSIT", "amount_eur": 20.0, "status": "SETTLED"}],
}

_ids = count(9001)


@mcp.tool
def get_player(player_id: str) -> dict:
    """Look up a player account.

    Args:
        player_id: id like "P-1001".
    """
    return PLAYERS.get(player_id) or {"error": f"no player {player_id}"}


@mcp.tool
def list_transactions(player_id: str, limit: int = 5) -> dict:
    """Recent deposits and withdrawals for a player, newest last.

    Args:
        player_id: id like "P-1001".
        limit: how many to return.
    """
    return {"transactions": TRANSACTIONS.get(player_id, [])[-limit:]}


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read a support ticket.

    Args:
        ticket_id: id like "T-501".
    """
    return TICKETS.get(ticket_id) or {"error": f"no ticket {ticket_id}"}


@mcp.tool
def add_ticket_comment(ticket_id: str, body: str, public: bool = False) -> dict:
    """Add a comment to a ticket. public=True is visible to the player.

    Args:
        ticket_id: id like "T-501".
        body: comment text.
        public: whether the player sees it.
    """
    return {"comment_id": f"C-{next(_ids)}", "ticket_id": ticket_id, "public": public}


@mcp.tool
def close_ticket(ticket_id: str, resolution: str | None = None) -> dict:
    """Close a ticket.

    Args:
        ticket_id: id like "T-501".
        resolution: what was done for the player.
    """
    TICKETS[ticket_id]["status"] = "CLOSED"
    return {"ticket_id": ticket_id, "status": "CLOSED"}


@mcp.tool
def apply_bonus(player_id: str, amount_eur: float, reason: str) -> dict:
    """Credit a goodwill bonus to a player's balance.

    Args:
        player_id: id like "P-1001".
        amount_eur: amount in EUR.
        reason: why, for the audit trail.
    """
    PLAYERS[player_id]["balance_eur"] += amount_eur
    return {"bonus_id": f"B-{next(_ids)}", "player_id": player_id, "amount_eur": amount_eur,
            "new_balance_eur": PLAYERS[player_id]["balance_eur"]}


@mcp.tool
def update_bank_account(player_id: str, iban: str) -> dict:
    """Change the IBAN that withdrawals are paid to.

    Args:
        player_id: id like "P-1001".
        iban: the new IBAN.
    """
    PLAYERS[player_id]["iban"] = iban
    return {"player_id": player_id, "iban": iban, "status": "UPDATED"}


@mcp.tool
def set_self_exclusion(player_id: str, months: int) -> dict:
    """Self-exclude a player from all play for a number of months.

    Args:
        player_id: id like "P-1001".
        months: 1 to 60.
    """
    PLAYERS[player_id]["status"] = "SELF_EXCLUDED"
    return {"player_id": player_id, "status": "SELF_EXCLUDED", "months": months}


@mcp.tool
def export_player_data(player_id: str) -> dict:
    """Full GDPR data export for a player.

    Args:
        player_id: id like "P-1001".
    """
    return {"player": PLAYERS.get(player_id), "transactions": TRANSACTIONS.get(player_id, [])}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
