---
name: comprehensive-planning-spec-assistant
description: Unterstützt dabei, aus vagen oder konkreten Vorhaben einen realistischen Projektplan mit Spezifikation, Task-Breakdown und passenden LLM-Prompts für Umsetzungsagenten zu entwickeln; verwenden, wenn Planung, Dokumentation und Prompt-Design für ein neues Vorhaben nötig sind.
---

## Wann verwenden

Verwenden, wenn:

- ein Nutzer ein Vorhaben oder Entwicklungsprojekt (z. B. Software, Produktfeature, Lernangebot, Content-Reihe, Prozessverbesserung) plant und dafür:
  - einen soliden, realistisch wirkenden Projektplan,
  - eine klar strukturierte Spezifikation,
  - einen brauchbaren Task-Breakdown
    benötigt.
- zusätzlich für die Umsetzung ein oder mehrere LLM-Agenten eingesetzt werden sollen und der Nutzer dafür **passende, gut designte Prompts** für diese Umsetzungsagenten braucht.
- der Nutzer seine eigene Planungs- und Spezifikationsqualität verbessern möchte (z. B. als Product Owner, Projektleiter:in, Lehrperson, Entwickler:in, Berater:in).
- unklar ist, wie man ein vages Ziel in klare Schritte, Artefakte und LLM-Aufgaben übersetzt.

Nicht verwenden, wenn:

- der Nutzer explizit **nur** eine schnelle Einzelantwort oder einen einmaligen Prompt ohne Planungsanteil möchte.
- lediglich triviale Mini-Aufgaben anstehen (z. B. eine einzelne E-Mail umformulieren) – hier reicht ein direkter Prompt ohne diesen Skill.

## Workflow / Anweisungen

### 1. Anfrage analysieren und Lücken identifizieren

1. Lies die Nutzeranfrage vollständig.
2. Extrahiere stillschweigend:
   - Hauptziel(e) des Vorhabens.
   - grobe Domäne (z. B. Softwareentwicklung, Bildung, Marketing, Forschung, Geschäftsprozess).
   - erwartete Deliverables (z. B. App, Dokumentation, Kurs, Kampagne, Report, Workflow).
   - relevante Stakeholder und Zielgruppen.
   - erkennbare harte Constraints (Zeit, Budget, vorhandene Tools/Stacks, Qualitätsanforderungen).
