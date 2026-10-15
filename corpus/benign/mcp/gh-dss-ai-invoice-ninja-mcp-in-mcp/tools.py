"""Invoice-Ninja-MCP: Logik der Tools, frei von MCP und Streamlit.

server.py registriert diese Funktionen als Tools für Claude Desktop und andere
MCP-Clients. Fachliche Fehler kommen als ToolFehler mit einer Meldung für den
Aufrufer; server.py übersetzt alles andere. Schreibende Funktionen nehmen
als erstes Argument den Aufrufer (Name aus MCP_TOKEN_<NAME>) fürs Protokoll.
"""
from __future__ import annotations

import hmac
import math
import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from in_mcp import angebot, ninja as nn, pms
from in_mcp.konfig import LABEL_PRAEFIX, Konfig
from in_mcp.protokoll import log


def log_angebot(angebotsnummer: str, quote_id: str, client_id: str) -> None:
    pms.angebot_loggen(angebotsnummer, quote_id, client_id)


def list_angebot_vorlagen() -> list[dict]:
    return pms.angebot_vorlagen()


MAX_TREFFER = 50

# Instanz-Konfiguration (Feldrollen, Angebotsregeln). server.main() und die Tests setzen sie;
# der Default ist die neutrale Konfiguration ohne Rollen.
K: Konfig = Konfig()


def einrichten(k: Konfig) -> None:
    global K
    K = k


_BERLIN = ZoneInfo("Europe/Berlin")
QUOTE_STATUS = {"1": "Entwurf", "2": "versendet", "3": "genehmigt", "4": "umgewandelt", "-1": "abgelaufen"}
INVOICE_STATUS = {"1": "Entwurf", "2": "versendet", "3": "teilbezahlt", "4": "bezahlt",
                  "5": "storniert", "6": "zurückerstattet"}
PAYMENT_STATUS = {"1": "ausstehend", "2": "storniert", "3": "fehlgeschlagen", "4": "abgeschlossen",
                  "5": "teilweise erstattet", "6": "erstattet"}
JA = ("yes", "true", "1")

# Kontakt-Rollen mit eigenem Tool-Argument (die Anrede wird gesondert behandelt)
KONTAKT_ROLLEN = ("mobil", "position", "abteilung")

# L1: Nur beim Neuanlegen geprüft (bestehende Keys werden nur case-insensitiv gesucht, nie
# validiert) - verhindert u.a. Steuerzeichen (Zeilenumbrüche), die im gemeinsamen Audit-Log
# eine gefälschte Protokollzeile vortäuschen könnten.
PRODUKT_KEY_MUSTER = re.compile(r"[\w .\-/]{1,100}")

# Einzige Kundenfelder, die der MCP ändern darf. Name, Kundennummer, Custom Values
# und Kontakte bleiben PMS bzw. kontakt_speichern vorbehalten.
KUNDE_FELDER = ("address1", "address2", "postal_code", "city", "vat_number", "phone", "website",
                "public_notes", "private_notes")

# in_rohdaten: Typ → (IN-Pfad, Schlüsselfelder für die Suche, in Prüfreihenfolge)
ROHDATEN_TYPEN = {
    "kunde": ("clients", ("number", "id")),
    "angebot": ("quotes", ("number", "id")),
    "projekt": ("projects", ("number", "id")),
    "rechnung": ("invoices", ("number", "id")),
    "produkt": ("products", ("product_key", "id")),
    "zahlung": ("payments", ("number", "id")),
    "lieferant": ("vendors", ("number", "name", "id")),
    "gutschrift": ("credits", ("number", "id")),
    "ausgabe": ("expenses", ("number", "id")),
    "aufgabe": ("tasks", ("number", "id")),
    "wiederkehrende_rechnung": ("recurring_invoices", ("number", "id")),
    "bestellung": ("purchase_orders", ("number", "id")),
}


def _rohdaten_quelle(typ: str) -> tuple[str, tuple[str, ...]]:
    """IN-Pfad und Suchfelder; Mandant-Nr. und Projektnummer nur mit Rolle (Reihenfolge wie vor dem Umzug)."""
    pfad, felder = ROHDATEN_TYPEN[typ]
    mandant, projektnr = K.feld("kunde", "mandant_nr"), K.feld("projekt", "projektnummer")
    if typ == "kunde" and mandant:
        felder = ("number", mandant, "id")
    if typ == "projekt" and projektnr:
        felder = (projektnr, "number", "id")
    return pfad, felder

# Custom-Field-Präfix je Typ (client1, invoice1, project1, vendor1, contact1, ...); sonst keine Beschriftungen
_ROHDATEN_PRAEFIX = {"kunde": ("client", "contact"), "angebot": ("invoice",), "rechnung": ("invoice",),
                     "projekt": ("project",), "lieferant": ("vendor",)}

# Werte, die in_rohdaten nie ausgibt - unabhängig vom Typ
SENSIBEL = {"password", "contact_key", "key", "link", "hash", "url", "token", "invitations", "backup"}

# Reine IN-Technik ohne Aussagewert fürs Rohdaten-Tool und das Abdeckungs-Prüfskript
TECHNIK = {"created_at", "updated_at", "user_id", "assigned_user_id", "entity_type", "company_id", "hashed_id",
          "contact_key", "password", "link", "last_login", "is_locked", "confirmed", "is_primary", "send_email",
          "client_hash", "documents", "invitations", "activities", "ledger", "system_logs", "gateway_tokens",
          "settings", "group_settings_id", "paid_to_date_compat", "sync", "e_invoice", "backup", "design_id",
          "recurring_id", "subscription_id", "reminder1_sent", "reminder2_sent", "reminder3_sent",
          "reminder_last_sent", "next_send_date", "last_sent_date", "uses_inclusive_taxes",
          "exchange_rate", "auto_bill_enabled", "partial", "partial_due_date", "line_items_compat", "tax_data",
          "location_id", "routing_id", "is_tax_exempt", "has_valid_vat_number", "classification", "id_number",
          "industry_id", "size_id", "country_id", "shipping_country_id", "currency_id", "language_id", "type_id",
          "token", "email_verified_at", "can_sign", "show_shipping_address"}
# is_amount_discount bleibt (sonst ist "discount" in in_rohdaten ohne Einordnung % vs. Betrag mehrdeutig),
# vendor_id bleibt (verknüpft Ausgaben/Bestellungen mit dem Lieferanten) - siehe Fix-Review Runde 1

# Zweite Filterebene zusätzlich zu SENSIBEL/TECHNIK: in_rohdaten ist über das Netz und für mehrere
# MCP-Clients erreichbar. Schlüssel mit diesen Fragmenten im (kleingeschriebenen) Namen fliegen ebenfalls raus,
# auch wenn IN künftig ein neues *_token/*_secret-Feld einführt, das noch in keiner der beiden Mengen
# steht. "_key"/"key" wird gesondert geprüft, weil sonst Geschäftsfelder wie product_key mitfallen.
MUSTER_SPERRE = ("password", "token", "secret", "signature", "oauth", "url", "link", "hash")
MUSTER_AUSNAHME = {"product_key"}  # harmloses Geschäftsfeld, das sonst über "_key" gesperrt würde


def _gesperrt(schluessel: str) -> bool:
    k = schluessel.lower()
    if k in MUSTER_AUSNAHME:
        return False
    if k == "key" or k.endswith("_key"):
        return True
    return any(muster in k for muster in MUSTER_SPERRE)


class ToolFehler(Exception):
    """Fachlicher Fehler; die Meldung geht unverändert an den Aufrufer."""


def aufrufer_fuer(authorization: str, tokens: dict[str, str]) -> str | None:
    """'Bearer <token>' → Name des Aufrufers oder None. Leere Tokens passen nie."""
    if not authorization.startswith("Bearer "):
        return None
    gesendet = authorization[len("Bearer "):].strip()
    if not gesendet:
        return None
    gesendet_bytes = gesendet.encode("utf-8")
    for name, token in tokens.items():
        if token and hmac.compare_digest(gesendet_bytes, token.encode("utf-8")):
            return name
    return None


def _ja(wert) -> bool:
    return str(wert or "").strip().lower() in JA


def _kappen(liste: list) -> dict:
    erg = {"treffer": liste[:MAX_TREFFER], "anzahl": len(liste)}
    if len(liste) > MAX_TREFFER:
        erg["hinweis"] = f"{len(liste)} Treffer, nur die ersten {MAX_TREFFER} gezeigt. Bitte Suche eingrenzen."
    return erg


def _enthaelt(q: str, *felder) -> bool:
    return any(q in str(f or "").lower() for f in felder)


def _im_zeitraum(datum: str, von: str, bis: str) -> bool:
    # IN liefert ISO-Daten (YYYY-MM-DD), der Textvergleich ist deshalb korrekt
    return (not von or (datum or "") >= von) and (not bis or (datum or "") <= bis)


# Beschriftungen der Custom Fields (companies.custom_fields) ändern sich selten; ein Abruf je
# 5 Minuten statt einer Anfrage je Tool-Aufruf.
LABEL_CACHE_SEKUNDEN = 300
_LABEL_CACHE = {"zeit": None, "labels": {}}


def _labels() -> dict:
    jetzt = time.monotonic()
    if _LABEL_CACHE["zeit"] is None or jetzt - _LABEL_CACHE["zeit"] > LABEL_CACHE_SEKUNDEN:
        try:
            labels = nn.get_custom_field_labels()
        except Exception:
            log.warning("IN-MCP: Beschriftungen der Custom Fields nicht lesbar, Feldnamen werden "
                       "verwendet", exc_info=True)
            return {}
        _LABEL_CACHE["labels"] = labels
        _LABEL_CACHE["zeit"] = jetzt
    return _LABEL_CACHE["labels"]


