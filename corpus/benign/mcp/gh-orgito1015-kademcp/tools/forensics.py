"""
Forensics / Stego tools:
  - file_info       : file type, magic bytes, metadata (file + exiftool)
  - binwalk_scan    : scan for embedded files and extract them
  - hex_dump        : hexdump with ASCII sidebar
  - stego_extract   : steghide / zsteg / outguess extraction
  - metadata_strip  : dump full EXIF/metadata from images
  - pcap_analyze    : basic pcap analysis (tshark summary)
  - carve_strings   : strings with offset info
"""

import atexit
import base64
import os
import shutil
import tempfile

from mcp.types import Tool

from tools.utils import clamp_int, resolve_workspace_path, run_cmd, write_tempfile

# Extraction output dirs (binwalk --extract, tshark --export-objects) are handed
# back to the caller so they can't be deleted immediately, but they must not grow
# without bound. We evict oldest-first on BOTH a count cap and a total-size cap,
# and register an atexit sweep so nothing survives process shutdown.
#
# Trade-off: because paths are returned for later inspection, a very old
# extraction may be reclaimed once newer ones exceed a cap. Callers should read
# what they need promptly; a reclaimed path is reported as missing on next use.
_EXTRACT_DIRS: list[str] = []
_MAX_EXTRACT_DIRS = 10
_MAX_EXTRACT_BYTES = 512 * 1024 * 1024  # 512 MB across all live extraction dirs


def _dir_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _evict_extract_dirs() -> None:
    """Drop oldest dirs until within both the count and total-size caps."""
    while _EXTRACT_DIRS and (
        len(_EXTRACT_DIRS) > _MAX_EXTRACT_DIRS
        or sum(_dir_size(d) for d in _EXTRACT_DIRS) > _MAX_EXTRACT_BYTES
    ):
        old = _EXTRACT_DIRS.pop(0)
        shutil.rmtree(old, ignore_errors=True)


def _new_extract_dir() -> str:
    """Create a tracked extraction temp dir, enforcing the caps."""
    d = tempfile.mkdtemp(prefix="kademcp_extract_")
    _EXTRACT_DIRS.append(d)
    _evict_extract_dirs()
    return d


@atexit.register
def _cleanup_extract_dirs() -> None:
    for d in _EXTRACT_DIRS:
        shutil.rmtree(d, ignore_errors=True)
    _EXTRACT_DIRS.clear()


forensics_tools = [
    Tool(
        name="file_info",
        description="Identify a file's type, magic bytes, and basic metadata. Accepts base64 or filepath.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string", "description": "Base64-encoded file bytes"},
                "filepath": {"type": "string"},
            },
        },
    ),
    Tool(
        name="binwalk_scan",
        description=(
            "Scan a file for embedded content using binwalk. "
            "Set extract=true to extract detected files into a temp directory."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "extract": {"type": "boolean", "default": False},
            },
        },
    ),
    Tool(
        name="hex_dump",
        description="Produce a hex dump of a file or bytes. Limit bytes shown with `length`.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "length": {"type": "integer", "description": "Max bytes to dump (default: 512)", "minimum": 1, "maximum": 1048576},
                "offset": {"type": "integer", "description": "Start offset (default: 0)", "minimum": 0},
            },
        },
    ),
    Tool(
        name="stego_extract",
        description=(
            "Attempt steganography extraction using steghide, zsteg (PNG/BMP), and outguess. "
            "Optionally provide a passphrase."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "passphrase": {"type": "string", "description": "Steghide passphrase (try empty if unknown)"},
            },
        },
    ),
    Tool(
        name="metadata_dump",
        description="Dump full EXIF and metadata from an image or document using exiftool.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
            },
        },
    ),
    Tool(
        name="pcap_analyze",
        description=(
            "Analyze a PCAP file. "
            "Modes: summary (default), http_objects, dns, credentials, follow_tcp."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "mode": {
                    "type": "string",
                    "enum": ["summary", "http_objects", "dns", "credentials", "follow_tcp"],
                    "default": "summary",
                },
                "stream_index": {"type": "integer", "description": "TCP stream index for follow_tcp mode"},
            },
        },
    ),
    Tool(
        name="carve_strings",
        description="Extract printable strings with file offsets. Useful for finding hidden flags.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_b64": {"type": "string"},
                "filepath": {"type": "string"},
                "min_length": {"type": "integer", "default": 6, "minimum": 1, "maximum": 1024},
                "filter_pattern": {"type": "string", "description": "Only show strings matching this substring"},
            },
        },
    ),
]


def _read_preview(path: str, preview: int = 500) -> tuple[bytes, int]:
    """Return (first `preview` bytes, total file size) without reading it all.

    Only a bounded chunk is loaded into memory, so a huge embedded payload can't
    exhaust RAM just to display a short preview.
    """
    try:
        total = os.path.getsize(path)
    except OSError:
        total = 0
    with open(path, "rb") as f:
        shown = f.read(preview)
    return shown, total


