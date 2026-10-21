# Background log triage

The standalone triage loop uses Python and requests to process local log input with a local Ollama model. It does not import the local_llm package. Each invocation runs one bounded cycle and exits; an operator can arrange a schedule separately. No scheduler or watchdog registration is supplied by this public copy.

## Local configuration

Copy config.example.json to config.json in this directory, then configure watch_paths for your own input and choose the Ollama model. Relative paths are resolved against this script directory. Keep local configuration and generated state out of Git. The example uses relative input and state paths; it is a starting configuration, not a bundled service deployment.

The ollama_url setting is the full URL of the local Ollama generate endpoint, including the /api/generate path (for example http://127.0.0.1:11434/api/generate); each request is posted to that URL exactly as written. Model selection for this loop uses its model setting independently of the text and file-tool environment variables. Configure an installed model before running a cycle.

The example exposes the per-call and per-cycle size limits (named max_chars_per_call and max_chars_per_cycle, but applied as UTF-8 bytes of the raw log input), context size, request timeout, drain bounds, failure threshold, state paths and capability-probe setting. Choose settings appropriate to your input and machine. probe_capability is disabled in the example; enable it only when you intend to run the local service probe.

## Processing boundaries

The loop reads whole lines and tracks committed progress with byte offsets. Change detection compares the file's current size with the stored offset only: input that shrinks below the stored offset resets that offset to the start of the file. A file replaced by one of the same or larger size is not detected, and reading resumes at the old offset inside the new content; a truncated file that has grown back past the old offset before the next cycle is likewise missed. Rotate by truncating the watched file, or by writing new output under a new file name with its own watch path, rather than by replacing a watched file in place. Adaptive shrinking handles size, timeout and output-exhaustion responses without silently splitting a line. Repeated outage or unparseable-output failures can eventually skip input after the configured threshold and write an alert.

Configuration is handled in two different ways. These settings fail closed: the model lane's ollama_num_ctx, output_margin_tokens, preamble_tokens, chars_per_token_floor, max_chars_per_call, max_chars_per_cycle, min_batch_chars, max_consecutive_failures and think, plus the benign_line_regexes table for model-lane paths, and max_chars_per_cycle for passthrough-lane paths. An invalid value holds the stored offset, reads nothing for that path and writes a high-severity alert. The two drain settings, cycle_time_budget_seconds and max_drain_rounds, do not: a non-positive or mistyped value is replaced by the built-in default (180 seconds, 50 rounds) and only an error line is written to the loop's log, with no alert record. Other settings, such as request_timeout_seconds, are not separately validated by the loop.

A benign_line_regexes pattern must match the whole line (it is applied with fullmatch), so a pattern without an end anchor does not hide a longer line that merely starts the same way. A single record longer than the per-cycle cap, counted in UTF-8 bytes of the raw line and not in characters, can never be read whole: the loop holds the offset, writes one high-severity "Oversize" alert for that path, and keeps waiting until the cap is raised above the record length in bytes (max_chars_per_cycle in the passthrough lane; in the model lane the smaller of max_chars_per_call, max_chars_per_cycle and what fits ollama_num_ctx) or the file is rotated by truncating it.

Structured alerts selected by passthrough_globs use the deterministic lane without a model request. The model lane wraps the watched text in a data fence whose markers carry a per-run random nonce. The nonce only stops a log line from forging the fence markers; it is a delimiter, not a defense. Text in a watched file can still steer what the model reports, so model-lane alerts can be wrong or missing, and an alert (or the absence of one) must be checked against the source log before you act on it. Capability probing and bounded backlog draining are configurable; these are operational guards rather than a guarantee about model accuracy or total execution time. Concurrent cycles must be prevented by the operator's scheduling choice.

## Run and test

These commands use the project's virtual environment (created in the root README's Setup section) rather than a bare python, which on Windows can resolve to the Microsoft Store stub or an unrelated global interpreter. From the repository root, install the declared package with its test extra, then run the tests for this loop:

```powershell
& ./.venv/Scripts/python.exe -m pip install ".[test]"
& ./.venv/Scripts/python.exe -m pytest tests/test_triage_loop.py tests/test_triage_hardening.py tests/test_triage_benign_filter.py tests/test_alert_digest.py tests/test_public_release_safety.py -q
```

These tests mock model requests and create synthetic temporary input; they need no Ollama and create no links. The full suite (`& ./.venv/Scripts/python.exe -m pytest tests -q`) also runs the file-tool tests, which create real Windows links in temporary folders: symbolic links need Developer Mode or an elevated shell, and junctions and hard links need the temporary folder on an NTFS volume. Those tests fail rather than skip when a link cannot be created.

To run an intentional local model cycle, configure this directory's config.json and run `& ./.venv/Scripts/python.exe loops/triage_loop.py` from the repository root. This command talks to the configured Ollama service and writes the configured local state.
