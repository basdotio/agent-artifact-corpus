# German (de)

Language rules for German. Use them together with the universal rules in
[../rules.md](../rules.md). The format of this file is in
[_template.md](_template.md).

| Field | Value |
| --- | --- |
| Code | `de` |
| Script | Latin |
| Status | draft: waits for a native-speaker review |
| Reviewers | — |

## Instruction form

Use the formal imperative with «Sie»: «Klicken Sie auf **Speichern**.» Some
projects use the infinitive («Auf **Speichern** klicken.») or the informal
«du». Use the form of the style guide of the project. Do not mix forms in
one document.

## Signal words

| English | German |
| --- | --- |
| WARNING | WARNUNG |
| CAUTION | VORSICHT |
| NOTE | HINWEIS |

## Rules

| ID | Rule | L1 | L2 | L3 | Universal rule |
| --- | --- | --- | --- | --- | --- |
| DE1 | One instruction form in a document | must | must | must | P1 |
| DE2 | Verbs, not the nominal style | prefer | must | must | V4 |
| DE3 | No formal filler words | prefer | must | must | W2 |
| DE4 | Active voice: no «werden» passive in instructions | prefer | must | must | V1 |
| DE5 | Short compound nouns (max parts) | must (4) | must (3) | must (3) | N1 |
| DE6 | Verb and its particle close together; no long sentence brackets | — | prefer | must | S1 |
| DE7 | Clear obligation: «müssen» and «können», not «sollten» | prefer | must | must | V5 |

### DE1: One instruction form

- Not: «Klicken Sie auf **Speichern**. Danach das Fenster schließen.»
- Use: «Klicken Sie auf **Speichern**. Schließen Sie danach das Fenster.»

### DE2: Verbs, not the nominal style

- Not: «Die Durchführung der Installation erfolgt über das Menü.»
- Use: «Installieren Sie das Programm über das Menü.»

### DE3: No formal filler words

See the [word choices](#word-choices) below.

- Not: «Diesbezüglich ist seitens des Administrators eine Freigabe
  erforderlich.»
- Use: «Der Administrator muss das freigeben.»

### DE4: Active voice

- Not: «Die Datei wird vom System automatisch geöffnet.»
- Use: «Das System öffnet die Datei automatisch.»

### DE5: Short compound nouns

A long compound noun is the German form of a long noun cluster (N1). Count
the parts of the compound. The maximum is 4 parts at Level 1 and 3 parts at
Levels 2 and 3. Use a preposition or a genitive to make it shorter.

- Not: «Datenbankverbindungszeitüberschreitungseinstellung» (5 parts)
- Use: «die Einstellung für die Zeitüberschreitung der Datenbankverbindung»

### DE6: No long sentence brackets

In German, a separable verb and its particle can be far apart. A long
distance between them makes the sentence hard to read. Keep the verb parts
close together, or make two sentences.

- Not: «Schalten Sie das Gerät, bevor Sie das Kabel, das an der Rückseite
  angeschlossen ist, entfernen, aus.»
- Use: «Schalten Sie das Gerät aus. Entfernen Sie danach das Kabel an der
  Rückseite.»

### DE7: Clear obligation

- Not: «Sie sollten den Dienst neu starten.»
- Use: «Starten Sie den Dienst neu.»

## Word choices

The checker reads this table. Keep the five columns. Separate alternatives
in the **Avoid** column with a comma. Put a phrase that contains a comma in
double quotes. An entry that ends with `*` matches all words that start with
it.

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| erfolgt, erfolgen | (use the action verb) | 2 | yes | Rule DE2. |
| Durchführung, durchführen, durchgeführt | (use the action verb) | 2 | yes | Rule DE2. |
| diesbezüglich | dazu, dafür | 2 | yes | Rule DE3. |
| seitens | von | 2 | yes | Rule DE3. |
| hinsichtlich, bezüglich | zu, für | 2 | yes | Rule DE3. |
| mittels | mit | 2 | yes | Rule DE3. |
| im Rahmen | bei, in | 2 | yes | Rule DE3. |
| sollte, sollten, solltest | müssen, können | 2 | yes | Rule DE7. |
| usw., etc. | (give the full list) | 1 | yes | Rule W7. |
| ggf., gegebenenfalls | (give the condition) | 1 | yes | Rule W7. |
| entsprechend, entsprechende, entsprechenden | (name the item) | 2 | yes | Rule W7. |
| ganz einfach, einfach nur | (delete the words) | 1 | yes | Rule W2. Keep «einfach» when it means "simple". |
| Seien Sie vorsichtig | (give the command and the risk) | 1 | yes | Rule SF3. |
<!-- controlled-language: on -->
