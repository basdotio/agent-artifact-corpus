# Token-consumption judgment reference

This auditor uses a conservative, qualitative signal rather than pretending to
measure model tokens. The reference is the public [Ponytail project](https://github.com/DietrichGebert/ponytail),
especially its YAGNI/minimal-context framing and progressive, task-sized
workflow.

Report a `token-overuse` candidate only when an instruction makes the extra
context or output unconditional, repeated, exhaustive, or unrelated to the
current task. Examples include rereading every file on every turn, loading all
skills before choosing one, or requiring exhaustive explanations for trivial
changes. Do not infer a token problem from a concise, conditional step, a
bounded safety check, or a user-requested detailed deliverable.

This reference changes classification only. The skill reports evidence and
judgment; it does not estimate tokens or suggest edits.