def _zusatzfelder(obj: dict, objekt: str) -> dict:
    """Custom Fields ohne Rolle, die einen Wert tragen, unter ihrer IN-Beschriftung (sonst Feldname)."""
    werte = {f: obj.get(f) for f in K.freie_felder(objekt) if str(obj.get(f) or "").strip()}
    if not werte:
        return {}
    labels = _labels()
    erg = {}
    for f, wert in werte.items():
        name = labels.get(f"{LABEL_PRAEFIX[objekt]}{f[-1]}") or f
        erg[name if name not in erg else f"{name} ({f})"] = wert
    return erg


def _mit_zusatz(erg: dict, obj: dict, objekt: str) -> dict:
    zusatz = _zusatzfelder(obj, objekt)
    if zusatz:
        erg["zusatzfelder"] = zusatz
    return erg


# --- Gemeinsam: Positionen, Rabatt (Angebot und Rechnung, siehe Task 8) ----------

def _positionen(items: list[dict]) -> list[dict]:
    return [{"produkt": i.get("product_key", ""), "text": i.get("notes", ""),
            "menge": i.get("quantity", 0), "preis": i.get("cost", 0), "mwst": i.get("tax_rate1", 0),
            "netto": round(float(i.get("line_total") or 0), 2),
            "brutto": round(float(i.get("gross_line_total") or 0), 2),
            "steuerbetrag": round(float(i.get("tax_amount") or 0), 2),
            "steuer": i.get("tax_name1", "") or ""} for i in items or []]


def _rabatt_text(discount, is_amount_discount) -> str:
    betrag = float(discount or 0)
    if betrag <= 0:
        return ""
    return f"{betrag:.2f} €" if is_amount_discount else f"{betrag:g} %"


# --- Kunden ----------------------------------------------------------------------

def _kunde_passt(c: dict, kunde: str) -> bool:
    kunde = kunde.strip()
    schluessel = [c.get("id"), (c.get("number") or "").strip()]
    mandant = K.feld("kunde", "mandant_nr")
    if mandant:
        schluessel.append((c.get(mandant) or "").strip())
    return kunde in schluessel


def _kunde(kunde: str) -> dict:
    """Kunde per Kundennummer oder IN-ID, frisch gelesen (vollständige Kontaktliste)."""
    treffer = [c for c in nn.get_all_clients() if _kunde_passt(c, kunde)]
    if not treffer:
        raise ToolFehler(f"Kunde {kunde} nicht gefunden. Kundennummer oder IN-ID angeben, "
                         "sonst zuerst kunden_suchen.")
    return nn.get_client(treffer[0]["id"])


def _kunde_kurz(c: dict) -> dict:
    erg = {"id": c.get("id", ""), "kundennummer": c.get("number", ""), "name": c.get("name", ""),
           "ort": c.get("city", "")}
    mandant = K.feld("kunde", "mandant_nr")
    if mandant:
        erg["mandant_nr"] = c.get(mandant, "")
    return _mit_zusatz(erg, c, "kunde")


def kunden_suchen(text: str) -> dict:
    q = (text or "").strip().lower()
    if not q:
        return _kappen([])
    mandant = K.feld("kunde", "mandant_nr")
    treffer = []
    for c in nn.get_all_clients():
        kontakte = c.get("contacts") or []
        if _enthaelt(q, c.get("name"), c.get("number"), c.get(mandant) if mandant else "", c.get("city"),
                     *[k.get("email") for k in kontakte],
                     *[f"{k.get('first_name', '')} {k.get('last_name', '')}" for k in kontakte]):
            treffer.append(_kunde_kurz(c))
    return _kappen(sorted(treffer, key=lambda c: c["name"].lower()))


def _lieferadresse(c: dict) -> dict | None:
    adresse = {"strasse": c.get("shipping_address1") or "", "zusatz": c.get("shipping_address2") or "",
              "plz": c.get("shipping_postal_code") or "", "ort": c.get("shipping_city") or "",
              "bundesland": c.get("shipping_state") or ""}
    return adresse if any(adresse.values()) else None


def _kontakt(k: dict) -> dict:
    erg = dict(angebot.kontakt_aus_in(k, K.feld("kontakt", "anrede")), telefon=k.get("phone", "") or "")
    for rolle in KONTAKT_ROLLEN:
        feld_ = K.feld("kontakt", rolle)
        if feld_:
            erg[rolle] = k.get(feld_, "") or ""
    return _mit_zusatz(erg, k, "kontakt")


def kunde_lesen(kunde: str) -> dict:
    c = _kunde(kunde)
    erg = {f: c.get(f, "") for f in ("address1", "address2", "postal_code", "city", "vat_number",
                                     "phone", "website", "public_notes", "private_notes")}
    erg["bundesland"] = c.get("state", "")
    erg["lieferadresse"] = _lieferadresse(c)
    erg["umsatz_bezahlt"] = round(float(c.get("paid_to_date") or 0), 2)
    erg["saldo_offen"] = round(float(c.get("balance") or 0), 2)
    # payment_balance = nicht zugeordnete Zahlungen (Anzahlungen ohne Rechnung), credit_balance =
    # Gutschrift-Guthaben - zwei verschiedene IN-Felder, vorher fälschlich beide als "guthaben" benannt
    erg["nicht_zugeordnete_zahlungen"] = round(float(c.get("payment_balance") or 0), 2)
    erg["gutschrift_guthaben"] = round(float(c.get("credit_balance") or 0), 2)
    erg.update(_kunde_kurz(c))
    erg["kontakte"] = [_kontakt(k) for k in c.get("contacts") or []]
    return erg


# --- Angebote --------------------------------------------------------------------

def _quotes() -> list[dict]:
    return [q for q in nn.get_quotes_listing() if not q.get("is_deleted")]


def _quote(angebotsnr: str) -> dict:
    nr = angebotsnr.strip().upper()
    for q in _quotes():
        if (q.get("number") or "").upper() == nr:
            return q
    raise ToolFehler(f"Angebot {nr} nicht gefunden.")


def _angebot_kurz(q: dict) -> dict:
    client = q.get("client") or {}
    amount = float(q.get("amount") or 0)
    erg = {
        "angebotsnr": q.get("number", ""), "kunde": client.get("name", ""),
        "kundennummer": client.get("number", ""),
        "datum": q.get("date", ""), "gueltig_bis": q.get("due_date", ""),
        "status": QUOTE_STATUS.get(str(q.get("status_id")), str(q.get("status_id"))),
        "archiviert": bool(q.get("archived_at")),
        "bestellnummer": q.get("po_number", ""),
        "netto": round(amount - float(q.get("total_taxes") or 0), 2), "brutto": round(amount, 2),
        "in_rechnung_umgewandelt": bool(q.get("invoice_id")),
        "rabatt": _rabatt_text(q.get("discount"), q.get("is_amount_discount")),
        "steuer_kopf": f"{q.get('tax_name1')} {float(q.get('tax_rate1') or 0):g} %"
                      if q.get("tax_name1") else "",
    }
    for rolle in ("bezeichnung", "projektnummer"):
        feld_ = K.feld("angebot", rolle)
        if feld_:
            erg[rolle] = q.get(feld_, "")
    for rolle in ("bestellt", "abgeschlossen"):
        feld_ = K.feld("angebot", rolle)
        if feld_:
            erg[rolle] = _ja(q.get(feld_))
    return _mit_zusatz(erg, q, "angebot")


def angebote_suchen(kunde: str = "", status: str = "", bestellt: bool | None = None,
                    von: str = "", bis: str = "", text: str = "") -> dict:
    kunde_q, status_q, text_q = kunde.strip().lower(), status.strip().lower(), text.strip().lower()
    treffer = []
    for q in _quotes():
        a = _angebot_kurz(q)
        if kunde_q and not (kunde_q == a["kundennummer"].lower() or kunde_q in a["kunde"].lower()):
            continue
        if status_q and a["status"].lower() != status_q:
            continue
        if bestellt is not None and a.get("bestellt") != bestellt:
            continue
        if not _im_zeitraum(a["datum"], von, bis):
            continue
        if text_q and not _enthaelt(text_q, a["angebotsnr"], a.get("bezeichnung"), a["kunde"]):
            continue
        treffer.append(a)
    return _kappen(sorted(treffer, key=lambda a: (a["datum"], a["angebotsnr"]), reverse=True))


def _rechnungsnr_fuer(invoice_id) -> str:
    if not invoice_id:
        return ""
    for i in nn.get_invoices_listing():
        if i.get("id") == invoice_id:
            return i.get("number", "")
    return ""


def angebot_lesen(angebotsnr: str) -> dict:
    q = _quote(angebotsnr)
    erg = _angebot_kurz(q)
    erg["positionen"] = _positionen(q.get("line_items") or [])
    erg["private_notiz"] = q.get("private_notes", "")
    erg["oeffentliche_notiz"] = q.get("public_notes", "")
    erg["rechnungsnr"] = _rechnungsnr_fuer(q.get("invoice_id"))
    return erg


# --- Projekte --------------------------------------------------------------------

def _projekte() -> list[dict]:
    return [p for p in nn.get_projects_listing() if not p.get("is_deleted")]


def _projekt(projekt: str) -> dict:
    such = projekt.strip()
    projektnr = K.feld("projekt", "projektnummer")
    for p in _projekte():
        if such == p.get("id") or such == (p.get("number") or "").strip() \
                or (projektnr and such.upper() == (p.get(projektnr) or "").strip().upper()):
            return p
    raise ToolFehler(f"Projekt {such} nicht gefunden. Projektnummer oder IN-ID angeben.")


