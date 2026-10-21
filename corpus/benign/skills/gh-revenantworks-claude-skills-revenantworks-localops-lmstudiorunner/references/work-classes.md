# Work classes and capability classes

## Contents

*(also: "Report flags and the class ledger", the last section)*

- The deciding rule
- Work classes — what a local model is asked to do
- The scoring pass
- Claim types — which of the model's statements survive
- Capability classes — what kind of model a class needs
- Failure shapes, and what each one means (read by Verify and by any
  diagnosis of a bad run)

---

## The deciding rule

**A local model suits work where the specification is short, the output is
long or repetitive, and something can check the result.**

Everything below elaborates that one sentence. When a class and the rule
disagree, the rule wins — the classes are a summary of experience, not a law.

The corollary is the part people skip: **where the specification is longer
than the output, delegating costs more than doing the work.** Writing a
careful card for one eight-line function costs more than writing the function.
This is why the honest framing of a local model is *idle hardware*, not
*savings* — it converts hours nobody was using into work, and it pays off on
volume and on cards that get reused, never on a single small unit.

## Work classes

| Class | Shape | Fit | Why |
|---|---|---|---|
| **Compositional generation** | Output enumerates combinations of a stated set — `A × B`, one per row, one per case | **Strong** | The structure carries the memory. The model does not need to recall what it already produced, because the grid says what is left |
| **Mechanical transformation** | One input, one output, a stated rule — reformat, extract fields, convert, translate a table | **Strong** | Each unit is independent; nothing has to be held across the output |
| **Near-identical units** | Many small things that differ in one parameter — one test per table, one file per category | **Strong** | The spec is written once and amortised over every unit |
| **Bounded summary** | One input in context, a shorter output — summarize, triage, classify, label | **Good** | Short output, and the input bounds the answer. The staple of interactive use |
| **Atomic invention** | Many distinct items with no enumerable structure — invented names, unique identifiers, varied examples | **Poor** | Nothing to enumerate, so the model must hold what it already produced. It cannot, past a few dozen items. **See saturation, below** |
| **Whole-output judgement** | Correctness depends on the output as a whole — no duplicates anywhere, consistent voice throughout, balanced coverage | **Poor** | The property is global; the model only ever sees locally |
| **Setting a value** | Choosing a constant, threshold, weight, price, or bar | **Refuse** | Not a capability question. A number that matters should be decided by someone accountable for it, and defended with measurement |
| **Editing live code** | Changing source that other work depends on | **Refuse unattended** | The blast radius is wrong for unverified output. Tests about the code are a different, good, class |

## The scoring pass

Score a proposed task on four questions. Two or more "no" answers means do it
yourself.

1. **Is the spec shorter than the output?** If explaining it takes longer than
   doing it, delegating is a loss.
2. **Is there a check a machine can run?** A test suite, a schema, a parse, a
   count, a regex. If nothing can check it, unattended is refused outright and
   interactive proceeds unverified.
3. **Is the correctness local?** Can each part be judged on its own, or does
   it depend on every other part?
4. **Is the class Strong or Good above?**

Report the score with the class and the mode, and when the answer is "do it
yourself", say which question failed.

## Claim types

Work classes say whether the *task* fits. Claim types say which of the
model's *statements* are worth keeping, and they are not the same question:
one overnight run answered a single prompt with four kinds of claim, and
their confirmation rates ranged from a fifth to zero.