3. Stelle **maximal drei gezielte Rückfragen**, nur wenn nötig. Priorität:
   1. **Ziel & Erfolg** (Was gilt konkret als „fertig"? Wer soll welchen Nutzen haben?).
   2. **Constraints & Ressourcen** (Zeitfenster, Budget, Team/Skills, bestehende Systeme).
   3. **Zielgruppe & Kontext** (Wer nutzt das Ergebnis? In welchem Umfeld?).
4. Wenn der Nutzer zusätzliche Fragen ablehnt oder Informationen offenlässt:
   - arbeite mit explizit genannten **Annahmen** weiter,
   - markiere diese später im Machbarkeitscheck.

### 2. Klarifizierte Zusammenfassung & Plausibilitätscheck

1. Erzeuge eine kurze, präzise Zusammenfassung in **3–6 Stichpunkten**:
   - Problem / Ziel,
   - Zielgruppe / Stakeholder,
   - Kontext / Umgebung,
   - grober Scope (in/out),
   - erkennbare Constraints.
2. Führe einen knappen **Plausibilitätscheck** durch:
   - Welche Aspekte wirken fragwürdig (zu ambitioniert, zu vage, widersprüchlich)?
   - Wo fehlen kritische Informationen, die vor der Umsetzung noch geklärt werden müssen?
3. Wenn das Vorhaben offenkundig unrealistisch ist (z. B. „komplexe Plattform in zwei Tagen alleine fertigstellen"):
   - benenne die Unplausibilitäten klar,
   - schlage eine **abgespeckte oder stufenweise** Variante vor (Pilot, MVP, Experiment).

### 3. Erfolgskriterien & KPIs definieren

1. Formuliere **3–7 messbare Erfolgskriterien** (KPIs), die zum Ziel passen, z. B.:
   - Qualität (z. B. Fehlerraten, Nutzerzufriedenheit, Testabdeckung),
   - Zeit (z. B. Durchlaufzeit, Time-to-First-Value),
   - Nutzung / Adoption,
   - Lernziele (was Nutzer:innen hinterher konkret können).
2. Achte darauf, dass KPIs:
   - spezifisch, beobachtbar und in der Praxis überprüfbar sind,
   - realistisch zu messen sind (kein reines Wunschdenken).

### 4. Projektstruktur in Phasen entwerfen

1. Teile das Vorhaben in **3–7 klar benannte Phasen**, z. B.:
   - Discovery / Analyse,
   - Konzeption / Design,
   - Prototyping / Implementierung,
   - Testen / Validieren,
   - Rollout / Einführung,
   - Monitoring / Iteration.
2. Für jede Phase:
   - definiere das **Phasenziel**,
   - liste zentrale **Fragen/Entscheidungen**, die dort geklärt werden,
   - benenne die wichtigsten **Deliverables** der Phase.

### 5. Spezifikation ausarbeiten

Erstelle eine konsistente, textbasierte Spezifikation mit folgenden Unterabschnitten (falls sinnvoll):

1. **Zielbild & Kontext**
   - Kurze Beschreibung des angestrebten Ergebnisses und warum es existiert.
2. **Stakeholder & Zielgruppen**
   - Wer nutzt das Ergebnis? Wer entscheidet über Erfolg?
3. **Scope**
   - „Im Scope": was explizit adressiert wird.
   - „Außerhalb des Scopes": was bewusst nicht gemacht wird.
4. **Funktionale Anforderungen**
   - Was soll das System / Artefakt konkret leisten? (Use Cases, User Stories, Funktionen).
5. **Nicht-funktionale Anforderungen / Qualitätsziele**
   - Performance, Sicherheit, Usability, Barrierefreiheit, Wartbarkeit, Skalierbarkeit, etc.
6. **Randbedingungen & Constraints**
   - Technologie-Stack, regulatorische Vorgaben, Schnittstellen zu existierenden Systemen, organisatorische Zwänge.
7. **Risiken, Abhängigkeiten & Annahmen**
   - identifizierte Risiken,
   - externe Abhängigkeiten (Teams, Tools, Lieferanten),
   - explizite Annahmen, die noch validiert werden müssen.
8. **Offene Fragen**
   - Punkte, die vor Umsetzung oder während früher Phasen entschieden werden müssen.

### 6. Task-Breakdown erstellen

1. Erstelle einen **strukturierten Task-Breakdown**, vorzugsweise nach Phasen gruppiert.
2. Für jeden Task mindestens festhalten:
   - Task-ID oder -Label,
   - zugeordnete Phase,
   - Kurzbeschreibung (1–2 Sätze),
   - Input-Voraussetzungen,
   - erwarteter Output / Artefakt,
   - grobes „Done"-Kriterium,
   - grobe Aufwandseinschätzung (z. B. S/M/L oder Stundenbereich),
   - Empfehlung: „primär Mensch", „primär LLM", „Mensch+LLM".
3. Vermeide übermäßige Mikro-Tasks; richte dich grob nach:
   - 5–20 Haupttasks für kleinere Vorhaben,
   - mehrstufige Gliederung (Epics → Tasks → optionale Subtasks) für größere Projekte.

### 7. Prompt-Design für Umsetzungs-Agent(en)

Erzeuge eine **konkrete Prompt-Sammlung**, die der Nutzer direkt in LLM-Tools einsetzen kann.

1. Erstelle mindestens:
   - **einen globalen Kontext-Prompt** („Projektkontext & Leitplanken"),
   - **Phasen- oder Modul-Prompts**, passend zu wesentlichen Task-Gruppen,
   - optional **Review-/Reflexionsprompts** (Code-Review, Qualitätssicherung, Retrospektive).
2. Jeder Prompt besteht aus:
   - **Titel** (z. B. „Prompt A – Architektur-Vorschlag für Datenmodell"),
   - Hinweis „Wann verwenden",
   - einem **vollständigen Prompt-Text**, den der Nutzer 1:1 kopieren kann.
3. Struktur des Prompt-Texts:
   - Rolle des LLM (z. B. „Du bist ein erfahrener Software-Architekt…"),
   - komprimierter Kontext (Projektzusammenfassung, relevante Spezifikationsauszüge),
   - **konkrete Aufgabe**,
   - relevante Constraints (z. B. Technologien, Stil, Länge, Verbotenes),
   - gewünschte **Ausgabestruktur** (z. B. nummerierte Liste, Tabelle, Markdown-Abschnitte),
   - kurze **Qualitäts- oder Prüfhinweise** (z. B. „prüfe Annahmen", „liste Risiken").
4. Gib die Prompt-Texte in der Regel in **Markdown-Codeblöcken** aus, damit sie leicht kopierbar sind.

### 8. Unsicherheiten & Alternativen benennen

1. Füge nach Plan, Spezifikation und Task-Breakdown einen kurzen Abschnitt hinzu:
   - Welche Teile sind relativ sicher?
   - Wo gibt es hohe Unsicherheit oder starke Annahmen?
   - Welche Vorab-Schritte (Research, Nutzerinterviews, technische Spikes) würden Risiko stark reduzieren?
2. Wenn trotz aller Strukturierung das Gesamtvorhaben wenig plausibel erscheint:
   - schlage **vereinfachte Alternativen oder Iterationen** vor (z. B. MVP, Pilotprojekt, begrenzter Scope),
   - fokussiere auf maximalen Lern- und Kundenwert im ersten Schritt.

### 9. Umgang mit sehr kleinen Aufgaben

1. Wenn die Nutzeranfrage inhaltlich eher klein ist (z. B. „Formuliere diesen Absatz in klarer Sprache um"):
   - verkürze das Format:
     - 1–2 Stichpunkte zur Zusammenfassung,
     - Mini-Plan mit 2–4 Schritten,
     - 1–2 passende Prompts statt vollständigem Projektplan.
2. Halte dich dabei trotzdem an den Geist des Skills:
   - Klarheit,
   - Umsetzbarkeit,
   - bewusste Auswahl guter Prompts.

## Ausgabeformat

Antworten dieses Skills sollen in der **Sprache des Nutzers** formuliert werden (sofern nicht explizit anders verlangt) und konsistent strukturiert sein.

Verwende folgende Hauptabschnitte (Überschriften oder fett markiert):

1. **1) Klarifizierte Zusammenfassung**

   - 3–6 Stichpunkte zu Ziel, Kontext, Scope, Stakeholdern, Constraints.

2. **2) Machbarkeitscheck & Risiken**

   - Kurzer Text mit Plausibilitätsbewertung,
   - wichtigste Risiken, Annahmen, offene Fragen.

3. **3) Projektplan (Phasenübersicht)**

   - Liste der Phasen mit:
     - Phasenname,
     - Ziel,
     - wichtigsten Deliverables.

4. **4) Spezifikation**

   - Unterabschnitte wie:
     - Zielbild & Kontext
     - Stakeholder & Zielgruppen
     - Scope (in/out)
     - Funktionale Anforderungen
     - Nicht-funktionale Anforderungen
     - Randbedingungen & Constraints
     - Risiken, Abhängigkeiten & Annahmen
     - Offene Fragen

5. **5) Task-Breakdown**

   - Strukturierte Auflistung (z. B. Markdown-Tabelle) mit:
     - Task-ID,
     - Phase,
     - Kurzbeschreibung,
     - Input,
     - Output,
     - „Done"-Kriterium,
     - Aufwandskategorie,
     - Mensch/LLM.

6. **6) Prompt-Sammlung für den Umsetzungs-Agenten**

   - Für jeden Prompt:
     - Titel,
     - „Wann verwenden" in ein bis zwei Sätzen,
     - **Prompt-Text in einem Markdown-Codeblock**, z. B.:
       ```text
       Du bist ein ...
       Kontext: ...
       Aufgabe: ...
       Randbedingungen: ...
       Ausgabeformat: ...
       ```
   - Prompts sinnvoll gruppieren (Global, Phase X, Review, etc.).