def _projekt_kurz(p: dict) -> dict:
    client = p.get("client") or {}
    task_rate = float(p.get("task_rate") or 0)
    name_feld = K.feld("projekt", "name")
    erg = {"id": p.get("id", ""),
           "projektname": p.get(name_feld, "") if name_feld else p.get("name", ""),
           "kunde": client.get("name", ""), "kundennummer": client.get("number", ""),
           "archiviert": bool(p.get("archived_at")), "in_nummer": p.get("number", ""),
           "faellig": p.get("due_date", ""), "private_notiz": p.get("private_notes", "") or "",
           "oeffentliche_notiz": p.get("public_notes", "") or "",
           "stundensatz": round(task_rate, 2) if task_rate else None}
    projektnr = K.feld("projekt", "projektnummer")
    if projektnr:
        erg["projektnummer"] = p.get(projektnr, "")
    if K.angebotsnr_im_projektnamen:
        m = re.search(K.angebotsnr_im_projektnamen, p.get("name", ""))
        erg["angebotsnr"] = m.group(0) if m else ""
    abgeschlossen = K.feld("projekt", "abgeschlossen")
    if abgeschlossen:
        erg["abgeschlossen"] = _ja(p.get(abgeschlossen))
    notiz = K.feld("projekt", "notiz")
    if notiz:
        erg["notiz"] = p.get(notiz, "") or ""
    return _mit_zusatz(erg, p, "projekt")


def projekte_suchen(kunde: str = "", abgeschlossen: bool | None = None, text: str = "") -> dict:
    kunde_q, text_q = kunde.strip().lower(), text.strip().lower()
    treffer = []
    for p in _projekte():
        k = _projekt_kurz(p)
        if kunde_q and not (kunde_q == k["kundennummer"].lower() or kunde_q in k["kunde"].lower()):
            continue
        if abgeschlossen is not None and k.get("abgeschlossen") != abgeschlossen:
            continue
        if text_q and not _enthaelt(text_q, k.get("projektnummer"), k["projektname"], k.get("angebotsnr"),
                                    k["kunde"]):
            continue
        treffer.append(k)
    return _kappen(sorted(treffer, key=lambda k: k.get("projektnummer", k["in_nummer"]), reverse=True))


def _rechnung_kurz(i: dict) -> dict:
    client = i.get("client") or {}
    amount = float(i.get("amount") or 0)
    erg = {"rechnungsnr": i.get("number", ""), "kunde": client.get("name", ""),
           "kundennummer": client.get("number", ""), "datum": i.get("date", ""),
           "faellig": i.get("due_date", ""), "brutto": round(amount, 2),
           "offen_betrag": round(float(i.get("balance") or 0), 2),
           "status": INVOICE_STATUS.get(str(i.get("status_id")), str(i.get("status_id"))),
           "bestellnummer": i.get("po_number", ""),
           "netto": round(amount - float(i.get("total_taxes") or 0), 2),
           "bezahlt": round(float(i.get("paid_to_date") or 0), 2)}
    for rolle in ("projektnummer", "projektbezeichnung"):
        feld_ = K.feld("rechnung", rolle)
        if feld_:
            erg[rolle] = i.get(feld_, "")
    return _mit_zusatz(erg, i, "rechnung")


def projekt_lesen(projekt: str) -> dict:
    p = _projekt(projekt)
    erg = _projekt_kurz(p)
    try:
        erg["angebot"] = _angebot_kurz(_quote(erg["angebotsnr"])) if erg.get("angebotsnr") else None
    except ToolFehler:
        erg["angebot"] = None
    erg["rechnungen"] = [{"rechnungsnr": r.get("number", ""), "datum": r.get("date", ""),
                          "brutto": round(float(r.get("amount") or 0), 2),
                          "status": INVOICE_STATUS.get(str(r.get("status_id")), str(r.get("status_id")))}
                         for r in nn.get_invoices_for_project(p["id"])]
    return erg


# --- Rechnungen, Katalog ---------------------------------------------------------

def rechnungen_suchen(kunde: str = "", von: str = "", bis: str = "", offen: bool | None = None) -> dict:
    kunde_q = kunde.strip().lower()
    treffer = []
    for i in nn.get_invoices_listing():
        if i.get("is_deleted"):
            continue
        r = _rechnung_kurz(i)
        if kunde_q and not (kunde_q == r["kundennummer"].lower() or kunde_q in r["kunde"].lower()):
            continue
        if not _im_zeitraum(r["datum"], von, bis):
            continue
        ist_offen = r["offen_betrag"] > 0 and str(i.get("status_id")) in ("2", "3")
        if offen is not None and ist_offen != offen:
            continue
        treffer.append(r)
    return _kappen(sorted(treffer, key=lambda r: (r["datum"], r["rechnungsnr"]), reverse=True))


def _rechnung(rechnungsnr: str) -> dict:
    nr = rechnungsnr.strip().upper()
    for i in nn.get_invoices_listing():
        if i.get("is_deleted"):
            continue
        if (i.get("number") or "").upper() == nr:
            return i
    raise ToolFehler(f"Rechnung {nr} nicht gefunden.")


def _zahlungen_fuer_rechnung(rechnung_id: str) -> list[dict]:
    treffer = []
    for p in nn.get_payments_listing():
        if p.get("is_deleted"):
            continue
        for pm in p.get("paymentables") or []:
            if pm.get("invoice_id") == rechnung_id:
                treffer.append({"zahlungsnr": p.get("number", ""), "datum": p.get("date", ""),
                                "betrag": round(float(pm.get("amount") or 0), 2),
                                "referenz": p.get("transaction_reference", "") or "",
                                "status": PAYMENT_STATUS.get(str(p.get("status_id")), str(p.get("status_id"))),
                                "erstattet": round(float(pm.get("refunded") or 0), 2)})
    return treffer


def rechnung_lesen(rechnungsnr: str) -> dict:
    i = _rechnung(rechnungsnr)
    erg = _rechnung_kurz(i)
    erg["positionen"] = _positionen(i.get("line_items") or [])
    erg["private_notiz"] = i.get("private_notes", "") or ""
    erg["rabatt"] = _rabatt_text(i.get("discount"), i.get("is_amount_discount"))
    erg["zahlungen"] = _zahlungen_fuer_rechnung(i.get("id"))
    return erg


def _zahlung_kurz(p: dict) -> dict:
    client = p.get("client") or {}
    return {"zahlungsnr": p.get("number", ""), "datum": p.get("date", ""),
            "betrag": round(float(p.get("amount") or 0), 2),
            "kunde": client.get("name", ""), "kundennummer": client.get("number", ""),
            "referenz": p.get("transaction_reference", "") or "",
            "status": PAYMENT_STATUS.get(str(p.get("status_id")), str(p.get("status_id"))),
            "rechnungen": [inv.get("number", "") for inv in p.get("invoices") or []]}


def zahlungen_suchen(kunde: str = "", von: str = "", bis: str = "", rechnung: str = "") -> dict:
    kunde_q = kunde.strip().lower()
    rechnung_q = rechnung.strip().upper()
    treffer = []
    for p in nn.get_payments_listing():
        if p.get("is_deleted"):
            continue
        z = _zahlung_kurz(p)
        if kunde_q and not (kunde_q == z["kundennummer"].lower() or kunde_q in z["kunde"].lower()):
            continue
        if not _im_zeitraum(z["datum"], von, bis):
            continue
        if rechnung_q and rechnung_q not in [r.upper() for r in z["rechnungen"]]:
            continue
        treffer.append(z)
    return _kappen(sorted(treffer, key=lambda z: (z["datum"], z["zahlungsnr"]), reverse=True))


def _lieferant_kurz(v: dict) -> dict:
    kontakte = [{"name": f"{k.get('first_name', '')} {k.get('last_name', '')}".strip(),
                "email": k.get("email", "") or "", "telefon": k.get("phone", "") or ""}
               for k in v.get("contacts") or []]
    return {"name": v.get("name", ""), "nummer": v.get("number", ""), "strasse": v.get("address1", "") or "",
            "plz": v.get("postal_code", "") or "", "ort": v.get("city", "") or "",
            "telefon": v.get("phone", "") or "", "website": v.get("website", "") or "",
            "ust_id": v.get("vat_number", "") or "", "kontakte": kontakte}


def lieferanten_auflisten() -> dict:
    treffer = [_lieferant_kurz(v) for v in nn.get_vendors_listing() if not v.get("is_deleted")]
    return _kappen(sorted(treffer, key=lambda v: v["name"].lower()))


_DOKUMENTE_PFAD = {"kunde": "clients", "angebot": "quotes", "rechnung": "invoices"}


def _unix_datum(ts) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(int(ts), tz=_BERLIN).strftime("%d.%m.%Y")


def dokumente_auflisten(art: str, nummer: str) -> dict:
    art = (art or "").strip().lower()
    if art not in _DOKUMENTE_PFAD:
        raise ToolFehler(f"art muss eines von {', '.join(_DOKUMENTE_PFAD)} sein.")
    if art == "kunde":
        obj = _kunde(nummer)
    elif art == "angebot":
        obj = _quote(nummer)
    else:
        obj = _rechnung(nummer)
    dokumente = nn.get_entity_documents(_DOKUMENTE_PFAD[art], obj["id"])
    erg_dokumente = [{"name": d.get("name", ""), "typ": d.get("type", ""),
                      "groesse_kb": round(float(d.get("size") or 0) / 1024, 1),
                      "datum": _unix_datum(d.get("created_at")),
                      "oeffentlich": bool(d.get("is_public"))} for d in dokumente if not d.get("is_deleted")]
    return {"art": art, "nummer": nummer, "dokumente": erg_dokumente,
            "hinweis": "Nur Liste; Inhalte sind über den MCP nicht abrufbar."}


