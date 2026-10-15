# Spanish (es)

Language rules for Spanish. Use them together with the universal rules in
[../rules.md](../rules.md). The format of this file is in
[_template.md](_template.md).

| Field | Value |
| --- | --- |
| Code | `es` |
| Script | Latin |
| Status | draft: waits for a native-speaker review |
| Reviewers | — |

## Instruction form

Use the imperative. Use «usted» («Haga clic en **Guardar**.») or «tú»
(«Haz clic en **Guardar**.») as the style guide of the project requires.
Some projects use the infinitive («Hacer clic en **Guardar**.»). Do not mix
forms in one document.

## Signal words

| English | Spanish |
| --- | --- |
| WARNING | ADVERTENCIA |
| CAUTION | PRECAUCIÓN |
| NOTE | NOTA |

## Rules

| ID | Rule | L1 | L2 | L3 | Universal rule |
| --- | --- | --- | --- | --- | --- |
| ES1 | One instruction form and one form of "you" in a document | must | must | must | P1 |
| ES2 | Verbs, not nouns made from verbs | prefer | must | must | V4 |
| ES3 | No formal filler phrases | prefer | must | must | W2 |
| ES4 | Active voice: no «ser» passive and no passive «se» in instructions | prefer | must | must | V1 |
| ES5 | Short chains of «de» (max nouns) | must (4) | must (3) | must (3) | N1 |
| ES6 | No gerund clauses («haciendo clic») for a second action | — | prefer | must | S1, P2 |
| ES7 | Clear obligation: no «se recomienda», «se debe», «debería» | prefer | must | must | V5 |

### ES2: Verbs, not nouns made from verbs

- Not: «Realice la instalación del módulo.»
- Use: «Instale el módulo.»

### ES4: Active voice

- Not: «El archivo es abierto por el sistema.» / «Se abre el archivo.»
- Use: «El sistema abre el archivo.» / «Abra el archivo.»

### ES6: No gerund clauses for a second action

- Not: «Haga clic en **Guardar**, cerrando la ventana.»
- Use: «Haga clic en **Guardar**. Después, cierre la ventana.»

### ES7: Clear obligation

- Not: «Se recomienda reiniciar el servicio.»
- Use: «Reinicie el servicio.»

## Word choices

The checker reads this table. Keep the five columns. Separate alternatives
in the **Avoid** column with a comma. Put a phrase that contains a comma in
double quotes. An entry that ends with `*` matches all words that start with
it.

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| realizar, realice, realiza, realizado | hacer, (use the action verb) | 2 | yes | Rule ES2. |
| llevar a cabo, lleve a cabo | hacer, (use the action verb) | 2 | yes | Rule ES2. |
| se recomienda | (use the imperative) | 2 | yes | Rule ES7. |
| se debe, se deben | (use the imperative) | 2 | yes | Rule ES7. |
| debería, deberían | debe, puede | 2 | yes | Rule ES7. |
| con el fin de, a fin de | para | 1 | yes | Rule ES3. |
| en lo que respecta a, en relación con | sobre, para | 2 | yes | Rule ES3. |
| por medio de, mediante | con | 2 | yes | Rule ES3. |
| "etc.", y así sucesivamente | (give the full list) | 1 | yes | Rule W7. |
| en caso necesario, si es necesario | (give the condition) | 1 | yes | Rule W7. |
| simplemente | (delete the word) | 1 | yes | Rule W2. |
| tenga cuidado, ten cuidado | (give the command and the risk) | 1 | yes | Rule SF3. |
<!-- controlled-language: on -->