def _resolve_file(args: dict, suffix: str = "") -> tuple[str | None, str | None, bool]:
    """Return (filepath, error_msg, is_temp).

    is_temp tells the caller whether it created the file (and so is
    responsible for deleting it) versus reusing a user-supplied filepath.
    """
    if "filepath" in args and args["filepath"]:
        real, err = resolve_workspace_path(args["filepath"])
        if err:
            return None, err, False
        return real, None, False
    if "file_b64" in args and args["file_b64"]:
        try:
            # Strip whitespace (tolerate wrapped base64) then validate so
            # out-of-alphabet characters raise instead of silently decoding.
            cleaned = "".join(args["file_b64"].split())
            data = base64.b64decode(cleaned, validate=True)
        except Exception as e:
            return None, f"[error] invalid base64 in file_b64: {e}", False
        path = write_tempfile(data, suffix=suffix)
        return path, None, True
    return None, "[error] provide file_b64 or filepath", False


async def handle_forensics(name: str, args: dict) -> str:
    if name == "file_info":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        try:
            file_out = await run_cmd("file", path)
            exif_out = await run_cmd("exiftool", "-s", "-s", path)
            return f"=== file ===\n{file_out}\n\n=== exiftool (short) ===\n{exif_out}"
        finally:
            if is_temp:
                os.unlink(path)

    if name == "binwalk_scan":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        try:
            if args.get("extract"):
                outdir = _new_extract_dir()
                result = await run_cmd("binwalk", "--extract", "--directory", outdir, path)
                listing = await run_cmd("find", outdir, "-type", "f")
                return f"{result}\n\nExtracted files:\n{listing}"
            return await run_cmd("binwalk", path)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "hex_dump":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        try:
            length = clamp_int(args.get("length", 512), default=512, minimum=1, maximum=1048576)
            offset = clamp_int(args.get("offset", 0), default=0, minimum=0, maximum=2**63 - 1)
            return await run_cmd("xxd", "-l", str(length), "-s", str(offset), path)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "stego_extract":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        out_path = None
        steg_dir = None
        try:
            passphrase = args.get("passphrase", "")
            results = []

            # steghide — write to an explicit path in a dedicated writable temp
            # dir (-xf) instead of relying on CWD, which is root-owned (/app) in
            # the Docker image while the process runs as the unprivileged `ctf` user.
            steg_dir = tempfile.mkdtemp()
            steg_out = os.path.join(steg_dir, "steghide_output.bin")
            sh_result = await run_cmd(
                "steghide", "extract", "-sf", path, "-p", passphrase, "-xf", steg_out, "-f"
            )
            if os.path.exists(steg_out):
                shown, total = _read_preview(steg_out)
                sh_result += f"\nExtracted {total} bytes (showing first {len(shown)}): {shown}"
            results.append(f"=== steghide ===\n{sh_result}")

            # zsteg (PNG/BMP)
            zs_result = await run_cmd("zsteg", "-a", path)
            results.append(f"\n=== zsteg ===\n{zs_result}")

            # outguess
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as _tmp:
                out_path = _tmp.name
            og_result = await run_cmd("outguess", "-r", path, out_path)
            if os.path.exists(out_path):
                shown, total = _read_preview(out_path)
                og_result += f"\nExtracted {total} bytes (showing first {len(shown)}): {shown}"
            results.append(f"\n=== outguess ===\n{og_result}")

            return "\n".join(results)
        finally:
            if out_path and os.path.exists(out_path):
                os.unlink(out_path)
            if steg_dir:
                shutil.rmtree(steg_dir, ignore_errors=True)
            if is_temp:
                os.unlink(path)

    if name == "metadata_dump":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        try:
            return await run_cmd("exiftool", path)
        finally:
            if is_temp:
                os.unlink(path)

    if name == "pcap_analyze":
        path, err, is_temp = _resolve_file(args, suffix=".pcap")
        if err:
            return err
        try:
            mode = args.get("mode", "summary")

            if mode == "summary":
                return await run_cmd(
                    "tshark", "-r", path, "-q", "-z", "conv,tcp", "-z", "io,stat,0"
                )
            if mode == "http_objects":
                outdir = _new_extract_dir()
                await run_cmd("tshark", "-r", path, "--export-objects", f"http,{outdir}")
                listing = await run_cmd("ls", "-la", outdir)
                return f"HTTP objects exported to {outdir}:\n{listing}"
            if mode == "dns":
                return await run_cmd(
                    "tshark", "-r", path, "-Y", "dns", "-T", "fields",
                    "-e", "dns.qry.name", "-e", "dns.a"
                )
            if mode == "credentials":
                return await run_cmd(
                    "tshark", "-r", path, "-Y",
                    "ftp.request.command==PASS || http.authbasic || telnet",
                    "-T", "fields", "-e", "ftp.request.arg", "-e", "http.authbasic"
                )
            if mode == "follow_tcp":
                idx = args.get("stream_index", 0)
                return await run_cmd(
                    "tshark", "-r", path, "-q", "-z", f"follow,tcp,ascii,{idx}"
                )
            return "[error] unknown pcap mode"
        finally:
            if is_temp:
                os.unlink(path)

    if name == "carve_strings":
        path, err, is_temp = _resolve_file(args)
        if err:
            return err
        try:
            min_len = str(clamp_int(args.get("min_length", 6), default=6, minimum=1, maximum=1024))
            out = await run_cmd("strings", "-t", "x", "-n", min_len, path)
            pattern = args.get("filter_pattern", "")
            if pattern:
                lines = [ln for ln in out.splitlines() if pattern.lower() in ln.lower()]
                return "\n".join(lines) or f"(no strings matching '{pattern}')"
            return out
        finally:
            if is_temp:
                os.unlink(path)

    return f"[error] unknown forensics tool: {name}"