def produkte_auflisten() -> list[dict]:
    return [{"produkt": p["product_key"], "text": p["notes"], "preis": p["price"], "mwst": p["tax_rate1"],
             "steuer": p["tax_name1"]}
            for p in nn.get_products()]


def angebot_vorlagen_auflisten() -> list[dict]:
    return [{"name": v["name"], "produkte": v["produkte"], "verkaufsbedingungen": v["verkaufsbedingungen"]}
            for v in list_angebot_vorlagen()]


# --- Rohdaten ----------------------------------------------------------------------

def _bereinigen(obj):
    """Entfernt rekursiv sensible/technische Schlüssel (SENSIBEL, TECHNIK, Muster-Sperre) und leere
    Werte (None, '', [], {}) aus dicts/Listen. Zahlen wie 0 und False bleiben erhalten."""
    if isinstance(obj, dict):
        erg = {}
        for k, v in obj.items():
            if k in SENSIBEL or k in TECHNIK or _gesperrt(k):
                continue
            v = _bereinigen(v)
            if v is None or v == "" or v == [] or v == {}:
                continue
            erg[k] = v
        return erg
    if isinstance(obj, list):
        return [_bereinigen(x) for x in obj]
    return obj


def in_rohdaten(typ: str, nummer: str) -> dict:
    if typ not in ROHDATEN_TYPEN:
        raise ToolFehler(f"typ muss eines von {', '.join(ROHDATEN_TYPEN)} sein.")
    pfad, schluessel_felder = _rohdaten_quelle(typ)
    nummer_q = nummer.strip().lower()
    treffer = None
    for obj in nn.get_listing(pfad):
        if obj.get("is_deleted"):
            continue
        if any(nummer_q and nummer_q == str(obj.get(f) or "").strip().lower() for f in schluessel_felder):
            treffer = obj
            break
    if treffer is None:
        raise ToolFehler(f"{typ} {nummer} nicht gefunden.")
    praefixe = _ROHDATEN_PRAEFIX.get(typ, ())
    beschriftungen = {k: v for k, v in nn.get_custom_field_labels().items()
                      if any(k.startswith(p) for p in praefixe)}
    return {"typ": typ, "daten": _bereinigen(treffer), "custom_field_beschriftungen": beschriftungen}


# --- Schreiben -------------------------------------------------------------------

def _pruefe_kontakte_erhalten(vorher: int, client: dict, name: str):
    """IN ersetzt beim Client-PUT die Kontaktliste. Ist sie danach kürzer, ist etwas schiefgelaufen."""
    nachher = len(client.get("contacts") or [])
    if nachher < vorher:
        log.error("IN-MCP: Kontaktliste von %s geschrumpft (%d → %d)", name, vorher, nachher)
        raise ToolFehler(f"Achtung: Bei {name} fehlen nach dem Speichern Kontakte ({vorher} → {nachher}). "
                         "Bitte in Invoice Ninja prüfen und Bescheid geben.")


def kontakt_speichern(aufrufer: str, kunde: str, vorname: str, nachname: str, email: str, anrede: str = "",
                      telefon: str | None = None, kontakt_id: str = "", mobil: str | None = None,
                      position: str | None = None, abteilung: str | None = None,
                      email_aendern: bool = False) -> str:
    """Optionale Felder mit None bleiben beim Ändern unverändert. Anrede nur mit Rolle kontakt.anrede.

    Die E-Mail eines bestehenden Kontakts (kontakt_id gesetzt) wird nur mit email_aendern=True
    geändert (M1: sonst könnte eine per Prompt-Injection untergeschobene Adresse künftige
    Rechnungen/Belege und Portalzugang an Dritte umleiten)."""
    anrede_feld = K.feld("kontakt", "anrede")
    if not anrede_feld:
        anrede = ""
    k = {"anrede": anrede, "vorname": vorname, "nachname": nachname, "email": email, "telefon": telefon or ""}
    zusatz = {}
    for rolle, wert in zip(KONTAKT_ROLLEN, (mobil, position, abteilung)):
        feld_ = K.feld("kontakt", rolle)
        if feld_ and wert is not None:
            zusatz[feld_] = wert.strip()
    if telefon is not None:
        zusatz["phone"] = telefon.strip()
    fehler = angebot.pruefe_kontakt(k, anrede_pflicht=bool(anrede_feld))
    if fehler:
        raise ToolFehler(" ".join(fehler))
    c = _kunde(kunde)
    bestehende = c.get("contacts") or []
    if kontakt_id:
        if not any(x.get("id") == kontakt_id for x in bestehende):
            raise ToolFehler(f"Kontakt {kontakt_id} gehört nicht zu {c.get('name', '')}.")
        alt = next(x for x in bestehende if x.get("id") == kontakt_id)
        alte_email = (alt.get("email") or "").strip()
        if not email_aendern and alte_email.lower() != email.strip().lower():
            raise ToolFehler(f"Die E-Mail von {alte_email} auf {email.strip()} zu ändern braucht das "
                             "Argument email_aendern=true - bitte nur auf ausdrücklichen Wunsch setzen.")
        liste = [dict(x) for x in bestehende]
        for x in liste:
            if x.get("id") == kontakt_id:
                x.update(first_name=vorname.strip(), last_name=nachname.strip(), email=email.strip(), **zusatz)
                if anrede_feld:
                    x[anrede_feld] = anrede
        aktion = "geändert"
    else:
        doppelt = [x for x in bestehende if (x.get("email") or "").strip().lower() == email.strip().lower()]
        if doppelt:
            raise ToolFehler(f"Bei {c.get('name', '')} gibt es schon einen Kontakt mit {email} "
                             f"(kontakt_id {doppelt[0].get('id')}). Zum Ändern kontakt_id angeben.")
        liste = angebot.kontaktliste_fuer_update(bestehende, [k], anrede_feld)
        liste[-1].update(zusatz)
        aktion = "angelegt"
    neu = nn.update_client_contacts(c["id"], liste)
    _pruefe_kontakte_erhalten(len(bestehende), neu, c.get("name", ""))
    log.info("IN-MCP [%s] kontakt_speichern %s %s (%s)", aufrufer, c.get("number"), email.strip(), aktion)
    name = " ".join(teil for teil in (anrede, vorname.strip(), nachname.strip()) if teil)
    return f"Kontakt {name} bei {c.get('name', '')} {aktion}."


def kunde_aendern(aufrufer: str, kunde: str, felder: dict) -> str:
    if not felder:
        raise ToolFehler("Keine Felder angegeben.")
    unerlaubt = sorted(set(felder) - set(KUNDE_FELDER))
    if unerlaubt:
        raise ToolFehler(f"Nicht änderbar: {', '.join(unerlaubt)}. Erlaubt sind: {', '.join(KUNDE_FELDER)}.")
    c = _kunde(kunde)
    bestehende = c.get("contacts") or []
    # Kontakte vollständig mitschicken: IN ersetzt die Liste beim Client-PUT
    payload = {f: str(w) for f, w in felder.items()}
    payload["contacts"] = [dict(x) for x in bestehende]
    neu = nn.update_client(c["id"], payload)
    _pruefe_kontakte_erhalten(len(bestehende), neu, c.get("name", ""))
    log.info("IN-MCP [%s] kunde_aendern %s (%s)", aufrufer, c.get("number"), ", ".join(sorted(felder)))
    return f"{c.get('name', '')}: {', '.join(sorted(felder))} geändert."


def _notiz(alt: str, text: str, modus: str, heute: date) -> str:
    zeile = f"{heute:%d.%m.%Y}: {text.strip()}"
    if modus == "ersetzen" or not (alt or "").strip():
        return zeile
    return f"{alt.rstrip()}\n{zeile}"


def _quote_oder_none(angebotsnr: str) -> dict | None:
    try:
        return _quote(angebotsnr)
    except ToolFehler:
        return None


def _projekt_oder_none(projekt: str) -> dict | None:
    try:
        return _projekt(projekt)
    except ToolFehler:
        return None


def notiz_setzen(aufrufer: str, ziel: str, text: str, modus: str = "anhaengen",
                 heute: date | None = None) -> str:
    """Ziel ist ein Angebot (Angebotsnummer) oder ein Projekt. Projektnotizen gehen ins Feld der Rolle
    projekt.notiz, ohne Rolle in private_notes. Treffen beide zu (getrennte Zähler, z. B. Angebot und
    Projekt mit derselben Nummer auf einer neutralen Instanz), wird nichts geschrieben - Aufrufer muss
    eindeutig machen, welches Ziel gemeint ist."""
    if modus not in ("anhaengen", "ersetzen"):
        raise ToolFehler("modus muss 'anhaengen' oder 'ersetzen' sein.")
    if not (text or "").strip():
        raise ToolFehler("Der Notiztext ist leer.")
    heute = heute or date.today()
    ziel = ziel.strip()
    q = _quote_oder_none(ziel)
    p = _projekt_oder_none(ziel)
    if q is not None and p is not None:
        raise ToolFehler(f"{ziel} ist sowohl Angebot als auch Projekt. Bitte die IN-ID des Projekts "
                         "angeben, oder für das Angebot die Angebotsnummer eindeutig machen.")
    if q is not None:
        nn.update_quote_private_notes(q["id"], _notiz(q.get("private_notes", ""), text, modus, heute))
        wo = f"Angebot {q['number']} (private Notiz)"
    elif p is not None:
        notiz_feld = K.feld("projekt", "notiz")
        feld_ = notiz_feld or "private_notes"
        if not nn.update_project(p["id"], {feld_: _notiz(p.get(feld_, ""), text, modus, heute)}):
            raise ToolFehler("Invoice Ninja ist nicht konfiguriert, die Notiz wurde nicht gespeichert.")
        projektnr = K.feld("projekt", "projektnummer")
        nummer = (p.get(projektnr) if projektnr else "") or p.get("number") or p["id"]
        wo = f"Projekt {nummer} ({'Notizfeld' if notiz_feld else 'private Notiz'})"
    else:
        raise ToolFehler(f"Weder Angebot noch Projekt {ziel} gefunden. "
                         "Angebotsnummer, Projektnummer oder IN-ID angeben.")
    log.info("IN-MCP [%s] notiz_setzen %s (%s)", aufrufer, ziel, modus)
    return f"Notiz an {wo} {'ersetzt' if modus == 'ersetzen' else 'angehängt'}."


