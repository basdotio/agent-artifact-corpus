# Security Policy

## Threat model — read this before running

KadeMCP is a CTF-solving toolkit. Several tools **execute arbitrary code and
binaries by design**:

- `run_python`, `run_crypto`, `run_webscript`, `run_pwnscript` run arbitrary
  Python supplied through the MCP client.
- `run_binary` executes uploaded/target binaries.
- The command-running helper (`tools/utils.run_cmd`) shells out to system tools
  (objdump, tshark, steghide, hashcat, …).

There is **no in-process OS-level sandbox** — no seccomp profile, no namespace
isolation, no filesystem jail. The intended isolation boundary is the **Docker
container** shipped with this repo, which runs as the unprivileged `ctf` user.

### Consequences

- Do **not** run this server directly on a host you care about. Use the
  container.
- Do **not** expose the server on a network port. It runs shell commands and
  arbitrary code; anyone who can reach it can run code as the server user.
- Treat any MCP client connected to this server as fully trusted.

### Path confinement (optional hardening)

Set the `KADEMCP_WORKSPACE` environment variable to a directory to confine
user-supplied `filepath` arguments to that directory (symlink-resolved). This
restricts *file path access* for tools like `disassemble`, `file_info`, and
`stego_extract`. It does **not** sandbox code execution — a `run_python` payload
can still touch anything the process can.

```bash
docker run --rm -i -e KADEMCP_WORKSPACE=/work -v "$PWD/challenges:/work" kademcp
```

## Reporting a vulnerability

This is a personal/research project. If you find a security issue in the tooling
itself (as opposed to the intended arbitrary-execution behavior described above),
open a GitHub issue, or if it is sensitive, contact the maintainer privately via
the email on the GitHub profile.
