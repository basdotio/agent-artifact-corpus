# Scanner limits

`find_markers.py` is a small, conservative tokenizer. It misses some markers rather
than inventing them.

## What counts as a marker

The comment text, after the comment opener and any `///`, `//!` or leading `*`
decoration, must **start** with `@claude` followed by whitespace or end of line.

| Written | Result |
|---|---|
| `# @claude rename this` | edit |
| `x = 1  # @claude rename this` | edit; only the comment is removed |
| `/* @claude split this\n   into two */` | edit; the instruction can span lines |
| `/** @claude add example` opening a doc comment with other lines | edit; only the opener line is the marker, the docs stay |
| ` * @claude handle overflow` inside a `/** */` | edit; only that line is removed |
| `# @claude? why 2` | question; the file is never edited |
| `# notes for @claude` | not a marker (the comment doesn't start with it) |
| `"# @claude"` in a string | not a marker |

An instruction spans several lines only when the block comment holds nothing but the
marker. A blank line, a `*`-prefixed line or an `@tag` line means the block also holds
docs, so only the marker's own line counts. Python and shell have no block comments,
so their instructions are one line long.

## Languages

| Syntax | Extensions |
|---|---|
| `//` `/* */` | c h cc cpp cxx hpp cs java kt kts scala swift rs dart groovy gradle proto, Jenkinsfile |
| `//` `/* */` plus `` ` `` template literals | js jsx mjs cjs ts tsx mts cts |
| `//` `/* */` plus `` ` `` raw strings | go |
| `#` plus triple-quoted strings | py pyi |
| `#` | sh bash zsh rb pl r ps1 yaml yml toml nix cmake mk, Makefile, Dockerfile, Containerfile |
| `#` `//` `/* */` | tf tfvars hcl |
| `//` `#` `/* */` | php |
| `--` `/* */` | sql |
| `--` | lua hs |
| `/* */` | css scss less |
| `<!-- -->` | html htm xml vue svelte |

`#` only opens a comment at the start of a line or after whitespace, so shell `$#` and
`${#x}` aren't read as comments.

## Known blind spots

- Heredocs (`<<EOF`) in shell and HCL are read as code, so a marker-like line inside
  one is reported.
- Rust raw strings `r#"…"#`, C++ raw strings `R"(…)"`, and Lua/Haskell block comments
  aren't understood.
- `${…}` expressions that contain backticks inside a JS template literal end the
  template early.
- Files over 1 MB and files that aren't valid UTF-8 are skipped.

## Excluding files from repo-wide scans

A file whose text contains `inline-comments: skip-in-repo-scan` is skipped when the
scanner runs with no paths or on a directory. It is still scanned when named
explicitly. Demo files use this so they don't get picked up by accident.