def _vkb_aktiv() -> bool:
    """Kennt die Instanz überhaupt Verkaufsbedingungen (Liste oder Muster)?"""
    return bool(K.verkaufsbedingungen or K.verkaufsbedingungen_muster)


def _vkb_keys(produkte: dict[str, dict]) -> set[str]:
    """Regel 1: konfigurierte Verkaufsbedingungen plus alle Katalog-Keys, auf die das Muster passt
    (case-sensitiv). Konfigurierte Keys werden auf die Schreibweise im Katalog abgebildet."""
    katalog_ci = {schluessel.lower(): schluessel for schluessel in produkte}
    keys = {katalog_ci.get(k.lower(), k) for k in K.verkaufsbedingungen}
    if K.verkaufsbedingungen_muster:
        muster = re.compile(K.verkaufsbedingungen_muster)
        keys |= {k for k in produkte if muster.search(k)}
    return keys


def _positionen_bauen(positionen: list[dict], produkte: dict[str, dict],
                      vkb_keys: set[str] | frozenset = frozenset()) -> tuple[list[dict], list[dict]]:
    """Katalogpositionen aus {produkt, menge?, preis?, text?}; MwSt. immer aus dem Katalog.
    Positionen mit einem Key aus vkb_keys kommen getrennt als feste Positionen zurück
    (liste, vkb_positionen) - der Aufrufer stellt sie ans Ende. Der Produktschlüssel wird
    case-insensitiv auf den kanonischen Katalog-Key abgebildet."""
    produkte_ci = {schluessel.lower(): produkt for schluessel, produkt in produkte.items()}
    vkb_ci = {schluessel.lower() for schluessel in vkb_keys}
    liste, vkb_positionen = [], []
    for pos in positionen:
        key = (pos.get("produkt") or "").strip()
        produkt = produkte_ci.get(key.lower())
        if produkt is None:
            raise ToolFehler(f"Produkt {key or '(leer)'} gibt es im IN-Katalog nicht. Siehe produkte_auflisten.")
        menge_roh = pos.get("menge")
        if menge_roh is None:
            menge = 1.0
        else:
            try:
                menge = float(menge_roh)
            except (TypeError, ValueError):
                raise ToolFehler(f"Position {key}: Menge muss eine Zahl größer 0 sein.")
            if menge <= 0:
                raise ToolFehler(f"Position {key}: Menge muss eine Zahl größer 0 sein.")
        ist_vkb = key.lower() in vkb_ci
        p = angebot.katalog_position(produkt, fest=ist_vkb)
        p["quantity"] = menge
        if pos.get("preis") is not None:
            try:
                preis = float(pos["preis"])
            except (TypeError, ValueError):
                raise ToolFehler(f"Position {key}: Preis muss eine Zahl ab 0 sein.")
            if preis < 0:
                raise ToolFehler(f"Position {key}: Preis muss eine Zahl ab 0 sein.")
            p["cost"] = preis
        if pos.get("text"):
            p["notes"] = pos["text"]
        if ist_vkb:
            p["eigener_text"] = bool(pos.get("text"))
            vkb_positionen.append(p)
        else:
            liste.append(p)
    return liste, vkb_positionen


def _vkb_setzen(liste: list[dict], vkb_positionen: list[dict], verkaufsbedingungen: str,
                produkte: dict[str, dict], vkb_keys: set[str], bisher: list[str]) -> tuple[tuple, str]:
    """Regeln 2-5: hängt höchstens eine Verkaufsbedingungen-Position an liste an. Liefert die Keys,
    deren Vorhandensein pruefe_positionen verlangt (leer = keine Pflicht), und den Text für die
    Rückmeldung (leer, wenn die Instanz keine Verkaufsbedingungen kennt)."""
    parameter = (verkaufsbedingungen or "").strip()
    if not _vkb_aktiv():
        if parameter:
            raise ToolFehler("Diese Instanz kennt keine Verkaufsbedingungen; verkaufsbedingungen weglassen.")
        return (), ""
    keys_ci = {k.lower(): k for k in vkb_keys}
    keine = parameter.lower() == "keine"
    if parameter and not keine:
        if parameter.lower() not in keys_ci:
            raise ToolFehler(f"verkaufsbedingungen muss eines von {', '.join(sorted(vkb_keys))} "
                             "oder 'keine' sein.")
        parameter = keys_ci[parameter.lower()]
    if len(vkb_positionen) > 1:
        raise ToolFehler("Höchstens eine Verkaufsbedingungen-Position erlaubt, übergeben: "
                         f"{', '.join(p['product_key'] for p in vkb_positionen)}.")
    pflicht = () if keine else tuple(sorted(vkb_keys))
    hinweis = ""
    if vkb_positionen:
        pos = vkb_positionen[0]
        vkb = pos["product_key"]
        herkunft = "aus der Positionsliste, eigener Text" if pos.get("eigener_text") \
            else "aus der Positionsliste, Katalogtext"
        if parameter and parameter != vkb:
            hinweis = (f" Parameter verkaufsbedingungen={verkaufsbedingungen.strip()} ignoriert, "
                       f"Position {vkb} aus der Liste verwendet.")
        liste.append(pos)
        return tuple(sorted(vkb_keys)), f" Verkaufsbedingungen: {vkb} ({herkunft}).{hinweis}"
    if keine:
        return pflicht, " Verkaufsbedingungen: keine Verkaufsbedingungen."
    bisher_keys = [keys_ci[b.lower()] for b in bisher if b and b.lower() in keys_ci]
    if parameter:
        vkb, herkunft = parameter, "Parameter"
    elif bisher_keys:
        vkb, herkunft = bisher_keys[-1], "bisherige des Angebots"
    elif K.standard_verkaufsbedingungen:
        vkb, herkunft = K.standard_verkaufsbedingungen, "Standard"
    else:
        return pflicht, ""   # pruefe_positionen meldet "Die Verkaufsbedingungen fehlen."
    produkte_ci = {k.lower(): p for k, p in produkte.items()}
    if vkb.lower() not in produkte_ci:
        raise ToolFehler(f"Produkt {vkb} fehlt im IN-Katalog.")
    position = angebot.katalog_position(produkte_ci[vkb.lower()], fest=True)
    liste.append(position)
    return pflicht, f" Verkaufsbedingungen: {position['product_key']} ({herkunft})."


def angebotsentwurf_anlegen(aufrufer: str, kunde: str, kontakt_emails: list[str], positionen: list[dict],
                            bezeichnung: str = "", gueltig_bis: str = "", verkaufsbedingungen: str = "",
                            heute: date | None = None) -> str:
    heute = heute or date.today()
    try:
        bis = date.fromisoformat(gueltig_bis) if gueltig_bis else \
            angebot.gueltig_bis_standard(heute, K.gueltig_standard_tage)
    except ValueError:
        raise ToolFehler(f"gueltig_bis '{gueltig_bis}' ist kein Datum im Format JJJJ-MM-TT.")
    produkte = {p["product_key"]: p for p in nn.get_products()}
    vkb_keys = _vkb_keys(produkte) if _vkb_aktiv() else set()
    liste, vkb_positionen = _positionen_bauen(positionen, produkte, vkb_keys)
    pflicht, vkb_text = _vkb_setzen(liste, vkb_positionen, verkaufsbedingungen, produkte, vkb_keys, [])
    bezeichnung_feld = K.feld("angebot", "bezeichnung")
    fehler = angebot.pruefe_kopf(bezeichnung, bis, heute, bezeichnung_pflicht=bool(bezeichnung_feld),
                                 min_tage=K.gueltig_min_tage, max_tage=K.gueltig_max_tage) \
        + angebot.pruefe_positionen(liste, pflicht, K.individuell_produkt)
    if fehler:
        raise ToolFehler(" ".join(fehler))
    c = _kunde(kunde)
    ids = angebot.kontakt_ids_fuer(c, kontakt_emails)
    gefunden = {(x.get("email") or "").strip().lower() for x in c.get("contacts") or [] if x.get("id") in ids}
    fehlend = [e for e in kontakt_emails if e.strip().lower() not in gefunden]
    if not ids or fehlend:
        raise ToolFehler(f"Empfänger nicht bei {c.get('name', '')} gefunden: {', '.join(fehlend) or '(keine)'}. "
                         "Zuerst mit kontakt_speichern anlegen.")
    quote = nn.create_quote(angebot.quote_payload(c["id"], ids, liste, bezeichnung, heute, bis, bezeichnung_feld))
    nr, qid = quote.get("number", ""), quote.get("id", "")
    hinweis = ""
    try:
        log_angebot(nr, qid, c["id"])
    except Exception:
        # Das Angebot steht schon in IN - ein Fehler hier darf den Erfolg nicht verschlucken,
        # der Aufrufer soll nicht auf Verdacht einen zweiten Entwurf anlegen.
        log.exception("IN-MCP: log_angebot fehlgeschlagen für %s", nr)
        hinweis = (" Hinweis: Eintrag ins angebot_log fehlgeschlagen, der Prüfbericht erfasst "
                  "dieses Angebot nicht.")
    log.info("IN-MCP [%s] angebotsentwurf_anlegen %s für %s", aufrufer, nr, c.get("number"))
    netto, _mwst, brutto = angebot.summen(liste)
    return (f"Angebotsentwurf {nr} für {c.get('name', '')} angelegt: {netto:.2f} € netto, "
            f"{brutto:.2f} € brutto, gültig bis {bis:%d.%m.%Y}.{vkb_text} Status Entwurf, nicht versendet. "
            "Bitte in Invoice Ninja prüfen und von dort versenden." + hinweis)


