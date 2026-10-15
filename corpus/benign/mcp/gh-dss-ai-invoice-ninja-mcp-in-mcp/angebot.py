"""Reine Helfer für Angebote und Kontakte (ohne HTTP). Übernommen aus DSS-PMS services/angebot.py
(Commit ea2d020), nur die Teile, die der IN-MCP braucht.
"""
from __future__ import annotations

import re
from datetime import date, timedelta


ANREDEN = ("Herr", "Frau")


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def bereinige_bezeichnung(text: str) -> str:
    """Entfernt führende Aufzählungszeichen und Tabs ("•\\tRisiko…"), die aus
    kopierten Texten stammen und im Projektnamen landen würden."""
    text = re.sub(r"^[\s•\-\*·]+", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def gueltig_bis_standard(heute: date, tage: int) -> date:
    return heute + timedelta(days=tage)


def pruefe_kopf(bezeichnung: str, gueltig_bis: date | None, heute: date, *, bezeichnung_pflicht: bool,
                min_tage: int, max_tage: int) -> list[str]:
    fehler = []
    if bezeichnung_pflicht and not bereinige_bezeichnung(bezeichnung):
        fehler.append("Bitte einen Projektnamen / eine Projektbezeichnung eintragen.")
    if gueltig_bis is None:
        fehler.append("Bitte das Gültigkeitsdatum wählen.")
    elif gueltig_bis < heute + timedelta(days=min_tage):
        fehler.append(f"Das Angebot muss mindestens {min_tage} Tage gültig sein.")
    elif gueltig_bis > heute + timedelta(days=max_tage):
        fehler.append(f"Das Angebot darf höchstens {max_tage} Tage gültig sein.")
    return fehler


def katalog_position(produkt: dict, fest: bool = False) -> dict:
    return {
        "product_key": produkt["product_key"],
        "notes": produkt.get("notes", "") or "",
        "quantity": 1,
        "cost": float(produkt.get("price") or 0),
        "katalog_preis": float(produkt.get("price") or 0),
        "tax_name1": produkt.get("tax_name1", ""),
        "tax_rate1": produkt.get("tax_rate1", 0),
        "tax_id": produkt.get("tax_id", ""),
        "fest": fest,
    }


def pruefe_positionen(positionen: list[dict], vkb_keys: tuple, individuell: str) -> list[str]:
    """vkb_keys leer = keine Pflichtposition; individuell leer = keine Sonderprüfung."""
    fehler = []
    if not any(not p.get("fest") for p in positionen):
        fehler.append("Bitte mindestens eine Leistung aufnehmen.")
    if vkb_keys and not any(p.get("fest") and p["product_key"] in vkb_keys for p in positionen):
        fehler.append("Die Verkaufsbedingungen fehlen.")
    for p in positionen:
        if p.get("fest"):
            continue
        key = p["product_key"]
        if float(p.get("quantity") or 0) <= 0:
            fehler.append(f"Position {key}: Die Menge muss größer als 0 sein.")
        if individuell and key == individuell:
            if not (p.get("notes") or "").strip():
                fehler.append(f"Position {key}: Bitte die Leistung beschreiben.")
            if float(p.get("cost") or 0) <= 0:
                fehler.append(f"Position {key}: Bitte einen Betrag eintragen.")
        elif float(p.get("cost") or 0) == 0 and float(p.get("katalog_preis") or 0) != 0:
            fehler.append(f"Position {key}: Der Betrag steht auf 0 €, im Katalog kostet sie "
                          f"{p['katalog_preis']:.2f} €. Bitte prüfen.")
    return fehler


def line_items(positionen: list[dict]) -> list[dict]:
    """Nur die Felder, die IN kennt. MwSt. steht in IN je Position, nicht am Angebot."""
    return [{
        "product_key": p["product_key"],
        "notes": p.get("notes", "") or "",
        "quantity": float(p.get("quantity") or 0),
        "cost": float(p.get("cost") or 0),
        "tax_name1": p.get("tax_name1", ""),
        "tax_rate1": p.get("tax_rate1", 0),
        "tax_id": p.get("tax_id", ""),
        "type_id": "1",
    } for p in positionen]


def summen(positionen: list[dict]) -> tuple[float, float, float]:
    netto = mwst = 0.0
    for p in positionen:
        betrag = round(float(p.get("quantity") or 0) * float(p.get("cost") or 0), 2)
        netto += betrag
        mwst += round(betrag * float(p.get("tax_rate1") or 0) / 100, 2)
    return round(netto, 2), round(mwst, 2), round(netto + mwst, 2)


def pruefe_kontakt(k: dict, anrede_pflicht: bool) -> list[str]:
    fehler = []
    if anrede_pflicht and k.get("anrede") not in ANREDEN:
        fehler.append("Bitte die Anrede wählen.")
    if not (k.get("vorname") or "").strip():
        fehler.append("Bitte den Vornamen eintragen.")
    if not (k.get("nachname") or "").strip():
        fehler.append("Bitte den Nachnamen eintragen.")
    if not _EMAIL.match((k.get("email") or "").strip()):
        fehler.append("Bitte eine gültige E-Mail-Adresse eintragen.")
    return fehler


def neuer_in_kontakt(k: dict, anrede_feld: str | None) -> dict:
    """Formulardaten → IN-Kontakt. Die Anrede steht im Custom Field der Rolle kontakt.anrede."""
    kontakt = {
        "first_name": k["vorname"].strip(),
        "last_name": k["nachname"].strip(),
        "email": k["email"].strip(),
        "phone": (k.get("telefon") or "").strip(),
        "send_email": True,
    }
    if anrede_feld:
        kontakt[anrede_feld] = k["anrede"]
    return kontakt


def kontaktliste_fuer_update(bestehende: list[dict], neue: list[dict], anrede_feld: str | None) -> list[dict]:
    """Vollständige Liste für den Client-PUT: IN ersetzt die Kontaktliste komplett,
    also müssen alle bestehenden Kontakte mit ihrer id unverändert mit."""
    return [dict(k) for k in bestehende] + [neuer_in_kontakt(k, anrede_feld) for k in neue]


def kontakt_aus_in(c: dict, anrede_feld: str | None) -> dict:
    """IN-Kontakt → einheitliche Form. Ohne Rolle kontakt.anrede gibt es kein Feld "anrede"."""
    kontakt = {"id": c.get("id", "")}
    if anrede_feld:
        kontakt["anrede"] = (c.get(anrede_feld) or "").strip()
    kontakt.update(vorname=(c.get("first_name") or "").strip(), nachname=(c.get("last_name") or "").strip(),
                   email=(c.get("email") or "").strip())
    return kontakt


def quote_payload(client_id: str, contact_ids: list[str], positionen: list[dict],
                  bezeichnung: str, heute: date, gueltig_bis: date, bezeichnung_feld: str | None) -> dict:
    """Angebot ohne Status-/Projekt-Custom-Values, public_notes, terms, footer, design_id -
    Design und Standardtexte kommen aus IN, nichts kann geerbt werden."""
    payload = {
        "client_id": client_id,
        "date": heute.isoformat(),
        "due_date": gueltig_bis.isoformat(),
        "line_items": line_items(positionen),
        "invitations": [{"client_contact_id": cid} for cid in contact_ids],
    }
    if bezeichnung_feld:
        payload[bezeichnung_feld] = bereinige_bezeichnung(bezeichnung)
    return payload


def kontakt_ids_fuer(client: dict, emails: list[str]) -> list[str]:
    """IDs der Empfänger im frisch gespeicherten Kunden, über die E-Mail zugeordnet."""
    gesucht = {e.strip().lower() for e in emails}
    return [c["id"] for c in client.get("contacts", [])
            if (c.get("email") or "").strip().lower() in gesucht]
