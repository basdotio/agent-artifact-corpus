"""UAT mode: persona-driven acceptance runs against a product, driven by an LLM.

A run takes a *persona* (who is visiting, from where, with what goal and
budget), a *target* (which sites the run may use) and a *brain* (which model
or agent harness plays the persona), drives the browser through the ordinary
lyra-browser tools, and writes ``report.json``.

The brain is replaceable; what makes a run trustworthy is not. The trace of
every tool call, the step budget, the screenshot after each action and the
guards on what a persona must never do are enforced by the server
(``recorder.UatMiddleware``), so they hold whether the persona is played by
our own tool-use loop or by an external harness that spawned
``lyra-browser --uat-run`` as its MCP server.

Nothing here is imported by the core server. The LLM SDKs are optional
(``pip install lyra-browser[uat]``) and are imported inside the brain that
needs them.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