def _entwurf_pruefen(q: dict) -> None:
    """Sperren für Änderungen an einem Angebotsentwurf: nur Status Entwurf, nicht archiviert, nicht
    bestellt, nicht abgeschlossen. Gemeinsam für angebotsentwurf_positionen_setzen und
    angebotsentwurf_kopf_setzen."""
    status = str(q.get("status_id"))
    if q.get("archived_at") or status != "1":
        was = "archiviert" if q.get("archived_at") else QUOTE_STATUS.get(status, status)
        raise ToolFehler(f"Angebot {q['number']} ist {was}, nicht Entwurf. Nur Entwürfe lassen sich ändern.")
    sperren = (("bestellt", "ist bereits bestellt. Nur unbestellte Entwürfe lassen sich ändern."),
               ("abgeschlossen", "ist als abgeschlossen markiert. Nur Entwürfe lassen sich ändern."))
    for rolle, grund in sperren:
        feld_ = K.feld("angebot", rolle)
        if feld_ and _ja(q.get(feld_)):
            raise ToolFehler(f"Angebot {q['number']} {grund}")


def angebotsentwurf_positionen_setzen(aufrufer: str, angebotsnr: str, positionen: list[dict],
                                      verkaufsbedingungen: str = "") -> str:
    """Ersetzt die komplette Positionsliste eines Angebotsentwurfs. MwSt. aus dem Katalog,
    Verkaufsbedingungen nach _vkb_setzen (Position aus der Liste, sonst Parameter, sonst die
    bisherige, sonst der Standard)."""
    q = _quote(angebotsnr)
    _entwurf_pruefen(q)
    produkte = {p["product_key"]: p for p in nn.get_products()}
    vkb_keys = _vkb_keys(produkte) if _vkb_aktiv() else set()
    liste, vkb_positionen = _positionen_bauen(positionen, produkte, vkb_keys)
    bisher = [i.get("product_key") or "" for i in q.get("line_items") or []]
    pflicht, vkb_text = _vkb_setzen(liste, vkb_positionen, verkaufsbedingungen, produkte, vkb_keys, bisher)
    fehler = angebot.pruefe_positionen(liste, pflicht, K.individuell_produkt)
    if fehler:
        raise ToolFehler(" ".join(fehler))
    brutto_vorher = float(q.get("amount") or 0)
    netto_vorher = round(brutto_vorher - float(q.get("total_taxes") or 0), 2)
    antwort = nn.update_quote_line_items(q["id"], angebot.line_items(liste))
    log.info("IN-MCP [%s] angebotsentwurf_positionen_setzen %s (%d Positionen)", aufrufer, q["number"], len(liste))
    if "amount" in antwort:
        brutto = round(float(antwort["amount"]), 2)
        netto = round(brutto - float(antwort.get("total_taxes") or 0), 2)
    else:
        netto, _mwst, brutto = angebot.summen(liste)
    return (f"Angebotsentwurf {q['number']}: {len(liste)} Positionen gesetzt. "
            f"Netto {netto_vorher:.2f} € → {netto:.2f} €, brutto {brutto_vorher:.2f} € → {brutto:.2f} €."
            f"{vkb_text} Status Entwurf, nicht versendet.")


_KOPF_LABEL = {"gueltig_bis": "Gültig bis", "bezeichnung": "Bezeichnung", "oeffentliche_notiz": "öffentliche Notiz"}


def angebotsentwurf_kopf_setzen(aufrufer: str, angebotsnr: str, gueltig_bis: str = "",
                                bezeichnung: str | None = None, oeffentliche_notiz: str | None = None,
                                heute: date | None = None) -> str:
    """Ändert Kopf-Felder eines Angebotsentwurfs: gueltig_bis (JJJJ-MM-TT, Grenzen aus der Konfiguration),
    bezeichnung (nur mit Rolle angebot.bezeichnung, bereinigt wie beim Anlegen, nicht leer) und
    oeffentliche_notiz (leerer String leert sie). Mindestens eines der drei Felder ist nötig. Sperren
    wie angebotsentwurf_positionen_setzen (_entwurf_pruefen)."""
    if not gueltig_bis and bezeichnung is None and oeffentliche_notiz is None:
        raise ToolFehler("Bitte mindestens eines der Felder gueltig_bis, bezeichnung oder "
                         "oeffentliche_notiz angeben.")
    q = _quote(angebotsnr)
    _entwurf_pruefen(q)
    heute = heute or date.today()
    felder: dict = {}
    geaendert: list[str] = []
    if gueltig_bis:
        try:
            bis = date.fromisoformat(gueltig_bis)
        except ValueError:
            raise ToolFehler(f"gueltig_bis '{gueltig_bis}' ist kein Datum im Format JJJJ-MM-TT.")
        if bis < heute + timedelta(days=K.gueltig_min_tage):
            raise ToolFehler(f"Das Angebot muss mindestens {K.gueltig_min_tage} Tage gültig sein.")
        if bis > heute + timedelta(days=K.gueltig_max_tage):
            raise ToolFehler(f"Das Angebot darf höchstens {K.gueltig_max_tage} Tage gültig sein.")
        felder["due_date"] = bis.isoformat()
        geaendert.append("gueltig_bis")
    if bezeichnung is not None:
        bezeichnung_feld = K.feld("angebot", "bezeichnung")
        if not bezeichnung_feld:
            raise ToolFehler("Diese Instanz kennt keine Bezeichnung für Angebote; bezeichnung weglassen.")
        bereinigt = angebot.bereinige_bezeichnung(bezeichnung)
        if not bereinigt:
            raise ToolFehler("Bitte einen Projektnamen / eine Projektbezeichnung eintragen.")
        felder[bezeichnung_feld] = bereinigt
        geaendert.append("bezeichnung")
    if oeffentliche_notiz is not None:
        felder["public_notes"] = oeffentliche_notiz
        geaendert.append("oeffentliche_notiz")
    nn.update_quote(q["id"], felder)
    log.info("IN-MCP [%s] angebotsentwurf_kopf_setzen %s (%s)", aufrufer, q["number"], ", ".join(geaendert))
    namen = ", ".join(_KOPF_LABEL[g] for g in geaendert)
    return f"Angebot {q['number']}: {namen} geändert."


def _steuersatz(mwst: str) -> dict:
    """Steuersatz aus IN über den Namen ('MwSt.') oder den Satz ('19', '19 %')."""
    saetze = nn.get_tax_rates()
    wert = str(mwst).strip()
    treffer = [s for s in saetze if s["name"].strip().lower() == wert.lower()]
    if not treffer:
        try:
            zahl = float(wert.replace("%", "").replace(",", ".").strip())
        except ValueError:
            zahl = None
        if zahl is not None:
            treffer = [s for s in saetze if s["rate"] == zahl]
    if len(treffer) != 1:
        vorhanden = ", ".join(f"{s['name']} {s['rate']:g} %" for s in saetze) or "(keine)"
        grund = "ist nicht eindeutig" if treffer else "gibt es nicht"
        raise ToolFehler(f"Steuersatz '{mwst}' {grund}. Vorhanden: {vorhanden}.")
    return treffer[0]


def produkt_speichern(aufrufer: str, produkt: str, text: str | None = None, preis: float | None = None,
                      mwst: str | None = None) -> str:
    """Ändert ein Katalogprodukt (nur angegebene Felder) oder legt es an (text, preis, mwst Pflicht).
    Der Schlüssel wird nie umbenannt, gelöscht wird nie."""
    key = (produkt or "").strip()
    if not key:
        raise ToolFehler("Der Produktschlüssel ist leer.")
    felder = {}
    if text is not None:
        if not text.strip():
            raise ToolFehler("Der Produkttext ist leer.")
        felder["notes"] = text.strip()
    if preis is not None:
        try:
            wert = float(preis)
        except (TypeError, ValueError):
            raise ToolFehler("Preis muss eine Zahl ab 0 sein.")
        if wert < 0:
            raise ToolFehler("Preis muss eine Zahl ab 0 sein.")
        felder["price"] = wert
    if mwst is not None:
        satz = _steuersatz(mwst)
        felder.update(tax_name1=satz["name"], tax_rate1=satz["rate"])
    angaben = [name for name, feld in (("text", "notes"), ("preis", "price"), ("mwst", "tax_name1"))
               if feld in felder]
    bestehend = next((p for p in nn.get_products() if p["product_key"].lower() == key.lower()), None)
    if bestehend:
        if not felder:
            raise ToolFehler("Keine Felder angegeben. Änderbar sind text, preis und mwst.")
        nn.update_product(bestehend["id"], felder)
        key = bestehend["product_key"]
        ergebnis = f"geändert ({', '.join(angaben)})"
    else:
        fehlend = [n for n in ("text", "preis", "mwst") if n not in angaben]
        if fehlend:
            raise ToolFehler(f"Produkt {key} gibt es noch nicht. Zum Anlegen fehlen: {', '.join(fehlend)}.")
        if not PRODUKT_KEY_MUSTER.fullmatch(key):
            raise ToolFehler("Produktschlüssel darf nur Buchstaben, Ziffern, Leerzeichen und . - / _ "
                             "enthalten (höchstens 100 Zeichen).")
        nn.create_product({"product_key": key, **felder, "tax_id": K.neue_steuerkategorie})
        ergebnis = "angelegt"
    log.info("IN-MCP [%s] produkt_speichern %s (%s)", aufrufer, key, ergebnis)
    return (f"Produkt {key} {ergebnis}. Bestehende Angebote bleiben unverändert; ein Entwurf übernimmt "
            "neue Katalogwerte erst mit angebotsentwurf_positionen_setzen.")


