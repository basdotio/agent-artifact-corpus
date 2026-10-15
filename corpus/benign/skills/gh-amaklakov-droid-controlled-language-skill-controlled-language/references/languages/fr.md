# French (fr)

Language rules for French. Use them together with the universal rules in
[../rules.md](../rules.md). The format of this file is in
[_template.md](_template.md).

| Field | Value |
| --- | --- |
| Code | `fr` |
| Script | Latin |
| Status | draft: waits for a native-speaker review |
| Reviewers | — |

## Instruction form

French technical documents use two forms: the imperative with «vous»
(«Cliquez sur **Enregistrer**.») and the infinitive («Cliquer sur
**Enregistrer**.»). Use the form of the style guide of the project. The
default is the imperative. Do not mix forms in one document.

## Signal words

| English | French |
| --- | --- |
| WARNING | AVERTISSEMENT |
| CAUTION | ATTENTION |
| NOTE | REMARQUE |

## Rules

| ID | Rule | L1 | L2 | L3 | Universal rule |
| --- | --- | --- | --- | --- | --- |
| FR1 | One instruction form in a document | must | must | must | P1 |
| FR2 | Verbs, not nouns made from verbs | prefer | must | must | V4 |
| FR3 | No formal filler phrases | prefer | must | must | W2 |
| FR4 | Active voice: no passive and no impersonal «il est» in instructions | prefer | must | must | V1 |
| FR5 | Short chains of «de» (max nouns) | must (4) | must (3) | must (3) | N1 |
| FR6 | No present-participle and gerund clauses («en cliquant») for a second action | — | prefer | must | S1, P2 |
| FR7 | Clear obligation: no «il convient de», «il est recommandé de» | prefer | must | must | V5 |

### FR2: Verbs, not nouns made from verbs

- Not: «Procédez à l'installation du module.»
- Use: «Installez le module.»

### FR4: Active voice

- Not: «Le fichier est ouvert automatiquement par le système.»
- Use: «Le système ouvre le fichier automatiquement.»

### FR5: Short chains of «de»

- Not: «la modification du paramètre de délai de connexion du serveur»
- Use: «modifiez le délai de connexion au serveur»

### FR6: No gerund clauses for a second action

- Not: «En cliquant sur **Valider**, vous enregistrez les modifications.»
- Use: «Cliquez sur **Valider**. Le système enregistre les modifications.»

### FR7: Clear obligation

- Not: «Il convient de redémarrer le service.»
- Use: «Redémarrez le service.»

## Word choices

The checker reads this table. Keep the five columns. Separate alternatives
in the **Avoid** column with a comma. Put a phrase that contains a comma in
double quotes. An entry that ends with `*` matches all words that start with
it.

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| procéder à, procédez à, procède à | (use the action verb) | 2 | yes | Rule FR2. |
| effectuer, effectuez, effectué | faire, (use the action verb) | 2 | yes | Rule FR2. |
| il convient de | (use the imperative) | 2 | yes | Rule FR7. |
| il est recommandé de | (use the imperative) | 2 | yes | Rule FR7. |
| il est nécessaire de | (use the imperative), il faut | 2 | yes | Rule FR7. |
| afin de | pour | 1 | yes | Rule FR3. |
| au niveau de | dans, sur | 2 | yes | Rule FR3. |
| en ce qui concerne | pour | 2 | yes | Rule FR3. |
| par le biais de | avec, par | 2 | yes | Rule FR3. |
| "etc.", et ainsi de suite | (give the full list) | 1 | yes | Rule W7. |
| le cas échéant, si nécessaire | (give the condition) | 1 | yes | Rule W7. |
| simplement | (delete the word) | 1 | yes | Rule W2. |
| soyez prudent, soyez prudents | (give the command and the risk) | 1 | yes | Rule SF3. |
<!-- controlled-language: on -->
