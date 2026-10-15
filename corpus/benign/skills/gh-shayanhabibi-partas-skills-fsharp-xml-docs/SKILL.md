---
name: fsharp-xml-docs
description: Partas conventions for writing, auditing and fixing F# XML documentation comments (`///` with summary, param, remarks, code lang, include and cref tags) so IDE tooltips and AI agents get dense, contract-level docs. Use whenever you add or change a public F# declaration, document an F# module/type/function, review or clean up `///` comments, fix FS3390 warnings, or the user mentions tooltips, doc comments, XML docs or "documenting the API" in an F# repo, even if they do not say "XML". Not for Markdown pages, fsdocs/Nacara site content, or C# docs.
---

# F# XML documentation (Partas)

A `///` block is read by two audiences through one channel: a person hovering in Rider, and an
agent that reads the source or the generated `.xml` beside the assembly. Both want the
**contract**: what the member does, what it needs, what it returns, how it fails. Neither wants
the argument for why the code is correct. Write the fewest words that carry the contract in full
sentences.

The writing rules for the prose itself are roboz0r's seven constructions, in
`references/comment-hygiene.md`; this file covers the XML structure around the prose. Read the
references once, at the start, by task:

- Any task (write, audit, fix): **`references/comment-hygiene.md`**.
- Write: also `references/examples.md` (before/after pairs from Partas repos). A fix follows the
  recipe below; open examples.md only when unsure how far to cut agent-written prose.
- `references/tags.md` only for cref signatures, CDATA escaping, or a tag you have not used today.

Every file you need is named here (scripts are under `<skill dir>/scripts/`); do not list the
skill directory.

**First turn after reading this file.** Send one message holding all of these in parallel, since
none depends on another: Read the references for your task. Write or fix: Read each input file,
and `mkdir -p` + `cp` it to its output path when the result goes elsewhere (`cp` keeps BOM and
CRLF; do not check them with `file`). Fix: also run `audit.fsx --compiler` on the inputs. Audit:
run `audit.fsx --compiler` and Read the sources and any `<include>`d xmldoc file (see Auditing
for large scopes). The next turn should be edits or the report.

## Shape

Every doc starts with an explicit `<summary>`. A bare `///` line is summary-only, is not checked
by the compiler, and cannot grow a `<param>` later without being rewritten.

| Part | Holds | Budget |
| --- | --- | --- |
| `<summary>` | The contract: what it is (types) or what it computes (functions). | 1–2 prose lines |
| `<param>` / `<typeparam>` | A constraint the name and type do not state: units, range, format, ownership. | 1 line each |
| `<returns>` | Only when the return value has meaning beyond its type (empty on miss, sorted, lazily evaluated). | 1 line |
| `<exception cref>` | Each exception this member raises itself, with the condition. | 1 line each |
| `<remarks>` | Facts a caller needs that do not fit the summary: side effects, thread safety, cost, ordering, idempotency. | ≤ 3 prose lines |
| `<example>` + `<code lang="fsharp">` | Usage that shows input → output. | code is exempt from the line budget |

Wrap doc lines to the project's width as you write them (`max_line_length` in `.editorconfig`;
150 in Partas repos). Width is not a separate pass after the audit.

The 3-line ceiling counts **prose lines**, not tag lines. A block that still wants a fourth prose
line after cutting words is a type or a function waiting to be written; cut to three and tell
the user about the candidate.

**Who gets a doc:**
- Public and internal API: at least a `<summary>`, even when the name looks self-explanatory. The
  tooltip is the documentation for someone without the source.
- Private members: nothing unless a behaviour is not visible in the signature.
- Primary constructor: documenting an existing file is comment-only, even when the task says
  "add docs", so never split `type X(args) =`. Put the constructor's argument constraints in the
  type's doc and suggest the split in the report. Split only when you are writing the type
  itself; the constructor's doc then sits on its own line between `type X` and `(args) =`. A
  secondary `new (...)` gets its own block.
- Union cases and record fields: document a case or field when its meaning is not exhausted by
  its name and type. Show emitted output for cases that produce output.

## Parameters: all or none

With FS3390 on, one `<param>` makes the compiler demand all of them. Rider's inspection goes
further: a `<paramref>` also opts the member in, and every other parameter then warns "No
documentation for parameter". So:

- If no parameter carries a constraint beyond its name and type, write **no** `<param>` tags and
  refer to parameters by `<c>name</c>` in the summary, not `<paramref>`.
- If any parameter needs a note, document **every** parameter, each with real content. An empty
  `<param name="x"></param>` is a defect, never a placeholder.
- Tupled and curried parameters are both documented by name. `this`, `_` and unit are skipped.