# --- Rechnungen ------------------------------------------------------------------
# Nur Entwürfe (Status 1) sind über den MCP änderbar, auch wenn Invoice Ninja mehr erlauben würde
# (lock_invoices) - versendete Rechnungen werden nur per Storno korrigiert. Gelöscht wird nie: die
# Rechnungsnummer ist beim Anlegen schon vergeben.

RECHNUNGSNR_HINWEIS = "Rechnungsnummer ist vergeben. Nicht löschen – eine falsche Rechnung stornieren."


def _invoice_status(i: dict) -> str:
    status = str(i.get("status_id"))
    return INVOICE_STATUS.get(status, status)


def _rechnung_frisch(rechnungsnr: str) -> dict:
    """Rechnung per Nummer (Liste der neuesten 500), danach frisch aus IN gelesen - entscheidend für
    alle Sperren ist der aktuelle Stand, nicht die Liste."""
    i = nn.get_invoice(_rechnung(rechnungsnr)["id"])
    if not i or i.get("is_deleted"):
        raise ToolFehler(f"Rechnung {rechnungsnr.strip().upper()} ist gelöscht.")
    return i


def _rechnungsentwurf_pruefen(i: dict) -> None:
    """Nur Entwürfe, die nicht archiviert sind, lassen sich über den MCP ändern."""
    status = str(i.get("status_id"))
    if i.get("archived_at") or status != "1":
        was = "archiviert" if i.get("archived_at") else _invoice_status(i)
        raise ToolFehler(f"Rechnung {i.get('number')} ist {was}, nicht Entwurf. Nur Entwürfe lassen sich "
                         "ändern; versendete Rechnungen werden per Storno korrigiert.")


def _datum(wert: str, name: str) -> date:
    try:
        return date.fromisoformat(wert.strip())
    except ValueError:
        raise ToolFehler(f"{name} '{wert}' ist kein Datum im Format JJJJ-MM-TT.")


def _datum_oder_none(wert) -> date | None:
    try:
        return date.fromisoformat(str(wert or ""))
    except ValueError:
        return None


def _faellig_pruefen(datum_: date | None, faellig: date | None) -> None:
    if datum_ and faellig and faellig < datum_:
        raise ToolFehler(f"Die Fälligkeit {faellig:%d.%m.%Y} liegt vor dem Rechnungsdatum {datum_:%d.%m.%Y}.")


def _rechnungspositionen(positionen: list[dict]) -> list[dict]:
    """Katalogpositionen wie bei Angeboten, aber ohne Verkaufsbedingungen-Logik: auch
    Verkaufsbedingungen-Positionen bleiben normale Positionen an ihrer Stelle, nichts wird angehängt."""
    produkte = {p["product_key"]: p for p in nn.get_products()}
    liste, _vkb = _positionen_bauen(positionen, produkte)
    fehler = angebot.pruefe_positionen(liste, (), K.individuell_produkt)
    if fehler:
        raise ToolFehler(" ".join(fehler))
    return liste


def _summen_aus(antwort: dict, liste: list[dict] | None = None) -> tuple[float, float]:
    """(netto, brutto) aus der IN-Antwort, sonst aus den Positionen gerechnet."""
    if "amount" in antwort:
        brutto = round(float(antwort["amount"]), 2)
        return round(brutto - float(antwort.get("total_taxes") or 0), 2), brutto
    netto, _mwst, brutto = angebot.summen(liste or [])
    return netto, brutto


def rechnungsentwurf_anlegen(aufrufer: str, kunde: str, positionen: list[dict], kontakt_emails: list[str] = (),
                             projekt: str = "", bestellnummer: str = "", datum: str = "", faellig: str = "",
                             oeffentliche_notiz: str = "") -> str:
    """Legt eine Rechnung als Entwurf an. kontakt_emails leer = Empfänger nach IN-Standard. projekt
    (Projektnummer, IN-Nummer oder IN-ID) setzt project_id und - mit den Rollen - Projektnummer und
    -bezeichnung der Rechnung."""
    datum_ = _datum(datum, "datum") if datum else None
    faellig_ = _datum(faellig, "faellig") if faellig else None
    _faellig_pruefen(datum_, faellig_)
    liste = _rechnungspositionen(positionen)
    c = _kunde(kunde)
    payload: dict = {"client_id": c["id"], "line_items": angebot.line_items(liste)}
    if kontakt_emails:
        ids = angebot.kontakt_ids_fuer(c, list(kontakt_emails))
        gefunden = {(x.get("email") or "").strip().lower() for x in c.get("contacts") or [] if x.get("id") in ids}
        fehlend = [e for e in kontakt_emails if e.strip().lower() not in gefunden]
        if fehlend:
            raise ToolFehler(f"Empfänger nicht bei {c.get('name', '')} gefunden: {', '.join(fehlend)}. "
                             "Zuerst mit kontakt_speichern anlegen.")
        payload["invitations"] = [{"client_contact_id": cid} for cid in ids]
    if projekt:
        p = _projekt(projekt)
        if p.get("client_id") and p["client_id"] != c["id"]:
            raise ToolFehler(f"Projekt {projekt.strip()} gehört nicht zu {c.get('name', '')}.")
        payload["project_id"] = p["id"]
        nr_feld, bez_feld = K.feld("rechnung", "projektnummer"), K.feld("rechnung", "projektbezeichnung")
        if nr_feld:
            quelle = K.feld("projekt", "projektnummer")
            payload[nr_feld] = (p.get(quelle) if quelle else p.get("number")) or ""
        if bez_feld:
            quelle = K.feld("projekt", "name")
            payload[bez_feld] = (p.get(quelle) if quelle else p.get("name")) or ""
    if bestellnummer:
        payload["po_number"] = bestellnummer.strip()
    if datum_:
        payload["date"] = datum_.isoformat()
    if faellig_:
        payload["due_date"] = faellig_.isoformat()
    if oeffentliche_notiz:
        payload["public_notes"] = oeffentliche_notiz
    rechnung = nn.create_invoice(payload)
    nr = rechnung.get("number", "")
    log.info("IN-MCP [%s] rechnungsentwurf_anlegen %s für %s", aufrufer, nr, c.get("number"))
    netto, brutto = _summen_aus(rechnung, liste)
    return (f"Rechnungsentwurf {nr} für {c.get('name', '')} angelegt: {netto:.2f} € netto, {brutto:.2f} € "
            f"brutto. Status Entwurf, nicht versendet. {RECHNUNGSNR_HINWEIS}")


def rechnungsentwurf_positionen_setzen(aufrufer: str, rechnungsnr: str, positionen: list[dict]) -> str:
    """Ersetzt die komplette Positionsliste eines Rechnungsentwurfs."""
    i = _rechnung_frisch(rechnungsnr)
    _rechnungsentwurf_pruefen(i)
    liste = _rechnungspositionen(positionen)
    brutto_vorher = round(float(i.get("amount") or 0), 2)
    netto_vorher = round(brutto_vorher - float(i.get("total_taxes") or 0), 2)
    antwort = nn.update_invoice(i["id"], {"line_items": angebot.line_items(liste)})
    log.info("IN-MCP [%s] rechnungsentwurf_positionen_setzen %s (%d Positionen)", aufrufer, i["number"], len(liste))
    netto, brutto = _summen_aus(antwort, liste)
    return (f"Rechnungsentwurf {i['number']}: {len(liste)} Positionen gesetzt. "
            f"Netto {netto_vorher:.2f} € → {netto:.2f} €, brutto {brutto_vorher:.2f} € → {brutto:.2f} €. "
            "Status Entwurf, nicht versendet.")


_RECHNUNG_KOPF = (("datum", "date", "Rechnungsdatum"), ("faellig", "due_date", "Fälligkeit"),
                  ("bestellnummer", "po_number", "Bestellnummer"),
                  ("oeffentliche_notiz", "public_notes", "öffentliche Notiz"),
                  ("private_notiz", "private_notes", "private Notiz"))


