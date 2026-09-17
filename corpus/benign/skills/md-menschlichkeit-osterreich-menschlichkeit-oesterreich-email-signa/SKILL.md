---
name: email-signatur
description: Erstellt brandkonforme HTML-E-Mail-Signaturen für Menschlichkeit Österreich. Nutze diesen Skill wenn jemand eine E-Mail-Signatur braucht oder eine bestehende angepasst werden soll.
---

# E-Mail-Signatur – Menschlichkeit Österreich

Erstelle E-Mail-Signaturen nach den Brand Guidelines.

## Technische Vorgaben

- Max. Breite: 480px
- Logo: Max. 200×80px, als verlinktes Bild, unter 40 KB
- Schrift: System-Fonts (Calibri, Arial, Helvetica) – 10-12pt
- Format: HTML-Tabelle (kein CSS-Grid, kein Flexbox)

## Inhalt (Reihenfolge)

1. **Logo** (horizontal): `logo-horizontal.png`, verlinkt auf Website
2. **Trennlinie**: 3px solid #D4611E (Logo-Orange)
3. **Name**: 15px, Bold, Farbe #2B231D (Neutral 900)
4. **Funktion**: 12px, Farbe #7A6E62 (Neutral 500)
5. **Organisation**: "Verein Menschlichkeit Österreich" in Bold, Farbe #1B4965 (Demokratie-Blau)
6. **Subline**: "für Demokratie & Menschenrechte" in Neutral 500
7. **Kontakt**: Telefon, E-Mail (Link in #B54A0F), Website (Link in #B54A0F)
8. **Claim**: "Gemeinsam gestalten – Ein Österreich, das niemanden zurücklässt." in #B8ADA0, 11px, italic
9. **Rechtliches**: ZVR 1182213083 · 3140 Pottenbrunn · Datenschutz-Link, 10px, #B8ADA0

## Farbzuordnung

| Element     | Farbe           | HEX     |
| ----------- | --------------- | ------- |
| Name        | Neutral 900     | #2B231D |
| Funktion    | Neutral 500     | #7A6E62 |
| Vereinsname | Demokratie-Blau | #1B4965 |
| Links       | Text-Orange     | #B54A0F |
| Claim       | Stein Hell      | #B8ADA0 |
| Fließtext   | Neutral 700     | #4A4039 |
| Trennlinie  | Logo-Orange     | #D4611E |

## Template

Wenn $ARGUMENTS einen Namen und eine Funktion enthält (z.B. "Maria Huber, Vorstandsmitglied"),
ersetze die Platzhalter entsprechend. Sonst generiere die Vorlage mit [Vorname Nachname] etc.

Gib den vollständigen HTML-Code aus, der direkt in ein E-Mail-Programm kopiert werden kann.
Füge oben einen Kommentar mit Anleitung ein.
