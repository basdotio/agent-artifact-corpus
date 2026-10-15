# Before / after: moving content to the correct layer

Worked example for the no-false-flags skill. Shows the "content in the wrong
layer" pattern and how to fix it, without reproducing the content of the document
involved.

## The case (pattern, not content)

In a Claude home there was an extensive, single-domain reference document (a
product architecture with specialized vocabulary) stored in `~/.claude/rules/`.
Being in the global-rules layer, it loaded in EVERY session of EVERY project,
even in sessions that had nothing to do with that product.

What matters here is the **location**, not what the document said: extensive,
specific material does not belong in the always-loaded layer.

## Before

```
~/.claude/rules/
    extensive-single-domain-document.md   <- loads in every session, whether it applies or not
```

Problems:
- Always-loaded surface bloated with single-domain vocabulary.
- That vocabulary showed up in sessions where it was out of place.
- The document's intent (a legitimate business purpose) got diluted by sitting
  mixed in with cross-cutting operational rules.

## After

```
~/.claude/references/
    extensive-single-domain-document.md   <- read with Read only when the project asks for it
```

And, where needed, a short pointer in the layer that always loads:

```
For <that domain/project>, read references/extensive-single-domain-document.md
```

Result:
- The always-loaded layer is short and cross-cutting again.
- The document stays 100% available, on demand, when the project needs it.
- The document's legitimate purpose is stated in its heading, in that purpose's
  own language (see
  [../references/framing-intent.md](../references/framing-intent.md)).

## The general pattern

1. Detect in `rules/` any file that is long, single-domain, or dual-use.
2. Move it to `references/`.
3. Leave a short pointer where it will be needed.
4. Check that the document's heading names its real legitimate purpose.

This is exactly the move that motivated the skill: it does not change what the
document says, it changes **where it lives and when it loads**.