7. **7) Nächste Schritte für den Menschen**
   - 3–5 konkrete nächste Schritte, wie der Nutzer mit Plan, Spezifikation und Prompts weiterarbeitet.

Wenn der Nutzer explizit nur einen einzelnen Prompt wünscht, kann Abschnitt 3–5 stark verkürzt werden; Abschnitt 6 bleibt Pflicht (mindestens ein gut gemachter Prompt).

## Beispiele

### Beispiel 1 – Software-Feature planen

**Nutzer:**  
„Ich möchte ein kleines Web-Tool bauen, mit dem unsere internen Teams Meeting-Notizen als strukturierte Aufgabenliste exportieren können. Es soll anfangs nur für unser Team funktionieren, später vielleicht für die ganze Firma."

**Assistent (auszugsweise):**

#### 1) Klarifizierte Zusammenfassung

- **Ziel:** Internes Web-Tool zum Umwandeln von Meeting-Notizen in Aufgabenlisten.
- **Zielgruppe:** Eigenes Team, später ggf. weitere Teams.
- **Scope v1:** Manuelle Eingabe von Text, Export als Markdown/CSV; keine Integration in externe Tools.
- …

#### 3) Projektplan (Phasenübersicht)

- **Phase 1 – Discovery & Anforderungen**
- **Phase 2 – Prototyp UX & Datenmodell**
- **Phase 3 – Implementierung & Tests**
- **Phase 4 – Pilot & Feedback**
- …

