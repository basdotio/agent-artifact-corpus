"""Optionale Anbindung an die DSS-PMS-Datenbank - nur wenn PMS_DB_PATH gesetzt ist.

Beim Kunden gibt es kein PMS: dann wird das Vorlagen-Tool nicht registriert und
angebot_loggen() tut nichts. Tabellen und Spalten wie in DSS-PMS database/db.py.
"""
import json
import os
import sqlite3
from datetime import datetime


def db_pfad() -> str:
    return os.environ.get("PMS_DB_PATH", "")


def aktiv() -> bool:
    return bool(db_pfad())


def _verbindung() -> sqlite3.Connection:
    conn = sqlite3.connect(db_pfad(), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def angebot_vorlagen() -> list[dict]:
    """Aktive Vorlagen wie PMS list_angebot_vorlagen(): name, produkte (Liste), verkaufsbedingungen."""
    conn = _verbindung()
    try:
        rows = conn.execute("SELECT name, produkte, verkaufsbedingungen FROM angebot_vorlagen "
                            "WHERE aktiv = 1 ORDER BY sortierung, name").fetchall()
        return [{"name": r["name"], "produkte": json.loads(r["produkte"] or "[]"),
                 "verkaufsbedingungen": r["verkaufsbedingungen"]} for r in rows]
    finally:
        conn.close()


def angebot_loggen(angebotsnummer: str, quote_id: str, client_id: str) -> None:
    """Eintrag für den PMS-Prüfbericht ("nie versendet"). Ohne PMS ein No-op."""
    if not aktiv():
        return
    conn = _verbindung()
    try:
        conn.execute("INSERT INTO angebot_log (angebotsnummer, quote_id, client_id, erstellt_am) "
                     "VALUES (?, ?, ?, ?)", (angebotsnummer, quote_id, client_id, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()
