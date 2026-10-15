# Configuration

A project can control the skill with three things:

1. A project configuration file: `.controlled-language.yml`.
2. A setting in the front matter of a document.
3. Markers in the text that turn the rules off and on.

All three are optional. Without them, the skill uses Level 2 and finds the
project terms itself.

## How the skill selects the level

The skill uses the first level that it finds in this order:

1. **The request.** For example: "level 3", "strict", "light", "80% of the
   way to ASD-STE100", "/controlled-language 1".
2. **The document front matter.** `controlled-language: 3`.
3. **A path override** in `.controlled-language.yml` that matches the file.
4. **The default level** in `.controlled-language.yml`.
5. **Level 2.**

Words and percentages in a request have these levels:

| In the request                                   | Level |
| ------------------------------------------------ | ----- |
| "1", "light", "soft", "relaxed", up to 60%       | 1     |
| "2", "standard", "normal", "balanced", 61%–90%   | 2     |
| "3", "strict", "full", "100%", more than 90%     | 3     |

## Project configuration file

Put `.controlled-language.yml` in the root folder of the project. A complete
template is in [`../assets/controlled-language.example.yml`](../assets/controlled-language.example.yml).

```yaml
# .controlled-language.yml
level: 2              # 1 = light, 2 = standard, 3 = strict
spelling: us          # us or uk. Level 3 always uses us.

# Files that the rules apply to. Other files are out of scope.
include:
  - "README.md"
  - "docs/**/*.md"
exclude:
  - "CHANGELOG.md"
  - "docs/legal/**"

# Different levels for some paths. The first match applies.
overrides:
  - path: "docs/safety/**"
    level: 3
  - path: "blog/**"
    level: 1

glossary:
  # Names of things in your domain. They count as one word.
  technical_nouns:
    - API key
    - smart contract
    - wallet address
  # Actions of your domain that have no simple general word.
  technical_verbs:
    - deploy
    - sign
    - mint
  # One concept, one term. The skill replaces the "not" forms.
  preferred_terms:
    - use: sign in
      not: [log in, login, log on]
    - use: API key
      not: [API token, access key]

# Extra words that the project does not want.
avoid_words:
  - word: leverage
    use: use
  - word: seamless
    use: (delete the word)

# Strings that the skill never changes.
keep_verbatim:
  - "Smarty Pay"
  - "Terms of Service"

# The language of the documents: auto (find it in each file) or a code
# such as en, ru, de.
language: auto

# Text that is not in English: apply (the universal rules and the rules of
# the language file) or off (do not change it).
non_english: apply
```

### Fields

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `level` | 1, 2, or 3 | 2 | The default level for the project. |
| `spelling` | `us` or `uk` | `us` | The spelling variant for Levels 1 and 2. Level 3 always uses `us`. |
| `include` | list of globs | all text files | The files in scope. |
| `exclude` | list of globs | none | The files out of scope. `exclude` is stronger than `include`. |
| `overrides` | list of `path` and `level` | none | Levels for some paths. The first match applies. |
| `glossary.technical_nouns` | list | none | Domain terms. Each term counts as one word (PU1). The skill does not simplify them. |
| `glossary.technical_verbs` | list | none | Domain actions. At Level 3, only these verbs and standard domain actions are acceptable as technical verbs (T3). |
| `glossary.preferred_terms` | list of `use` and `not` | none | One term per concept (T1). The skill replaces each `not` form with the `use` form. |
| `avoid_words` | list of `word` and `use` | none | Project words to avoid. The skill also uses [word-choices.md](word-choices.md). |
| `keep_verbatim` | list | none | Strings that the skill never changes. |
| `language` | `auto` or a language code | `auto` | The language of the documents. With `auto`, the skill and the checker find the language of each file. |
| `non_english` | `apply` or `off` | `apply` | What to do with text that is not in English. `apply` uses the universal rules and the language file. The old value `neutral` means `apply`. |

The format is a simple YAML subset: keys, lists, nested keys, and inline
lists (`[a, b]`). The checker script reads this subset without extra
packages.

## Front matter of a document

Set the level for one document in its YAML front matter:

```markdown
---
title: Install the agent
controlled-language: 3
---
```

The long form also works:

```markdown
---
controlled-language:
  level: 1
---
```

To give the language of a document, use `lang` or `language` in the front
matter: `lang: ru`.

## Markers in the text

Use HTML comments to turn the rules off for a part of a document. The skill
and the checker do not change or check the text between the markers. Use
the markers for legal text, quotations, and text that other teams own.

```markdown
<!-- controlled-language: off -->
This text is a quotation from the license agreement and stays as it is.
<!-- controlled-language: on -->
```

You can also change the level for a part of a document:

```markdown
<!-- controlled-language: level 3 -->
WARNING: Disconnect the power cable before you open the case.
<!-- controlled-language: level 2 -->
```

## Content that the skill never changes

These parts of a document are not prose. The skill keeps them exactly as
they are, at all levels:

- Code blocks and inline code.
- Commands, file names, paths, URLs, and e-mail addresses.
- Identifiers: names of APIs, functions, variables, fields, and environment
  variables.
- UI labels as they appear in the product (keep the exact capitalization).
- Product names, company names, and `keep_verbatim` strings.
- Quotations, legal text, and text between `off` markers.
- Front matter, link targets, anchors, and HTML attributes.
- Data values in tables.

The skill applies the rules to headings, list items, table text that is
prose, image alt text, and link text.