#### 6) Prompt-Sammlung für den Umsetzungs-Agenten (Auszug)

**Prompt A – Feature-Liste aus Anforderungen ableiten**

```text
Du bist ein erfahrener Produktentwickler ...
Kontext: ...
Aufgabe: Leite aus den folgenden Anforderungen eine priorisierte Feature-Liste für v1 ab ...
Ausgabeformat: nummerierte Liste mit Begründung je Feature.
```

---

### Beispiel 2 – Bildungsformat planen

**Nutzer:**  
„Ich will einen 4-wöchigen Online-Kurs ‚Einführung in Datenanalyse für Sozialwissenschaftler:innen' planen, inklusive Materialien und Übungsaufgaben. Später soll ein LLM helfen, Übungsaufgaben und Musterlösungen zu generieren."

**Assistent (auszugsweise):**

#### 1) Klarifizierte Zusammenfassung

- **Ziel:** 4-wöchiger Online-Kurs zur Datenanalyse für sozialwissenschaftliche Zielgruppe.
- **Zielgruppe:** Studierende ohne starke Mathe-Vorkenntnisse.
- **Deliverables:** Wochenstruktur, Lernziele, Inhalte, Aufgaben, Bewertungslogik.
- …

#### 5) Task-Breakdown

- **T1** – Zielgruppe & Lernziele schärfen
- **T2** – Wochenstruktur und Themenplan entwerfen
- **T3** – Beispiel-Datensätze auswählen
- …

#### 6) Prompt-Sammlung für den Umsetzungs-Agenten (Auszug)

**Prompt B – Übungsaufgaben zu einem Kursthema generieren**

```text
Du bist Hochschuldozent:in für Datenanalyse in den Sozialwissenschaften ...
Kontext: Dies ist Woche 2 des Kurses, Thema „Deskriptive Statistik" ...
Aufgabe: Erstelle 5 Übungsaufgaben mit Lösungen auf Einsteiger-Niveau ...
Ausgabeformat: Markdown mit Überschriften „Aufgabe" und „Lösung" je Item.
```

## Validierung & Packaging

Zur lokalen Validierung und Verpackung dieses Skills können z. B. folgende Kommandos verwendet werden:

- **Schneller Check des Skill-Ordners:**

  ```bash
  python quick_validate.py comprehensive-planning-spec-assistant
  ```

- **Erstellen eines ZIP-Pakets:**
  ```bash
  python package_skill.py comprehensive-planning-spec-assistant ./dist
  ```
