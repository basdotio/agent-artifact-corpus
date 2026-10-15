# Tag reference

The set is Microsoft's F# XML-doc tags
(<https://learn.microsoft.com/dotnet/fsharp/language-reference/xml-documentation>) plus the
Partas additions: `<example>`, `<include>`, and a mandatory `lang` on `<code>`. Anything else is
reported by the audit as `non-standard-tag`.

## Top-level tags

| Tag | Use |
| --- | --- |
| `<summary>text</summary>` | Required on every doc. One or two sentences. |
| `<remarks>text</remarks>` | Caller-relevant facts beyond the summary. Separate paragraphs with `<para>`. |
| `<param name="x">text</param>` | All parameters or none. Never empty. |
| `<typeparam name="'T">text</typeparam>` | Only for a constraint on `'T` the signature does not show. Names are not checked by the compiler. |
| `<returns>text</returns>` | Only when the value means more than its type. |
| `<exception cref="T:System.FormatException">when</exception>` | Exceptions this member raises, directly or by design through a callee, with the triggering condition. |
| `<seealso cref="..."/>` | A related member the reader will likely want next. |
| `<example>...</example>` | Partas addition. Prose plus `<code lang="fsharp">`. |
| `<include file="..." path="..."/>` | Partas addition. Shared fragments; see SKILL.md. Unexpanded before .NET 11 by design. |

## Inline tags

| Tag | Use |
| --- | --- |
| `<para>text</para>` | A paragraph inside `<summary>`, `<remarks>`, `<returns>` or `<example>`. Replaces `<br/>`. |
| `<c>text</c>` | Inline code: identifiers, literals, short expressions. |
| `<code lang="fsharp">text</code>` | Multi-line code. `lang` is always present: `fsharp`, `xml`, `json`, `shell`, `csharp`, `typescript`. |
| `<paramref name="x"/>` | Reference to a parameter. In Rider this opts the member into documenting every parameter; prefer `<c>x</c>` when there are no `<param>` tags. |
| `<typeparamref name="'T"/>` | Reference to a type parameter. |
| `<see cref="...">text</see>` | Inline link. Keep the fact in the prose; the link is unchecked. |

## cref forms

F# neither resolves nor checks crefs, even with FS3390. Write the full XML signature, the form
that appears in the generated `.xml` file:

| Prefix | Target | Example |
| --- | --- | --- |
| `T:` | type, module (compiled as a type) | `T:Partas.Build.Stage` |
| `M:` | method, function, constructor | `M:Partas.Build.Stage.run(Partas.Build.Context)` |
| `P:` | property | `P:Partas.Build.Stage.Name` |
| `F:` | field | `F:Partas.Build.Defaults.Timeout` |
| `E:` | event | `E:Partas.Signals.Store.Changed` |

The exact signature of an existing member can be copied from the project's generated `.xml`
(`bin/<config>/<tfm>/<Assembly>.xml`). A curried F# function compiles to a method with one
parameter per curried argument; `FSharpFunc` appears as
`Microsoft.FSharp.Core.FSharpFunc{A,B}`.

## Escaping

`///` bodies starting with `<` are XML. `<`, `>` and `&` in text must be escaped, which makes
prose harder for both audiences to read. In order of preference:

1. Rephrase so the character is not needed (`a list of strings`, not `string list` in brackets).
2. Use an F# form without angle brackets: `'T list`, `int option`, `Result of 'T * string`.
3. For code with generics or operators, use CDATA:

```xml
/// <example>
/// <code lang="fsharp"><![CDATA[
/// let xs = ResizeArray<int>()
/// xs.Add 1 |> ignore
/// ]]></code>
/// </example>
```

## Formatting inside `///`

- One space after `///`. Keep lines within the project's `.editorconfig` `max_line_length` (150 in
  Partas repos).
- Short docs fit on one line: `/// <summary>The resolved absolute path.</summary>`.
- Longer docs put tags on their own lines with content between them.
- A primary constructor is documented by a `///` block placed immediately before its argument
  list, per Microsoft's guidance.

## Compiler support

| Setting | Effect |
| --- | --- |
| `<GenerateDocumentationFile>true</GenerateDocumentationFile>` | Writes `<Assembly>.xml` next to the DLL; this is what tooltips read from a package. |
| `<WarnOn>$(WarnOn);3390</WarnOn>` | FS3390: malformed XML, unknown `<param>` names, undocumented parameters when some are documented. |

FS3390 does not check crefs, `<typeparam>` names, or missing docs.