## Tags

Use only the tags Microsoft documents for F# plus the Partas additions.

- Top level: `summary`, `remarks`, `param`, `typeparam`, `returns`, `exception`, `seealso`,
  `example`, `include`.
- Inline: `para`, `code`, `c`, `paramref`, `typeparamref`, `see`.
- **`<code>` always carries `lang`**, even though tooltips ignore it: `<code lang="fsharp">`,
  `<code lang="xml">`, `<code lang="json">`, `<code lang="shell">`. It tells an agent what it is
  reading and lets a doc generator highlight it.
- Paragraphs are `<para>`, never `<br/>`. HTML tags (`<br>`, `<a>`, `<b>`, `<ul>`) are not part
  of the set. This applies to hand-written docs; generated ones are left alone (see below).
- `cref` uses the full XML signature form: `cref="T:Partas.Build.Stage"`,
  `cref="M:Partas.Build.Stage.run(...)"`. F# does not resolve short C#-style crefs and does not
  check any cref, so write one only when the link helps, and keep the fact in the prose too.

## `<include>`

`<include file="..." path="..."/>` is part of the Partas set. Full expansion into the generated
documentation file arrives with the .NET 11 SDK; Partas adopts it now. **Before .NET 11, an
unexpanded `<include>` in the output `.xml` or a missing tooltip is expected — do not report it,
do not work around it, and do not inline the included text to compensate.**

Use it for text shared by two or more members (overload families, builder operations with the
same remark), or for a long example that would bury the declaration. Keep the `<summary>` inline
so a source reader always sees the contract at the declaration; include the shared `<remarks>`
or `<example>`, e.g. `/// <include file="../xmldoc/command.xml" path="/command/aliasRemark/*"/>`.

An `<include>` and its fragment are one change: write the fragment into the XML file in the same
edit that adds the tag, creating the file if needed. The file lives in an `xmldoc/` folder beside
the sources, one root element per module and one child per shared fragment; `file` is relative to
the `.fs` file. `path="/root/fragment/*"` splices the fragment's children beside `<summary>`, so
each fragment holds complete top-level elements and follows the same tag rules as inline docs:

```xml
<?xml version="1.0" encoding="utf-8"?>
<command>
  <aliasRemark>
    <remarks>Aliases accumulate: calling this twice adds both rather than replacing the first.</remarks>
  </aliasRemark>
</command>
```

When moving duplicated text into a fragment, delete it from every member that now includes it.
The audit's `include-unresolved` confirms each tag resolves.

## Density: what earns a line

Aim every sentence at a caller who will modify or call this code tomorrow. A line earns its
place by carrying one of:

- a precondition or accepted range (`Must be non-empty`, `Relative to the repository root`)
- a failure mode and its trigger (`Returns <c>Error</c> when the tag is missing`)
- a side effect (writes files, starts a process, mutates the argument, reads the environment)
- a guarantee the type cannot state (sorted, deduplicated, stable across runs, idempotent)
- cost when it surprises (walks the whole tree, performs I/O per call)
- the concrete shape of input → output, preferably as an `<example>`

Delete a sentence that restates the name or signature, narrates the implementation, defends a
design choice, or records history ("renamed from", "previously"). Reviewer-only notes use the
strippable `//FOR-REVIEW` form from `references/comment-hygiene.md`.

Avoid XML escapes in prose. `&lt;AssemblyName&gt;.xml` is noise to both audiences: rephrase
(`the assembly-named .xml file`) or put it in `<c>` with a placeholder that needs no brackets.
Inside `<code>`, generics and operators still need escaping or a `<![CDATA[ ... ]]>` block.

## Workflow

### Writing new docs

Write the doc **when you write the declaration**, not at the end of the change. Late docs come
from memory and drift from the code. After drafting, run the checks in `comment-hygiene.md`'s
"How to apply", then run the audit (below) on the file.

**Documenting an existing file.** When the result goes to another path, `cp` the input there in
the first turn (above), then add or replace each doc block with Edit, anchored on the declaration line. Send
independent Edits together in one turn, and take each `old_string` from text you have already
read rather than printing the region again. Never re-Write the whole file: that retypes every
code line and can drop the BOM or CRLF endings. Put the `--compiler --against <original>` run
in the same message, after the Edits (and after the report Write, if any), so it checks the
edited file; take another turn only if an Edit failed or the run shows findings or code changes.

### Auditing

Run the audit script on the files or directories in scope. It reports two groups:

- **Conventions** (parse only, milliseconds per file): `bare-doc`, `missing-summary`,
  `empty-param`, `empty-tag`, `code-lang`, `non-standard-tag`, and `long-line` (a `///` line
  wider than the nearest `.editorconfig` `max_line_length`, 150 if none; a lone unbreakable tag
  such as a long cref is exempt). Do not run separate width checks. `include-unresolved` flags
  an `<include>` whose file is missing or malformed or whose `path` selects nothing; fragments it
  selects get `code-lang` and `non-standard-tag` at their line in the XML file.
- **Compiler** (`--compiler`, adds a type-check per file): FS3390 malformed XML, unknown
  `<param>` names, and undocumented parameters in a partially documented member. It works on a
  file checked alone; unresolved project references do not suppress it.

The script cannot judge prose. The prose pass needs the code to check each doc's claims. When
the scope is small enough to read whole (roughly under 1,000 source lines), Read the source files
in the same turn as the `--compiler` run and skip `--docs`; Read's line numbers serve for citing
findings. For larger scopes, `--docs` prints every doc block with its line range and declaration
at roughly half the size of the source; read it against `comment-hygiene.md` and open the code
only where a doc makes a claim you need to check. Either way, report prose findings with file
and line alongside the script's findings. When the report goes to a file, the final reply gives
counts by severity and points to the file; it does not restate the findings.

With a SageFs session, load the audit in-process instead (sub-second re-runs): see
`references/sagefs.md`. Otherwise use the CLI (`<skill dir>` is the directory holding this file):

```shell
dotnet fsi <skill dir>/scripts/audit.fsx --compiler <file-or-dir>...
dotnet fsi <skill dir>/scripts/audit.fsx --check <file-or-dir>...   # exit 1 on any finding
dotnet fsi <skill dir>/scripts/audit.fsx --docs <file-or-dir>...    # list docs with their declarations
dotnet fsi <skill dir>/scripts/audit.fsx --compiler --against <original> <edited>
```

`--docs` replaces the audit; run it as a separate command. `--against` reports `code-removed`
and `code-added` for any non-`///` line that differs (BOM, line endings and blank lines
ignored), else prints `comment-only`. The script uses the running SDK's own
FSharp.Compiler.Service (.NET 10 or 11), so there is no restore.

### Generated docs are out of scope

Docs produced by a generator (Xantham bindings, anything under an `// <auto-generated>` header)
or transcribed from upstream JavaScript/TypeScript documentation (JSDoc, MDN text such as the
CSS property docs in Partas.Solid's `Style.fs`) follow their source, not these conventions.
Leave their `<br/>`, `<b>`, `<a>` and prose alone, and do not report them as findings, unless
the user explicitly asks for generated docs to be changed. A fix belongs in the generator.

The audit skips files it recognises as generated (the header, `.g.fs`, `fable_modules/`,
`Generated/`) when walking a directory; `--include-generated` (or
`XmlDocAudit.auditWith compiler true paths`) turns that off. A transcribed file without a header
is not recognised: when its findings are all non-standard tags inside upstream prose, treat it
as generated and say so in the report.

### Fixing

A fix pass is comment-only. Before you start, establish whose prose it is: defaults apply
fully to agent-written docs; on human-written docs, fix structure (tags, empty params, missing
`lang`) and leave prose style alone unless it is false.

1. Audit the scope and keep the report.
2. Re-read the code for every doc you change. The doc that travelled with the code is not
   evidence about the code; a claim you cannot trace to the code is deleted, not kept.
3. Fix structure first (tags, params, `lang`, `<br/>` → `<para>`), then prose.
4. Re-run the audit with `--compiler --against <original>`, in the same message as the last
   Edit and after it. That one run is the post-edit check: it confirms the change is
   comment-only and that no findings remain (width included); do not add hand diffs, `awk`/`wc`
   checks or re-reads. If it reports `code-removed`/`code-added`, undo that edit rather than
   reporting it. In a project, also confirm it still builds; with `<WarnOn>$(WarnOn);3390</WarnOn>`
   the build is also the FS3390 gate.
5. Report what changed (one line per change, grouped by kind), what remains and why (for example,
   human prose left alone), and any type candidates found while cutting; leave out advice beyond
   the task's scope. If the task asks for a report file, write it in the same turn as the step-4
   run; rewrite it only if that run shows findings or code changes. The final reply gives the
   step-4 result and anything not verified (such as no project build), and points to the file.

## Keeping the rules loaded

Most doc comments are written during other work, when this skill is not loaded. At the end, offer
(ask first) to copy `assets/xml-docs-rules.md` into the project's `.claude/rules/` or `CLAUDE.md`,
and to enable `<GenerateDocumentationFile>true</GenerateDocumentationFile>` and
`<WarnOn>$(WarnOn);3390</WarnOn>` so the compiler enforces part of this.