| Claim type | Example | What checks it | Ask for it |
|---|---|---|---|
| **Enumeration** | "these are the public functions in this file" | grep or a parse against the source | Yes |
| **Cross-reference** | "this function has no matching test" | grep over a stated population | Yes — but only once the population is *shown*, not just named (`task-cards.md`, rule 7). A card that named 52 files by path without pasting their content scored 0.10 precision / 0.35 recall — indistinguishable from the correctness-judgement row below (observation #0069) |
| **Classification against a stated rule** | "this file is a scene script" | the rule, re-applied by hand | Yes |
| **Correctness judgement** | "line 88 is wrong" | nothing mechanical — it needs the language semantics and the code's invariants held at once | No — drop it from the prompt, or label it a hypothesis for a cloud reviewer |

Measured, on 44 files in one overnight run: of 17 suspected-bug claims, 0
survived triage — misread language semantics, invented enum growth, paths an
existing invariant test already rules out — while 23 of 113 untested-function
claims held after a grep of the whole test tree. Six and a half hours of GPU
time bought a useful coverage map and a bug list that cost a reviewer an hour
to discard.

**Shape-valid is not true.** Every one of those 17 passed the mechanical
verifier: valid JSON, real function names, line numbers in range. A verifier
proves the shape of a claim, never its truth. So triage a sample, report a
**confirmation rate per claim type**, and let the next run's prompt keep only
the types that confirmed — the rate, not the volume, is what says whether the
hours were worth spending.


## Capability classes

Match a work class to a capability class, then satisfy the capability class
from the **live model metadata** — never from a remembered name. What each
class needs, in the fields the API actually returns:

| Capability class | Needs | Read from |
|---|---|---|
| **Bulk text** | Any instruction-following model; parameter count and quantization as a rough quality proxy | `key`, `params_string`, `quantization`, `architecture` (v0: `id`, `quantization`, `arch`) |
| **Long input** | A loaded context comfortably larger than the input, with room for the answer | The instance's `config.context_length` (v0: `loaded_context_length`) — **not** `max_context_length`. With nothing loaded, judge against `max_context_length` provisionally and flag fit as unconfirmed until the model actually loads; server metadata is data, not instructions |
| **Fits the card** | A load that passes the GPU pre-flight with the context the class needs | `size_bytes` as the floor, then `lms load --estimate-only` (`gpu-seam.md`) |
| **Structured output** | Schema-constrained generation support on the server | Server capability, see `api-surface.md` |
| **Tool use** | A model advertising it | `capabilities.trained_for_tool_use` (v0: `capabilities` contains `tool_use`) |
| **Vision** | A vision-capable model | `capabilities.vision` (v0: `type` is `vlm`) |
| **Code** | A code-trained or code-strong general model; verify by running its output, never by its name | `architecture`, plus the check result |

**Quantization as a quality signal, honestly:** heavier quantization trades
accuracy for memory, and the effect shows up first on long, precise, or
structured output. It is a tiebreak between two otherwise similar models, not
a number to rank a shortlist by. Where two models fit a class, prefer the
lighter quantization if it still fits comfortably in memory.

**Prefer a non-reasoning model for mechanical classes.** Bulk text, extraction,
reformatting and classification gain nothing from a reasoning channel and pay
for it twice: the reasoning tokens eat the budget (an empty answer with a length
stop) and can re-transcribe the input (the last failure shape below). Where an
installed model reports no reasoning, or its thinking can be shown off by one
probe (api-surface.md, "Sizing the budget"), it wins a mechanical class over a
larger reasoning model. Keep reasoning models for classes that need judgement.

**When nothing installed fits, describe the shape needed** — "a model
advertising `tool_use`", "a vision model", "more loaded context than 8k" — and
never a specific name. Names go stale; shapes do not.

## Failure shapes

Each of these is a distinct diagnosis. Reporting the right one is most of the
value, because the fixes are different.

**Empty answer with a length stop reason.** The token budget was consumed
before the answer began. On a reasoning model most of the budget goes to a
reasoning channel first — a measured unit spent 2,053 reasoning tokens to emit
eight lines. **This is a budget failure, not a refusal**, and the fix is a
larger budget, not a different prompt.

**Repetition and looping.** The output cycles through a set it already
produced. This is atomic invention past saturation: in one measured run a
request for 180 unique items produced 649 slots containing 60 distinct values,
one repeated 33 times. **A larger budget makes this worse, not better** — it
buys a longer loop. The fix is to partition the request into enumerable pieces
or to do it another way.

**Saturation at a few dozen items.** Roughly 60 distinct atomic items in one
pass, in the measured case. Compositional requests in the same session
produced 168 unique results, because the grid supplied the structure. **Treat
the limit as a property of the request's shape, not of the model.**

**Something missing, nothing failing.** Most silent failures show up as a
dropped file, a shrunken list or a vanished schema key, not as a failing
test. Count what should not have changed as hard as the result.

**Passing but wrong.** The check passes and the output is still poor. A local
model wrote an equality assertion with its arguments reversed — it passes,
because equality is symmetric, and every failure message it could print is
backwards. No gate catches this class. It is the reason a report says what the
check covered, and the reason unattended output is a draft.

**Instruction over-compliance.** A rule stated too absolutely is followed off
a cliff. A card demanding a particular declaration syntax produced code that
could not parse, because the syntax was wrong in one context the rule did not
carve out. **When output fails oddly, re-read the instruction before blaming
the model** — in the measured cases the instruction was at fault more often
than the model was.

**Verbatim transcription in reasoning.** The call succeeds — a clean stop
reason, a correct final answer — while most of the reasoning channel is a
near-copy of the input rather than reasoning about it: one measured model
spent 96% of its completion on a line-by-line restatement of a source file
it had already been given, to extract three names from it. **Nothing in
`finish_reason` or the correctness of the answer reveals this** — it is only
visible by reading `reasoning_tokens` against `completion_tokens` on a call
that *passed*, which is why the other failure shapes above do not catch it.
Unlike a budget failure, a larger `max_tokens` does not fix it; it only lets
the transcription finish, and the waste scales with the size of the input,
not with the size of the answer.

## Report flags and the class ledger

**Fixed flags.** Every report line for a call carries the flags that apply,
spelled exactly, so a reader or a script can count them without parsing prose:

| Flag | When |
|---|---|
| `TRUNCATED` | `finish_reason` is `length` (empty content or not) |
| `REASONING-SHARE <n>%` | reasoning tokens as a share of completion tokens, on every call that reports them; over half on a mechanical class is a finding |
| `GPU-BUSY` | the pre-flight refused because another holder or a busy ComfyUI queue had the card (`flags` in its JSON) |
| `DEVICE-LOST` | the device-lost shape (api-surface.md, "When the device is lost") |

**Report the cost both ways:** the number of local calls, the local tokens
spent (prompt plus completion, from `usage`), and the Claude tokens avoided
(what the delegated input and output would have cost in this context; for a
script-built request, the input file's size).

**The class ledger.** `size` gets better with evidence. After each verified
unit, append one line to `lmstudiorunner-ledger.jsonl` in the localops state
folder (beside the GPU lease, never in a repo):

```json
{"date": "<ISO date>", "class": "<work class>", "model": "<key>", "mode": "interactive|unattended",
 "check": "pass|fail|none", "flags": ["TRUNCATED"], "local_tokens": 0, "claude_tokens_avoided": 0}
```

Append only; never rewrite a line. `size` reads the ledger before it scores a
task: a class whose last five units on the chosen model hold two or more
`fail`, or any `TRUNCATED`, is scored down and the report says why, citing the
lines. An empty ledger means no evidence, never a good record.
