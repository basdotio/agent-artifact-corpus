"""
Reversing / Pwn tools:
  - disassemble     : objdump disassembly of a binary
  - strings_extract : run `strings` on a file
  - ltrace_strace   : run ltrace or strace on a binary with args
  - checksec        : check binary protections (via checksec)
  - run_pwnscript   : execute a pwntools Python script
  - run_binary      : run a binary with optional stdin and capture output
"""

import base64
import os

from mcp.types import Tool

from tools.utils import clamp_int, resolve_workspace_path, run_cmd, run_python, write_tempfile

reversing_tools = [
    Tool(
        name="disassemble",
        description=(
            "Disassemble a binary using objdump. "
            "Pass the binary as base64 in `binary_b64`, or provide a `filepath`. "
            "Optional: `arch` (default: auto), `section` (e.g. .text)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "binary_b64": {"type": "string", "description": "Base64-encoded binary bytes"},
                "filepath": {"type": "string", "description": "Absolute path to binary on disk"},
                "section": {"type": "string", "description": "ELF section to disassemble (default: .text)"},
                "arch": {
                    "type": "string",
                    "enum": ["auto", "x86", "x86_64", "arm", "aarch64", "mips", "ppc", "riscv"],
                    "default": "auto",
                    "description": (
                        "Target architecture. 'auto' lets objdump detect it. "
                        "Intel syntax (-M intel) is only applied for x86/x86_64."
                    ),
                },
            },
        },
    ),
    Tool(
        name="strings_extract",
        description="Run `strings` on a binary or file to find printable strings. Accepts base64 or filepath.",
        inputSchema={
            "type": "object",
            "properties": {
                "binary_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "min_length": {"type": "integer", "description": "Minimum string length (default: 4)", "minimum": 1, "maximum": 1024},
            },
        },
    ),
    Tool(
        name="ltrace_strace",
        description=(
            "Trace a binary's library calls (ltrace) or system calls (strace). "
            "Pass the binary as base64 in `binary_b64`, or provide a `filepath`. "
            "Choose `tracer` (ltrace | strace, default: strace) and optional `args` "
            "to pass to the binary."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "binary_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "tracer": {"type": "string", "enum": ["ltrace", "strace"], "default": "strace"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "CLI arguments for the binary"},
            },
        },
    ),
    Tool(
        name="checksec",
        description="Check binary security protections (NX, PIE, RELRO, stack canary) using checksec.",
        inputSchema={
            "type": "object",
            "properties": {
                "binary_b64": {"type": "string"},
                "filepath": {"type": "string"},
            },
        },
    ),
    Tool(
        name="run_binary",
        description="Execute a binary with optional stdin input and capture stdout/stderr. 20s timeout.",
        inputSchema={
            "type": "object",
            "properties": {
                "binary_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "CLI arguments"},
                "stdin": {"type": "string", "description": "Data to send on stdin"},
            },
        },
    ),
    Tool(
        name="run_pwnscript",
        description=(
            "Execute a Python pwntools script. "
            "Write your full exploit in `code`. "
            "Use process('/path/to/binary') or remote('host', port). "
            "The script runs as a subprocess; print() output is returned."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Full Python pwntools script"},
            },
            "required": ["code"],
        },
    ),
]


def _resolve_binary(args: dict) -> tuple[str | None, str | None, bool]:
    """Return (filepath, error_msg, is_temp). Writes temp file if b64 supplied.

    is_temp tells the caller whether it created the file (and so is
    responsible for deleting it) versus reusing a user-supplied filepath.
    """
    if "filepath" in args and args["filepath"]:
        real, err = resolve_workspace_path(args["filepath"])
        if err:
            return None, err, False
        return real, None, False
    if "binary_b64" in args and args["binary_b64"]:
        try:
            # Strip whitespace (tolerate wrapped base64) then validate so
            # out-of-alphabet characters raise instead of silently decoding.
            cleaned = "".join(args["binary_b64"].split())
            data = base64.b64decode(cleaned, validate=True)
        except Exception as e:
            return None, f"[error] invalid base64 in binary_b64: {e}", False
        path = write_tempfile(data, suffix=".bin")
        os.chmod(path, 0o755)
        return path, None, True
    return None, "[error] provide binary_b64 or filepath", False


# Maps the arch enum to objdump's -m machine name so the architecture is
# actually applied (not just the -M intel syntax flag).
ARCH_TO_MACHINE = {
    "x86": "i386",
    "x86_64": "i386:x86-64",
    "arm": "arm",
    "aarch64": "aarch64",
    "mips": "mips",
    "ppc": "powerpc",
    "riscv": "riscv",
}
_X86_ARCHES = {"x86", "x86_64"}


async def _detect_is_x86(path: str) -> bool:
    """Best-effort check whether a binary targets x86/x86_64, via objdump -f."""
    info = await run_cmd("objdump", "-f", path)
    low = info.lower()
    return "i386" in low or "x86-64" in low or "x86_64" in low


async def handle_reversing(name: str, args: dict) -> str:
    if name == "disassemble":
        path, err, is_temp = _resolve_binary(args)
        if err:
            return err
        try:
            section = args.get("section", ".text")
            arch = (args.get("arch") or "auto").lower()

            cmd = ["objdump", "-d"]
            # Actually set the machine when a specific arch is requested; 'auto'
            # lets objdump read it from the file's own header.
            if arch != "auto":
                machine = ARCH_TO_MACHINE.get(arch)
                if machine:
                    cmd += ["-m", machine]
                use_intel = arch in _X86_ARCHES
            else:
                use_intel = await _detect_is_x86(path)

            # Intel syntax only applies to x86/x86_64.
            if use_intel:
                cmd += ["-M", "intel"]
            cmd += ["--section", section, path]
            return await run_cmd(*cmd)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "ltrace_strace":
        path, err, is_temp = _resolve_binary(args)
        if err:
            return err
        try:
            tracer = (args.get("tracer") or "strace").lower()
            if tracer not in ("strace", "ltrace"):
                return f"[error] unknown tracer: {tracer} (use 'strace' or 'ltrace')"
            cli_args = args.get("args", [])
            # -f follows forked children; both tools emit their trace on stderr,
            # which run_cmd already captures alongside stdout.
            return await run_cmd(tracer, "-f", path, *cli_args)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "strings_extract":
        path, err, is_temp = _resolve_binary(args)
        if err:
            return err
        try:
            min_len = str(clamp_int(args.get("min_length", 4), default=4, minimum=1, maximum=1024))
            return await run_cmd("strings", "-n", min_len, path)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "checksec":
        path, err, is_temp = _resolve_binary(args)
        if err:
            return err
        try:
            return await run_cmd("checksec", "--file", path)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "run_binary":
        path, err, is_temp = _resolve_binary(args)
        if err:
            return err
        try:
            cli_args = args.get("args", [])
            stdin_data = args.get("stdin", "").encode() if args.get("stdin") else None
            return await run_cmd(path, *cli_args, input_data=stdin_data)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "run_pwnscript":
        return await run_python(args["code"])

    return f"[error] unknown reversing tool: {name}"
