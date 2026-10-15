"""instanz.yaml laden und prüfen.

Die Datei ordnet den Custom Fields von Invoice Ninja Rollen zu (z. B. angebot.bestellt:
custom_value3) und enthält die Angebotsregeln einer Instanz. Jede Rolle ist optional; fehlt sie,
entfällt das zugehörige Verhalten. Fehler brechen den Start mit einer Meldung ab, die den
Schlüssel nennt. Spec: DSS-PMS docs/superpowers/specs/2026-09-23-in-mcp-eigenes-repo-design.md
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

FELDER = ("custom_value1", "custom_value2", "custom_value3", "custom_value4")

ROLLEN = {
    "kunde": ("mandant_nr",),
    "kontakt": ("mobil", "position", "abteilung", "anrede"),
    "angebot": ("projektnummer", "bezeichnung", "bestellt", "abgeschlossen"),
    "rechnung": ("projektnummer", "projektbezeichnung"),
    "projekt": ("projektnummer", "name", "abgeschlossen", "notiz"),
}

# Präfix der IN-Beschriftungen in companies.custom_fields (client1, contact2, ...).
# Angebote und Rechnungen teilen sich in IN die Felder invoice1-4.
LABEL_PRAEFIX = {"kunde": "client", "kontakt": "contact", "angebot": "invoice", "rechnung": "invoice",
                 "projekt": "project"}

_OBERSTE = ("instanz", "rollen", "angebot", "produkt", "rechnungen")
_INSTANZ = ("name", "hinweise")
_ANGEBOT = ("verkaufsbedingungen", "standard_verkaufsbedingungen", "individuell_produkt",
            "gueltig_standard_tage", "gueltig_min_tage", "gueltig_max_tage", "angebotsnr_im_projektnamen",
            "verkaufsbedingungen_muster")
_PRODUKT = ("neue_steuerkategorie",)
_TAGE_DEFAULTS = (("gueltig_standard_tage", 30), ("gueltig_min_tage", 1), ("gueltig_max_tage", 365))
_RECHNUNGEN = ("schreiben", "status", "versenden", "stornieren")


class KonfigFehler(Exception):
    """instanz.yaml ist fehlerhaft; die Meldung nennt den Schlüssel."""


@dataclass(frozen=True)
class Konfig:
    name: str = "Invoice Ninja"
    hinweise: str = ""
    rollen: dict = field(default_factory=dict)
    verkaufsbedingungen: tuple = ()
    standard_verkaufsbedingungen: str = ""
    individuell_produkt: str = ""
    gueltig_standard_tage: int = 30
    gueltig_min_tage: int = 1
    gueltig_max_tage: int = 365
    angebotsnr_im_projektnamen: str = ""
    neue_steuerkategorie: str = "2"
    verkaufsbedingungen_muster: str = ""
    rechnungen: dict = field(default_factory=lambda: {k: False for k in _RECHNUNGEN})

    def feld(self, objekt: str, rolle: str) -> str | None:
        """IN-Feld (custom_valueN) einer Rolle oder None, wenn die Rolle nicht zugeordnet ist."""
        return self.rollen.get(objekt, {}).get(rolle)

    def freie_felder(self, objekt: str) -> tuple:
        """Custom Fields eines Objekts ohne Rolle - sie erscheinen als zusatzfelder."""
        belegt = set(self.rollen.get(objekt, {}).values())
        return tuple(f for f in FELDER if f not in belegt)

    def rechnungen_erlaubt(self, recht: str) -> bool:
        """Ob ein Rechnungs-Recht (schreiben/status/versenden/stornieren) für diese Instanz freigeschaltet ist."""
        return self.rechnungen.get(recht, False)


def _abschnitt(name: str, wert, erlaubt) -> dict:
    if wert is None:
        return {}
    if not isinstance(wert, dict):
        raise KonfigFehler(f"{name}: muss ein Abschnitt mit Schlüsseln sein.")
    fremd = sorted(set(wert) - set(erlaubt))
    if fremd:
        raise KonfigFehler(f"{name}: unbekannter Schlüssel {', '.join(fremd)}. "
                           f"Erlaubt: {', '.join(sorted(erlaubt))}.")
    return wert


def _rollen(roh: dict) -> dict:
    rollen = {}
    for objekt, zuordnung in roh.items():
        zuordnung = _abschnitt(f"rollen.{objekt}", zuordnung, ROLLEN[objekt])
        vergeben = {}
        for rolle, feld_ in zuordnung.items():
            if feld_ not in FELDER:
                raise KonfigFehler(f"rollen.{objekt}.{rolle}: '{feld_}' ist kein Feld, "
                                   f"erlaubt sind {', '.join(FELDER)}.")
            if feld_ in vergeben:
                raise KonfigFehler(f"rollen.{objekt}: {feld_} ist doppelt vergeben "
                                   f"({vergeben[feld_]} und {rolle}).")
            vergeben[feld_] = rolle
        if zuordnung:
            rollen[objekt] = dict(zuordnung)
    return rollen


def aus_dict(daten: dict | None) -> Konfig:
    daten = _abschnitt("instanz.yaml", daten, _OBERSTE)
    instanz = _abschnitt("instanz", daten.get("instanz"), _INSTANZ)
    rollen = _rollen(_abschnitt("rollen", daten.get("rollen"), ROLLEN))
    angebot = _abschnitt("angebot", daten.get("angebot"), _ANGEBOT)
    produkt = _abschnitt("produkt", daten.get("produkt"), _PRODUKT)

    vkb_roh = angebot.get("verkaufsbedingungen")
    if vkb_roh is not None and not isinstance(vkb_roh, list):
        raise KonfigFehler("angebot.verkaufsbedingungen: muss eine Liste sein, z. B. [VKBMA].")
    vkb = tuple(str(x) for x in vkb_roh or ())
    standard_vkb = str(angebot.get("standard_verkaufsbedingungen") or (vkb[0] if vkb else ""))
    if standard_vkb and standard_vkb not in vkb:
        raise KonfigFehler(f"angebot: standard_verkaufsbedingungen {standard_vkb} steht nicht in "
                           "verkaufsbedingungen.")

    tage = {}
    for schluessel, default in _TAGE_DEFAULTS:
        wert = angebot.get(schluessel, default)
        if not isinstance(wert, int) or isinstance(wert, bool) or wert < 0:
            raise KonfigFehler(f"angebot.{schluessel}: muss eine ganze Zahl ab 0 sein.")
        tage[schluessel] = wert
    if not tage["gueltig_min_tage"] <= tage["gueltig_standard_tage"] <= tage["gueltig_max_tage"]:
        raise KonfigFehler("angebot: gueltig_standard_tage muss zwischen gueltig_min_tage und "
                           "gueltig_max_tage liegen.")

    muster = str(angebot.get("angebotsnr_im_projektnamen") or "")
    if muster:
        try:
            re.compile(muster)
        except re.error as e:
            raise KonfigFehler(f"angebot.angebotsnr_im_projektnamen: ungültiger regulärer Ausdruck ({e}).")

    vkb_muster = str(angebot.get("verkaufsbedingungen_muster") or "")
    if vkb_muster:
        try:
            re.compile(vkb_muster)
        except re.error as e:
            raise KonfigFehler(f"angebot.verkaufsbedingungen_muster: ungültiger regulärer Ausdruck ({e}).")

    steuer = str(produkt.get("neue_steuerkategorie", "2"))
    if steuer not in ("1", "2", "3"):
        raise KonfigFehler("produkt.neue_steuerkategorie: erlaubt sind 1, 2, 3 "
                           "(Ware, Dienstleistung, Digital).")

    rechnungen_roh = _abschnitt("rechnungen", daten.get("rechnungen"), _RECHNUNGEN)
    rechnungen = {}
    for schluessel in _RECHNUNGEN:
        wert = rechnungen_roh.get(schluessel, False)
        if not isinstance(wert, bool):
            raise KonfigFehler(f"rechnungen.{schluessel}: muss true oder false sein.")
        rechnungen[schluessel] = wert

    return Konfig(
        name=str(instanz.get("name") or "Invoice Ninja"),
        hinweise=" ".join(str(instanz.get("hinweise") or "").split()),
        rollen=rollen,
        verkaufsbedingungen=vkb,
        standard_verkaufsbedingungen=standard_vkb,
        individuell_produkt=str(angebot.get("individuell_produkt") or ""),
        angebotsnr_im_projektnamen=muster,
        neue_steuerkategorie=steuer,
        verkaufsbedingungen_muster=vkb_muster,
        rechnungen=rechnungen,
        **tage,
    )


def laden(pfad: str) -> Konfig:
    try:
        with open(pfad, encoding="utf-8") as f:
            daten = yaml.safe_load(f)
    except FileNotFoundError:
        raise KonfigFehler(f"Konfigurationsdatei {pfad} fehlt.")
    except yaml.YAMLError as e:
        raise KonfigFehler(f"{pfad} ist kein gültiges YAML: {e}")
    return aus_dict(daten)
