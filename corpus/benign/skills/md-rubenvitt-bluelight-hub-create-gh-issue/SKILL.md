---
name: create-gh-issue
description: GitHub-Issues mit `gh issue create` strukturiert anlegen, inklusive deutschem Markdown-Body, Emoji-Präfix im Titel und repo-nativen Labels aus `gh label list`. Verwenden, wenn Codex ein neues GitHub-Issue für Features oder User Stories, Bugs, Refactorings, technische Schulden, Research-Spikes, Dokumentationsaufgaben, Chores oder Epics entwerfen oder direkt erstellen soll.
---

# GitHub Issue anlegen

Das Issue Ende-zu-Ende anlegen, außer der Nutzer verlangt ausdrücklich nur einen Entwurf.

## Ablauf

1. Repository-Kontext ermitteln.
   - `gh repo view --json nameWithOwner` ausführen.
   - `gh label list --limit 200` ausführen.
   - Bei spürbarem Duplikat-Risiko zusätzlich `gh issue list --limit 200 --search "<keywords>"` ausführen.
2. Issue-Typ klassifizieren.
   - Den passendsten Typ wählen: Feature, Bug, Technical Debt oder Refactor, Research oder Spike, Dokumentation, Epic oder Chore beziehungsweise Ops.
   - Nicht alles gewaltsam als User Story formulieren. Die Struktur soll dem Arbeitstyp folgen.
3. Issue-Body auf Deutsch formulieren.
   - `references/issue-templates.md` laden.
   - Kurzes, gut scanbares Markdown mit klaren Abschnitten und flachen Listen bevorzugen.
   - Lücken mit Annahmen oder offenen Fragen markieren, statt bei kleineren Unklarheiten zu blockieren.
4. Titel bauen.
   - Mit einem passenden Emoji beginnen.
   - Konkret, ergebnisorientiert und eigenständig verständlich formulieren.
   - Füllwörter wie `Issue`, `Ticket`, `Problem mit` oder einen Punkt am Ende vermeiden.
5. Labels aus der Live-Label-Liste auswählen.
   - Nur Labels verwenden, die `gh label list` tatsächlich liefert.
   - `references/label-strategy.md` laden.
   - In der Regel 2 bis 5 Labels setzen.
6. Issue erstellen.
   - Den Markdown-Body in eine temporäre Datei schreiben, um Shell-Escaping-Probleme zu vermeiden.
   - `gh issue create` mit `--title`, `--body-file` und je einem `--label` pro Label ausführen.
   - Bei reinem Entwurfswunsch hier stoppen.
7. Ergebnis zurückmelden.
   - Bei Erstellung Nummer und URL nennen.
   - Typ, gewählte Labels und relevante Annahmen kurz aufführen.

## Qualitätsmaßstab

- Das Issue auf Deutsch schreiben, außer der Repository-Kontext verlangt klar etwas anderes.
- Den Titel mit genau einem passenden Emoji beginnen.
- Die Body-Struktur am Issue-Typ ausrichten statt eine Einheitsvorlage zu verwenden.
- Akzeptanzkriterien nur ergänzen, wenn das Issue tatsächlich umsetzbare Arbeit beschreibt.
- Keine Labels, Milestones oder Project-Felder erfinden.
- Die repo-native Taxonomie über generische GitHub-Gewohnheiten stellen.

## Typauswahl

- Feature oder User Story: Für neuen Nutzer- oder Operator-Nutzen verwenden.
- Bug: Für defektes oder fehlendes Verhalten mit klarer Lücke zwischen Ist und Erwartung verwenden.
- Technical Debt oder Refactor: Für Wartbarkeit, Architektur, Bereinigung oder Konsistenz ohne primären Endnutzer-Scope verwenden.
- Research oder Spike: Für unbekannte Punkte verwenden, die vor der Umsetzung geklärt werden müssen.
- Dokumentation: Für ADRs, technische Doku, Prozessdoku oder fehlende Dokumentation verwenden.
- Epic: Für übergreifende Planung über mehrere Child-Issues oder Workstreams verwenden.
- Chore oder Ops: Für Tooling, CI, Konfiguration, Deployment, Dependencies oder Housekeeping verwenden.

Wenn zwei Typen plausibel wirken, den Typ wählen, der die Struktur des Issue-Bodys am stärksten verändert.

## Kommandomuster

Eine temporäre Datei und explizite Labels verwenden:

```bash
tmp_body="$(mktemp /tmp/create-gh-issue.XXXXXX.md)"

cat > "$tmp_body" <<'EOF'
## Ziel
...
EOF

gh issue create \
  --title "✨ Beispieltitel" \
  --body-file "$tmp_body" \
  --label "enhancement" \
  --label "frontend"

rm -f "$tmp_body"
```

## Referenzen

- Body-Vorlagen: `references/issue-templates.md`
- Label-Strategie: `references/label-strategy.md`
