## F# XML documentation

Full conventions: the `fsharp-xml-docs` skill (`fsharp-xml-docs@partas`). These are the rules
that must be in context while a doc is being written.

- Every `///` doc starts with `<summary>`. A doc states the contract for a caller: what it is or
  computes, what it needs, how it fails. It never argues that the code is correct.
- Prose budget: summary 1–2 lines; remarks at most 3 prose lines (tag lines and `<code>` do not
  count). Public API always gets a summary; private members only when behaviour is not visible
  in the signature.
- `<param>`: all or none, never empty. With no `<param>` tags, refer to parameters as
  `<c>name</c>`, not `<paramref>`.
- Tags: `summary remarks param typeparam returns exception seealso example include` and inline
  `para code c paramref typeparamref see`. `<code>` always has `lang` (`<code lang="fsharp">`).
  Paragraphs are `<para>`, never `<br/>`. crefs use the full form (`T:Ns.Type`).
- `<include>` is allowed for text shared by several members; keep the `<summary>` inline. Write
  the fragment into `xmldoc/<module>.xml` in the same edit as the tag; each fragment holds complete
  `<remarks>`/`<example>` elements. Before .NET 11 it does not expand in the generated `.xml`;
  that is expected, not a defect.
- Write the doc with the declaration, from the code in front of you, not at the end of the change.
- Docs from a generator or transcribed from JS/TS docs (JSDoc, MDN) are left as they are unless the user asks.
