"""Invoice-Ninja-API für den IN-MCP. Übernommen aus DSS-PMS services/invoice_ninja.py (Commit ea2d020),
nur die Funktionen, die der MCP braucht. URL und Token kommen ausschließlich aus der Umgebung.

Gotchas (gelten für jedes IN): Schreibaufrufe brauchen Accept: application/json (sonst 302 statt 422),
der Client-PUT ersetzt die komplette Kontaktliste, MwSt. steht je Position, tax_id ist die Steuerkategorie.
"""
import os

import requests


def _get_config() -> tuple[str, str]:
    return os.environ.get("INVOICE_NINJA_URL", "").rstrip("/"), os.environ.get("INVOICE_NINJA_API_TOKEN", "")


def _schreib_header(token: str) -> dict:
    # Accept ist Pflicht: ohne ihn antwortet IN bei Validierungsfehlern mit einem
    # 302 auf HTML statt mit 422 JSON (Befund aus einer anderen IN-Integration, 01.06.2026).
    return {"X-API-Token": token, "Content-Type": "application/json", "Accept": "application/json"}


def get_invoices_for_project(project_id: str) -> list[dict]:
    """Lädt alle Rechnungen eines Projekts aus Invoice Ninja."""
    url, token = _get_config()
    if not url or not token or not project_id:
        return []
    resp = requests.get(
        f"{url}/api/v1/invoices",
        headers={"X-API-Token": token},
        params={"project_id": project_id, "per_page": 100},
        timeout=15,
    )
    resp.raise_for_status()
    invoices = []
    for inv in resp.json().get("data", []):
        if inv.get("project_id") != project_id:
            continue
        invoices.append({
            "id": inv.get("id", ""),
            "number": inv.get("number", ""),
            "date": inv.get("date", ""),
            "amount": inv.get("amount", 0),
            "status_id": inv.get("status_id", 0),
        })
    return invoices


def update_project(project_id: str, felder: dict) -> bool:
    """Schreibt einzelne Projektfelder (IN-MCP notiz_setzen); nicht übergebene bleiben unverändert."""
    url, token = _get_config()
    if not url or not token or not project_id:
        return False
    resp = requests.put(f"{url}/api/v1/projects/{project_id}", headers=_schreib_header(token),
                        json=felder, timeout=10)
    resp.raise_for_status()
    return True


