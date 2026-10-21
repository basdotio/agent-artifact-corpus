# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0]

### Packaging & CI
- `tools/` is now correctly included in the built wheel (`[tool.setuptools]`
  config); added a CI job that builds the wheel, installs it into a clean venv,
  and imports it from outside the repo.
- Pinned `mcp>=1.0.0,<2` — `server.py` uses the mcp 1.x decorator API, which was
  removed in 2.x.
- Declared previously-undeclared dependencies (`gmpy2`, `lxml`); added the matching
  system headers to the Docker image.
- Added a `tests/` suite and a CI job that runs it.

### Docker
- Provisions `rockyou.txt` into `/usr/share/wordlists`.
- Adds `binutils-multiarch` so `disassemble` can target non-x86 architectures.
- Adds a `.dockerignore` to keep the build context lean.

### Crypto
- `hash_crack` no longer silently defaults to MD5: it errors on unknown/ambiguous
  lengths and rejects unsupported modes. Length-32 (MD5 vs NTLM) requires an
  explicit mode.
- Fixed NTLM hash-length identification (32, not 64).
- Morse handles `/` word separators; multiple spaces collapse to one separator.
- Strict, error-handled base64 decoding.

### Web
- `db_type` now selects DB-specific SQLi payloads and error signatures.
- `sqli_test` / `lfi_test` support method + body injection (not just GET).
- All web tools reject requests with no `FUZZ` marker.
- Baseline handling is error-tolerant and no longer adopts a fuzzed response as
  the baseline; "interesting" is judged relative to the baseline status.
- Proper Windows path-traversal payloads; `depth` is bounded.
- Generated code uses `repr()` so booleans/None embed as valid Python.
- `http_request.timeout` is clamped and schema-bounded.

### Forensics / Reversing
- Extraction directories are bounded by count *and* total size, with an atexit
  sweep; extracted payloads are read with a bounded preview.
- `steghide` writes to an explicit temp path instead of relying on CWD.
- `disassemble` gained a working `arch` option; `ltrace_strace` implemented.
- Numeric fields (`length`, `offset`, `min_length`, `depth`, `timeout`) have
  schema bounds and defensive clamping.

### Robustness / Safety
- Handler exceptions in `server.py` are caught and returned as controlled errors.
- `run_cmd` starts a new session and kills the whole process group on timeout,
  then reaps the process.
- Optional path confinement via `KADEMCP_WORKSPACE`.
- Corrected the misleading "sandboxed" description; documented the real security
  model in `SECURITY.md`.
