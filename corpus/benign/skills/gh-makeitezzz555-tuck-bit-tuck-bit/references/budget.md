# Evidence-based execution budgets (default)

Economy: prefer one worker, small context, focused validation for low-risk simple tasks.
Balanced (default): select effort according to complexity and risk, allow justified delegation.
Critical: perform independent review and stronger checks when security, data loss or complicated integration justifies it.

An iteration should change the evidence or implementation. If a tool call yields no useful new information, reconsider the search or stop; don't loop.
Limit unproductive retries. Batch related questions and terminal inspections where safe.
Separate mandatory work from speculative improvements. Avoid repeated model-powered reviews that examine an identical diff.
Preserve high-value reasoning: using extra tokens to avoid bad architectural decisions can be the cheaper choice.
Never equate cached input tokens with a zero-cost execution.