def get_quotes_listing() -> list[dict]:
    """Lädt alle Quotes roh (inkl. archivierter/gelöschter) mit Kundenobjekt.
    Gefiltert wird in services/bestellung.py, damit die Regeln testbar bleiben."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(
        f"{url}/api/v1/quotes",
        headers={"X-API-Token": token},
        params={"per_page": 500, "include": "client"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_projects_listing() -> list[dict]:
    """Alle Projects roh (aktiv + archiviert) mit Kundenobjekt - für den IN-MCP."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(
        f"{url}/api/v1/projects",
        headers={"X-API-Token": token},
        params={"per_page": 500, "include": "client", "status": "active,archived"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_invoices_listing() -> list[dict]:
    """Die neuesten 500 Rechnungen roh (aktiv + archiviert) mit Kundenobjekt - für den IN-MCP."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(
        f"{url}/api/v1/invoices",
        headers={"X-API-Token": token},
        params={"per_page": 500, "include": "client", "status": "active,archived", "sort": "date|desc"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_payments_listing() -> list[dict]:
    """Die neuesten 500 Zahlungen roh (aktiv + archiviert) mit Kunde, Rechnungen, Paymentables - für den IN-MCP."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(
        f"{url}/api/v1/payments",
        headers={"X-API-Token": token},
        params={"per_page": 500, "include": "client,invoices,paymentables",
                "status": "active,archived", "sort": "date|desc"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_vendors_listing() -> list[dict]:
    """Alle Lieferanten roh (aktiv + archiviert) - für den IN-MCP."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(
        f"{url}/api/v1/vendors",
        headers={"X-API-Token": token},
        params={"per_page": 500, "status": "active,archived"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_listing(pfad: str, **params) -> list[dict]:
    """Rohe IN-Liste zu einem beliebigen Endpunkt (z.B. 'clients', 'products') - für in_rohdaten
    im IN-MCP. Default per_page=500 und status='active,archived', per params überschreibbar."""
    url, token = _get_config()
    if not url or not token:
        return []
    params.setdefault("per_page", 500)
    params.setdefault("status", "active,archived")
    resp = requests.get(f"{url}/api/v1/{pfad}", headers={"X-API-Token": token}, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_custom_field_labels() -> dict:
    """Beschriftungen der Custom Fields (z.B. {'client1': 'Mandant-Nr.'}) aus der ersten Company.
    IN speichert 'Beschriftung|Typ|...'; nur der Teil vor dem ersten '|' interessiert, leere weg."""
    url, token = _get_config()
    if not url or not token:
        return {}
    resp = requests.get(f"{url}/api/v1/companies", headers={"X-API-Token": token}, timeout=15)
    resp.raise_for_status()
    companies = resp.json().get("data", [])
    if not companies:
        return {}
    cf = companies[0].get("custom_fields") or {}
    return {k: v.split("|")[0] for k, v in cf.items() if v}


def get_entity_documents(pfad: str, entity_id: str) -> list[dict]:
    """Dokumentliste eines Kunden/Angebots/einer Rechnung roh - für den IN-MCP."""
    if pfad not in ("clients", "quotes", "invoices"):
        raise ValueError(f"Unbekannter Pfad für Dokumente: {pfad}")
    url, token = _get_config()
    if not url or not token or not entity_id:
        return []
    resp = requests.get(
        f"{url}/api/v1/{pfad}/{entity_id}",
        headers={"X-API-Token": token},
        params={"include": "documents"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("documents", [])


def update_client(client_id: str, felder: dict) -> dict:
    """Ändert Kundenfelder (IN-MCP). Die Kontaktliste muss als `contacts` mit allen
    bestehenden Kontakten samt id mitkommen - siehe update_client_contacts()."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/clients/{client_id}", headers=_schreib_header(token),
                        json=felder, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def update_quote_private_notes(quote_id: str, text: str) -> bool:
    """Schreibt die private Notiz eines Angebots (IN-MCP)."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/quotes/{quote_id}", headers=_schreib_header(token),
                        json={"private_notes": text}, timeout=10)
    resp.raise_for_status()
    return True


def get_products() -> list[dict]:
    """Aktive Produkte des IN-Katalogs. Der Katalogpreis steht in `price`, `cost` ist 0."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(f"{url}/api/v1/products", headers={"X-API-Token": token},
                        params={"per_page": 500}, timeout=15)
    resp.raise_for_status()
    produkte = []
    for p in resp.json().get("data", []):
        if p.get("is_deleted") or p.get("archived_at"):
            continue
        produkte.append({
            "id": p.get("id", ""),
            "product_key": p.get("product_key", ""),
            "notes": p.get("notes", "") or "",
            "price": float(p.get("price") or p.get("cost") or 0),
            "tax_name1": p.get("tax_name1", "") or "",
            "tax_rate1": p.get("tax_rate1") or 0,
            "tax_id": p.get("tax_id", "") or "",
        })
    return produkte


def get_all_clients() -> list[dict]:
    """Alle aktiven Kunden roh, inkl. Kontakte. Gesucht wird lokal (IN-`filter` ist Freitext)."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(f"{url}/api/v1/clients", headers={"X-API-Token": token},
                        params={"per_page": 500, "status": "active"}, timeout=15)
    resp.raise_for_status()
    return [c for c in resp.json().get("data", []) if not c.get("is_deleted")]


def get_client(client_id: str) -> dict | None:
    """Ein Kunde roh mit aktuellen Kontakten (vor dem Ergänzen von Kontakten frisch lesen)."""
    url, token = _get_config()
    if not url or not token or not client_id:
        return None
    resp = requests.get(f"{url}/api/v1/clients/{client_id}", headers={"X-API-Token": token}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data")


def update_client_contacts(client_id: str, contacts: list[dict]) -> dict:
    """Schreibt die Kontaktliste eines Kunden.

    ACHTUNG: IN ersetzt die komplette Liste. Kontakte, die hier ohne ihre `id` fehlen,
    werden gelöscht - Liste immer über angebot.kontaktliste_fuer_update() bauen."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/clients/{client_id}", headers=_schreib_header(token),
                        json={"contacts": contacts}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def create_quote(payload: dict) -> dict:
    """Legt ein Angebot als Entwurf an. Gibt die IN-Daten zurück (id, number)."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/quotes", headers=_schreib_header(token), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def mark_quote_sent(quote_id: str) -> bool:
    """Setzt ein Angebot auf 'versendet' (status_id=2). Ohne das bleibt ein über Outlook
    verschicktes Angebot ein Entwurf: nie bestellbar im PMS, läuft nie ab, kein Nachfass."""
    url, token = _get_config()
    if not url or not token or not quote_id:
        return False
    resp = requests.post(f"{url}/api/v1/quotes/bulk", headers=_schreib_header(token),
                         json={"action": "mark_sent", "ids": [quote_id]}, timeout=10)
    resp.raise_for_status()
    return True


def get_tax_rates() -> list[dict]:
    """Aktive Steuersätze aus IN. Die id hier ist NICHT das `tax_id` von Produkten/Positionen -
    das ist in IN die Steuerkategorie (1 Ware, 2 Dienstleistung, 3 Digital)."""
    url, token = _get_config()
    if not url or not token:
        return []
    resp = requests.get(f"{url}/api/v1/tax_rates", headers={"X-API-Token": token}, timeout=15)
    resp.raise_for_status()
    return [{"id": r.get("id", ""), "name": r.get("name", "") or "", "rate": float(r.get("rate") or 0)}
            for r in resp.json().get("data", []) if not r.get("is_deleted") and not r.get("archived_at")]


def create_product(payload: dict) -> dict:
    """Legt ein Katalogprodukt an (IN-MCP produkt_speichern)."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/products", headers=_schreib_header(token), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def update_product(product_id: str, felder: dict) -> dict:
    """Ändert Felder eines Katalogprodukts; nicht übergebene Felder bleiben in IN unverändert."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/products/{product_id}", headers=_schreib_header(token),
                        json=felder, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def update_quote(quote_id: str, felder: dict) -> dict:
    """Ändert einzelne Kopf-Felder eines Angebots (Gültig bis, Bezeichnung, öffentliche Notiz). Nur die
    übergebenen Felder werden geschrieben, alle anderen (Positionen, Empfänger, Custom Values) bleiben
    in Invoice Ninja unangetastet."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/quotes/{quote_id}", headers=_schreib_header(token),
                        json=felder, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def update_quote_line_items(quote_id: str, line_items: list[dict]) -> dict:
    """Ersetzt die Positionen eines Angebots. Nur line_items - Kopf, Empfänger und Custom Values
    bleiben unangetastet. MwSt. steht je Position (siehe angebot.line_items)."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/quotes/{quote_id}", headers=_schreib_header(token),
                        json={"line_items": line_items}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


# --- Rechnungen (IN-MCP, pro Instanz freischaltbar) ---------------------------------
# Rechnungen entstehen in IN immer als Entwurf; die Nummer vergibt IN je nach Einstellung
# (counter_number_applied) schon beim Speichern. Gelöscht wird über den MCP nie.

def get_invoice(invoice_id: str) -> dict:
    """Eine Rechnung frisch aus IN, mit Empfängern (invitations) - vor jedem Schreiben lesen."""
    url, token = _get_config()
    resp = requests.get(f"{url}/api/v1/invoices/{invoice_id}", headers={"X-API-Token": token},
                        params={"include": "invitations"}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", {})


def create_invoice(payload: dict) -> dict:
    """Legt eine Rechnung an (in IN immer Status Entwurf). Gibt die IN-Daten zurück (id, number, amount)."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/invoices", headers=_schreib_header(token), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def update_invoice(invoice_id: str, felder: dict) -> dict:
    """Ändert einzelne Felder einer Rechnung; nicht übergebene bleiben in IN unverändert."""
    url, token = _get_config()
    resp = requests.put(f"{url}/api/v1/invoices/{invoice_id}", headers=_schreib_header(token),
                        json=felder, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def invoice_bulk(action: str, ids: list[str]) -> list | dict:
    """Bulk-Aktion auf Rechnungen (mark_sent, email, cancel, ...). Liefert die Rechnungen danach."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/invoices/bulk", headers=_schreib_header(token),
                         json={"action": action, "ids": list(ids)}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def create_payment(payload: dict) -> dict:
    """Erfasst eine Zahlung (client_id, amount, date, invoices: [{invoice_id, amount}])."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/payments", headers=_schreib_header(token), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})


def quote_bulk(action: str, ids: list[str]) -> list | dict:
    """Bulk-Aktion auf Angebote (z. B. convert_to_invoice)."""
    url, token = _get_config()
    resp = requests.post(f"{url}/api/v1/quotes/bulk", headers=_schreib_header(token),
                         json={"action": action, "ids": list(ids)}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])
