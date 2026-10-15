# Russian (ru)

Language rules for Russian. Use them together with the universal rules in
[../rules.md](../rules.md). The format of this file is in
[_template.md](_template.md).

| Field | Value |
| --- | --- |
| Code | `ru` |
| Script | Cyrillic |
| Status | reviewed |
| Reviewers | [@amaklakov-droid](https://github.com/amaklakov-droid) |

## Instruction form

Use the polite imperative (second person plural): «Откройте», «Нажмите»,
«Введите». Write «вы» with a lowercase letter, unless the style guide of the
project requires «Вы».

Some projects use the infinitive in instructions («Открыть», «Нажать»), for
example, documents to a Russian state standard (GOST). In these projects,
keep the infinitive. Do not mix the two forms in one document.

## Signal words

| English | Russian |
| --- | --- |
| WARNING | ВНИМАНИЕ |
| CAUTION | ОСТОРОЖНО |
| NOTE | ПРИМЕЧАНИЕ |

## Rules

| ID | Rule | L1 | L2 | L3 | Universal rule |
| --- | --- | --- | --- | --- | --- |
| RU1 | Polite imperative in instructions, one form in a document | must | must | must | P1 |
| RU2 | Verbs, not verbal nouns with a weak verb | prefer | must | must | V4 |
| RU3 | No bureaucratic words (канцелярит) | prefer | must | must | W2 |
| RU4 | Active voice: no «-ся» passive and no short passive participles | prefer | must | must | V1 |
| RU5 | Short genitive chains (max nouns) | must (4) | must (3) | must (3) | N1 |
| RU6 | No adverbial-participle clauses (деепричастные обороты) | — | prefer | must | S1, P2 |
| RU7 | No participial clauses (причастные обороты) | — | prefer | must | S1 |
| RU8 | Clear obligation: no «следует», «рекомендуется», «необходимо» in instructions | prefer | must | must | V5 |
| RU9 | One spelling of «вы» and of the letter «ё» in a document | must | must | must | W8 |

### RU1: Polite imperative in instructions

- Not: «Пользователю необходимо нажать кнопку **Сохранить**.»
- Use: «Нажмите **Сохранить**.»

### RU2: Verbs, not verbal nouns

A weak verb with a verbal noun («осуществить установку», «произвести
настройку», «выполнить проверку») is longer and less clear than the verb.

- Not: «Произведите настройку параметров подключения.»
- Use: «Настройте подключение.»

### RU3: No bureaucratic words

Bureaucratic words make the text long and formal. They do not add meaning.
See the [word choices](#word-choices) below.

- Not: «Данный раздел является основным в рамках настройки.»
- Use: «Это главный раздел настройки.»

### RU4: Active voice

Say who does the action. In instructions, use the imperative.

- Not: «Файл открывается системой автоматически.»
- Use: «Система открывает файл автоматически.»
- Not: «Резервная копия должна быть создана заранее.»
- Use: «Заранее создайте резервную копию.»

### RU5: Short genitive chains

A chain of nouns in the genitive case is the Russian form of a long noun
cluster (N1). The maximum is 4 nouns at Level 1 and 3 nouns at Levels 2 and
3.

- Not: «настройка параметров подключения сервера базы данных» (5 nouns)
- Use: «настройте подключение к базе данных» (verb and 2 nouns)

### RU6: No adverbial-participle clauses

An adverbial-participle clause («нажав», «выбрав», «перейдя») puts two
actions in one sentence. It is similar to the English "-ing" form. Make two
instructions.

- Not: «Выбрав вкладку **Безопасность**, нажмите **Подключить 2FA**.»
- Use:
  1. Выберите вкладку **Безопасность**.
  2. Нажмите **Подключить 2FA**.

### RU7: No participial clauses

A participial clause («отображаемый на экране», «полученный в письме») makes
a long noun phrase. Make a separate sentence or a short relative clause.

- Not: «Введите код, полученный в письме, отправленном на ваш адрес.»
- Use: «Мы отправим письмо с кодом на ваш адрес. Введите этот код.»

### RU8: Clear obligation

«Следует», «рекомендуется», and «необходимо» do not show clearly if the
action is necessary. In instructions, use the imperative. In descriptions,
use «нужно» for a requirement and «можно» for a possibility.

- Not: «Следует перезапустить сервис.»
- Use: «Перезапустите сервис.»

### RU9: Consistent spelling

Write «вы» in one form in a document. Use the letter «ё» everywhere or
nowhere. Keep the spelling of UI labels exactly as the product shows them.

## Word choices

The checker reads this table. Keep the five columns. Separate alternatives
in the **Avoid** column with a comma. Put a phrase that contains a comma in
double quotes. An entry that ends with `*` matches all words that start with
it.

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| осуществ* | (use the action verb) | 2 | yes | Rule RU2. «Осуществите вход» → «Войдите». |
| произвести, произведите, производится, производить, производим | (use the action verb) | 2 | yes | Rule RU2. «Произведите настройку» → «Настройте». |
| выполнить настройку, выполните настройку, выполнить проверку, выполните проверку, выполнить установку, выполните установку | настройте, проверьте, установите | 2 | yes | Rule RU2. |
| является, являются, являться | (rewrite with a verb or a dash) | 2 | yes | Rule RU3. «X является Y» → «X — это Y». |
| данный, данная, данное, данного, данной, данном, данному | этот, эта, это | 2 | yes | Rule RU3. The checker does not flag «данные», because it usually means "data". |
| в целях | чтобы, для | 1 | yes | Rule RU3. |
| в рамках | в, при, для | 2 | yes | Rule RU3. |
| "в связи с тем, что", в связи с тем что | потому что | 1 | yes | Rule RU3. |
| в связи с чем | поэтому | 1 | yes | Rule RU3. |
| в случае если, "в случае, если" | если | 1 | yes | Rule RU3. |
| имеет место, имеют место | происходит, есть | 2 | yes | Rule RU3. |
| посредством | с помощью, через | 2 | yes | Rule RU3. |
| следует | (use the imperative) | 2 | yes | Only when «следует» means "must". It can also mean "follows". Rule RU8. |
| рекомендуется | (use the imperative) | 2 | yes | Rule RU8. |
| необходимо | (use the imperative), нужно | 2 | yes | Rule RU8. |
| и т. п., и т.п., и т. д., и т.д., и др. | (give the full list) | 1 | yes | Rule W7. |
| при необходимости | (give the condition) | 1 | yes | Rule W7. |
| соответствующий, соответствующее, соответствующую, соответствующем | (name the item) | 2 | yes | Rule W7. |
| надлежащим образом, должным образом | (give the criterion) | 1 | yes | Rule W7. |
| просто, всего лишь | (delete the word) | 1 | yes | Rule W2. |
| будьте осторожны, будьте внимательны | (give the command and the risk) | 1 | yes | Rule SF3. |
| кликните, кликнуть | нажмите | 2 | yes | Rule W3. |
<!-- controlled-language: on -->