def rechnungsentwurf_kopf_setzen(aufrufer: str, rechnungsnr: str, datum: str = "", faellig: str = "",
                                 bestellnummer: str | None = None, oeffentliche_notiz: str | None = None,
                                 private_notiz: str | None = None) -> str:
    """Ändert Kopf-Felder eines Rechnungsentwurfs. Texte mit None bleiben unverändert, ein leerer
    String leert das Feld. Mindestens ein Feld ist nötig."""
    werte = {"datum": datum or None, "faellig": faellig or None, "bestellnummer": bestellnummer,
             "oeffentliche_notiz": oeffentliche_notiz, "private_notiz": private_notiz}
    if all(w is None for w in werte.values()):
        raise ToolFehler("Bitte mindestens eines der Felder datum, faellig, bestellnummer, oeffentliche_notiz "
                         "oder private_notiz angeben.")
    datum_ = _datum(datum, "datum") if datum else None
    faellig_ = _datum(faellig, "faellig") if faellig else None
    i = _rechnung_frisch(rechnungsnr)
    _rechnungsentwurf_pruefen(i)
    if datum_ or faellig_:
        _faellig_pruefen(datum_ or _datum_oder_none(i.get("date")), faellig_ or _datum_oder_none(i.get("due_date")))
    if datum_:
        werte["datum"] = datum_.isoformat()
    if faellig_:
        werte["faellig"] = faellig_.isoformat()
    felder = {feld_: werte[name] for name, feld_, _l in _RECHNUNG_KOPF if werte[name] is not None}
    geaendert = [label for name, _f, label in _RECHNUNG_KOPF if werte[name] is not None]
    nn.update_invoice(i["id"], felder)
    log.info("IN-MCP [%s] rechnungsentwurf_kopf_setzen %s (%s)", aufrufer, i["number"], ", ".join(felder))
    return f"Rechnung {i['number']}: {', '.join(geaendert)} geändert. Status Entwurf, nicht versendet."


def angebot_in_rechnung_umwandeln(aufrufer: str, angebotsnr: str) -> str:
    """Wandelt ein Angebot in einen Rechnungsentwurf um (IN übernimmt Positionen, Projekt, Bestellnummer,
    Zusatzfelder). Gesperrt nur, wenn schon umgewandelt oder abgelaufen - wie in Invoice Ninja."""
    q = _quote(angebotsnr)
    if q.get("invoice_id"):
        nr = _rechnungsnr_fuer(q["invoice_id"]) or q["invoice_id"]
        raise ToolFehler(f"Angebot {q['number']} ist bereits in Rechnung {nr} umgewandelt.")
    if str(q.get("status_id")) == "-1":
        raise ToolFehler(f"Angebot {q['number']} ist abgelaufen – zuerst Gültigkeit verlängern.")
    nn.quote_bulk("convert_to_invoice", [q["id"]])
    invoice_id = (_quote_oder_none(q["number"]) or {}).get("invoice_id")
    if not invoice_id:
        log.warning("IN-MCP [%s] angebot_in_rechnung_umwandeln %s: keine Rechnung am Angebot", aufrufer, q["number"])
        raise ToolFehler("Umwandlung von Invoice Ninja nicht bestätigt (Angebot hat keine Rechnung). Bitte mit "
                         "angebot_lesen bzw. rechnungen_suchen prüfen.")
    try:
        rechnung = nn.get_invoice(invoice_id) or {}
    except Exception:
        log.warning("IN-MCP: Rechnung %s nach Umwandlung nicht lesbar", invoice_id, exc_info=True)
        rechnung = {}
    nr = rechnung.get("number", "")
    log.info("IN-MCP [%s] angebot_in_rechnung_umwandeln %s → %s", aufrufer, q["number"], nr or invoice_id)
    if not nr:
        return (f"Angebot {q['number']} in einen Rechnungsentwurf umgewandelt (IN-ID {invoice_id}); die "
                f"Rechnungsnummer ließ sich nicht lesen, bitte mit rechnungen_suchen prüfen. {RECHNUNGSNR_HINWEIS}")
    netto, brutto = _summen_aus(rechnung)
    return (f"Angebot {q['number']} in Rechnungsentwurf {nr} umgewandelt: {netto:.2f} € netto, {brutto:.2f} € "
            f"brutto. Status Entwurf, nicht versendet. {RECHNUNGSNR_HINWEIS}")


def rechnung_als_versendet_markieren(aufrufer: str, rechnungsnr: str) -> str:
    """Setzt einen Rechnungsentwurf auf versendet, ohne E-Mail (Versand auf anderem Weg)."""
    i = _rechnung_frisch(rechnungsnr)
    _rechnungsentwurf_pruefen(i)
    nn.invoice_bulk("mark_sent", [i["id"]])
    danach = nn.get_invoice(i["id"]) or {}
    log.info("IN-MCP [%s] rechnung_als_versendet_markieren %s", aufrufer, i["number"])
    if str(danach.get("status_id") or "") in ("", "1"):   # nicht (mehr) lesbar oder noch Entwurf
        raise ToolFehler(f"Markieren als versendet von Invoice Ninja nicht bestätigt (Status jetzt: "
                         f"{_invoice_status(danach)}) – bitte in Invoice Ninja prüfen.")
    return (f"Rechnung {i['number']} als versendet markiert (ohne E-Mail). Sie ist damit im MCP gesperrt, "
            "Korrektur nur per Storno.")


def rechnung_zahlung_erfassen(aufrufer: str, rechnungsnr: str, betrag: float | None = None, datum: str = "",
                              referenz: str = "", heute: date | None = None) -> str:
    """Erfasst eine Zahlung zu einer versendeten oder teilbezahlten Rechnung. Ohne betrag der offene
    Restbetrag, ohne datum heute."""
    i = _rechnung_frisch(rechnungsnr)
    status = str(i.get("status_id"))
    if status not in ("2", "3"):
        raise ToolFehler(f"Rechnung {i['number']} ist {_invoice_status(i)}. Zahlungen lassen sich nur zu "
                         "versendeten oder teilbezahlten Rechnungen erfassen.")
    offen = round(float(i.get("balance") or 0), 2)
    if offen <= 0:
        raise ToolFehler(f"Rechnung {i['number']} hat keinen offenen Betrag mehr.")
    if betrag is None:
        wert = offen
    else:
        try:
            wert = float(betrag)
        except (TypeError, ValueError):
            raise ToolFehler("betrag muss eine Zahl sein.")
        if not math.isfinite(wert):
            raise ToolFehler("betrag muss eine Zahl sein.")
        if abs(wert * 100 - round(wert * 100)) > 1e-6:
            raise ToolFehler("betrag darf höchstens zwei Nachkommastellen haben.")
        wert = round(wert, 2)
    if wert <= 0:
        raise ToolFehler("betrag muss größer als 0 sein.")
    if wert > offen:
        raise ToolFehler(f"betrag darf höchstens {offen:.2f} € sein (offener Betrag von {i['number']}).")
    tag = _datum(datum, "datum") if datum else (heute or date.today())
    payload = {"client_id": i["client_id"], "amount": wert, "date": tag.isoformat()}
    if referenz.strip():
        payload["transaction_reference"] = referenz.strip()
    payload["invoices"] = [{"invoice_id": i["id"], "amount": wert}]
    nn.create_payment(payload)
    log.info("IN-MCP [%s] rechnung_zahlung_erfassen %s %.2f", aufrufer, i["number"], wert)
    return (f"Zahlung über {wert:.2f} € zu Rechnung {i['number']} erfasst ({tag:%d.%m.%Y}). "
            f"Restbetrag {offen - wert:.2f} €.")


def rechnung_versenden(aufrufer: str, rechnungsnr: str) -> str:
    """Übergibt eine Rechnung an Invoice Ninja zum E-Mail-Versand an ihre Empfänger (IN wählt die Vorlage)."""
    i = _rechnung_frisch(rechnungsnr)
    if str(i.get("status_id")) in ("5", "6"):
        raise ToolFehler(f"Rechnung {i['number']} ist {_invoice_status(i)} und wird nicht versendet.")
    if i.get("archived_at"):
        raise ToolFehler(f"Rechnung {i['number']} ist archiviert – vor dem Versand in Invoice Ninja wiederherstellen.")
    kontakte = {k.get("id"): (k.get("email") or "").strip()
                for k in (nn.get_client(i["client_id"]) or {}).get("contacts") or []}
    emails = [kontakte.get(inv.get("client_contact_id"), "") for inv in i.get("invitations") or []]
    emails = [e for e in emails if e]
    if not emails:
        raise ToolFehler(f"Rechnung {i['number']} hat keine Empfänger mit E-Mail-Adresse. Empfänger in "
                         "Invoice Ninja an der Rechnung eintragen.")
    nn.invoice_bulk("email", [i["id"]])
    log.info("IN-MCP [%s] rechnung_versenden %s (%d Empfänger)", aufrufer, i["number"], len(emails))
    # IN verschickt über eine Warteschlange: die Antwort heißt "angenommen", nicht "zugestellt"
    return (f"Rechnung {i['number']} an Invoice Ninja zum Versand übergeben an {len(emails)} Empfänger "
            f"({', '.join(emails)}). Zustellung im Verlauf der Rechnung in Invoice Ninja prüfen.")


def rechnung_stornieren(aufrufer: str, rechnungsnr: str) -> str:
    """Storniert eine versendete oder teilbezahlte Rechnung (Invoice Ninja storniert keine Entwürfe und
    keine bezahlten Rechnungen)."""
    i = _rechnung_frisch(rechnungsnr)
    if str(i.get("status_id")) not in ("2", "3"):
        raise ToolFehler(f"Rechnung {i['number']} ist {_invoice_status(i)}. Stornieren lassen sich nur "
                         "versendete oder teilbezahlte Rechnungen.")
    nn.invoice_bulk("cancel", [i["id"]])
    danach = nn.get_invoice(i["id"]) or {}
    log.info("IN-MCP [%s] rechnung_stornieren %s", aufrufer, i["number"])
    if str(danach.get("status_id")) != "5":
        raise ToolFehler(f"Storno von Invoice Ninja nicht bestätigt (Status jetzt: {_invoice_status(danach)}) – "
                         "bitte in Invoice Ninja prüfen.")
    zahlungen = " Bereits erfasste Zahlungen bleiben bestehen." if str(i.get("status_id")) == "3" else ""
    return (f"Rechnung {i['number']} storniert. Status storniert in Invoice Ninja; es wird keine "
            f"Gutschrift/Stornorechnung erzeugt.{zahlungen}")
