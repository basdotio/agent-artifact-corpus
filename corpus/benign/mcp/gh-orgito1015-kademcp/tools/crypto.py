"""
Crypto tools:
  - decode_encode   : base64, hex, rot13, url, binary, morse
  - hash_identify   : guess hash type from its length/pattern
  - hash_crack      : crack hash with rockyou wordlist via hashcat/john
  - run_crypto      : run arbitrary Python crypto code (pycryptodome available)
  - xor_bruteforce  : single-byte and multi-byte XOR brute-force
  - frequency_analysis : letter frequency analysis for classical ciphers
"""

import base64
import os
import string
import urllib.parse

from mcp.types import Tool

from tools.utils import decode_input, run_cmd, run_python, write_tempfile

crypto_tools = [
    Tool(
        name="decode_encode",
        description=(
            "Encode or decode data using a named scheme. "
            "Schemes: base64, base64url, hex, rot13, url, binary, morse, ascii. "
            "Direction: encode | decode (default: decode)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Input data (string or hex prefixed with 0x)"},
                "scheme": {"type": "string", "description": "Encoding scheme"},
                "direction": {"type": "string", "enum": ["encode", "decode"], "default": "decode"},
            },
            "required": ["data", "scheme"],
        },
    ),
    Tool(
        name="hash_identify",
        description="Identify a hash type by its length and character set.",
        inputSchema={
            "type": "object",
            "properties": {
                "hash_value": {"type": "string"},
            },
            "required": ["hash_value"],
        },
    ),
    Tool(
        name="hash_crack",
        description=(
            "Attempt to crack a hash using hashcat with rockyou (john fallback). "
            "Modes: md5, sha1, sha256, sha512, ntlm. Mode is auto-detected only for "
            "unambiguous lengths (40=sha1, 64=sha256, 128=sha512); for length-32 "
            "(MD5 vs NTLM) or anything else you must pass `mode` explicitly."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "hash_value": {"type": "string"},
                "mode": {
                    "type": "string",
                    "enum": ["md5", "sha1", "sha256", "sha512", "ntlm"],
                    "description": "Hash mode; required when the length is ambiguous or unrecognized",
                },
            },
            "required": ["hash_value"],
        },
    ),
    Tool(
        name="xor_bruteforce",
        description=(
            "XOR brute-force. For single-byte XOR, tries all 256 keys and ranks by English frequency. "
            "For known key, XORs data with that key (repeating). "
            "Input as hex (0x...) or raw string."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Ciphertext as hex (0x...) or raw"},
                "key": {"type": "string", "description": "Known key (leave empty to brute-force single-byte)"},
                "top_n": {"type": "integer", "description": "Show top N single-byte results (default: 5)"},
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="frequency_analysis",
        description="Letter frequency analysis for classical cipher cracking (Caesar, Vigenère, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "ciphertext": {"type": "string"},
                "top_n": {"type": "integer", "description": "How many top letters to show (default: 10)"},
            },
            "required": ["ciphertext"],
        },
    ),
    Tool(
        name="run_crypto",
        description=(
            "Run arbitrary Python crypto code. pycryptodome (Crypto.*), gmpy2, sympy are available. "
            "Print results; they are returned as output."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
            },
            "required": ["code"],
        },
    ),
]

# Morse code table
MORSE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z", "-----": "0", ".----": "1", "..---": "2", "...--": "3",
    "....-": "4", ".....": "5", "-....": "6", "--...": "7", "---..": "8",
    "----.": "9",
}
MORSE_ENC = {v: k for k, v in MORSE.items()}

# Length-only identification is inherently ambiguous: many algorithms share a
# digest length. NTLM is MD4-based and is 32 hex chars, the same length as MD5.
HASH_SIGNATURES = [
    (32,  "MD5 or NTLM"),
    (40,  "SHA1"),
    (56,  "SHA224"),
    (64,  "SHA256"),
    (96,  "SHA384"),
    (128, "SHA512"),
]

HASHCAT_MODES = {
    "md5": "0", "sha1": "100", "sha256": "1400",
    "sha512": "1700", "ntlm": "1000",
}

JOHN_FORMATS = {
    "md5": "Raw-MD5", "sha1": "Raw-SHA1", "sha256": "Raw-SHA256",
    "sha512": "Raw-SHA512", "ntlm": "NT",
}
# Only unambiguous digest lengths auto-map. Length 32 (MD5 vs NTLM) is
# intentionally omitted so hash_crack refuses to guess between them.
LENGTH_TO_MODE = {40: "sha1", 64: "sha256", 128: "sha512"}

ENGLISH_FREQ = "etaoinshrdlcumwfgypbvkjxqz"


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def _score_english(text: bytes) -> float:
    try:
        s = text.decode(errors="replace").lower()
    except Exception:
        return 0.0
    score = 0.0
    for ch in s:
        pos = ENGLISH_FREQ.find(ch)
        if pos != -1:
            score += len(ENGLISH_FREQ) - pos
    return score


async def handle_crypto(name: str, args: dict) -> str:
    if name == "decode_encode":
        data = args["data"]
        scheme = args["scheme"].lower()
        direction = args.get("direction", "decode")

        try:
            if scheme == "base64":
                if direction == "decode":
                    cleaned = "".join(data.split())
                    cleaned += "=" * (-len(cleaned) % 4)
                    # validate=True rejects out-of-alphabet chars instead of
                    # silently discarding them and returning garbage.
                    return base64.b64decode(cleaned, validate=True).decode(errors="replace")
                return base64.b64encode(data.encode()).decode()

            if scheme == "base64url":
                if direction == "decode":
                    cleaned = "".join(data.split())
                    cleaned += "=" * (-len(cleaned) % 4)
                    # Translate the URL-safe alphabet back to standard so we can
                    # decode with validate=True (urlsafe_b64decode has no validate).
                    std = cleaned.translate(str.maketrans("-_", "+/"))
                    return base64.b64decode(std, validate=True).decode(errors="replace")
                return base64.urlsafe_b64encode(data.encode()).decode()

            if scheme == "hex":
                raw = data.replace(" ", "").replace("0x", "")
                if direction == "decode":
                    return bytes.fromhex(raw).decode(errors="replace")
                return data.encode().hex()

            if scheme == "rot13":
                return data.translate(str.maketrans(
                    string.ascii_uppercase + string.ascii_lowercase,
                    string.ascii_uppercase[13:] + string.ascii_uppercase[:13] +
                    string.ascii_lowercase[13:] + string.ascii_lowercase[:13],
                ))

            if scheme == "url":
                if direction == "decode":
                    return urllib.parse.unquote(data)
                return urllib.parse.quote(data)

            if scheme == "binary":
                if direction == "decode":
                    groups = data.split()
                    return "".join(chr(int(g, 2)) for g in groups)
                return " ".join(f"{ord(c):08b}" for c in data)

            if scheme == "morse":
                if direction == "decode":
                    # Words are separated by "/"; letters within a word by spaces.
                    words = data.strip().split("/")
                    decoded_words = [
                        "".join(MORSE.get(tok, "?") for tok in word.split())
                        for word in words
                    ]
                    return " ".join(decoded_words)
                # Encode: split on any whitespace run into words so multiple or
                # mixed spaces collapse to a single "/" word separator; letters
                # within a word are space-separated morse tokens.
                words = data.split()
                encoded_words = [
                    " ".join(MORSE_ENC.get(c.upper(), "?") for c in word)
                    for word in words
                ]
                return " / ".join(encoded_words)

            if scheme == "ascii":
                if direction == "decode":
                    nums = [int(x) for x in data.replace(",", " ").split()]
                    return "".join(chr(n) for n in nums)
                return " ".join(str(ord(c)) for c in data)

            return f"[error] unknown scheme: {scheme}"
        except Exception as e:
            return f"[error] {e}"

    if name == "hash_identify":
        h = args["hash_value"].strip()
        length = len(h)
        candidates = [sig for ln, sig in HASH_SIGNATURES if ln == length]
        colon = h.find(":")
        hints = []
        if colon != -1:
            hints.append("Contains ':' — may be salted or username:hash format")
        if h.startswith("$"):
            hints.append("Starts with '$' — likely crypt / bcrypt / scrypt format")
        result = f"Hash: {h}\nLength: {length}\n"
        result += f"Likely type: {', '.join(candidates) if candidates else 'unknown'}\n"
        result += "Note: this is length-only identification and is ambiguous — "
        result += "several algorithms produce the same digest length.\n"
        if hints:
            result += "\n".join(hints)
        return result

    if name == "hash_crack":
        h = args["hash_value"].strip()
        explicit_mode = (args.get("mode") or "").strip().lower()

        if explicit_mode:
            # Reject unsupported modes (e.g. "bcrypt") instead of silently
            # cracking as MD5 (hashcat mode 0).
            if explicit_mode not in HASHCAT_MODES:
                supported = ", ".join(sorted(HASHCAT_MODES))
                return f"[error] unsupported mode '{explicit_mode}'. Supported: {supported}."
            mode_name = explicit_mode
        else:
            # Auto-detect by length only when it maps to a single algorithm.
            mode_name = LENGTH_TO_MODE.get(len(h), "")
            if not mode_name:
                hint = " (length 32 is ambiguous: MD5 or NTLM)" if len(h) == 32 else ""
                supported = ", ".join(sorted(HASHCAT_MODES))
                return (
                    f"[error] could not determine hash mode{hint}; refusing to guess. "
                    f"Pass `mode` explicitly. Supported: {supported}."
                )
        hc_mode = HASHCAT_MODES[mode_name]

        wordlist = "/usr/share/wordlists/rockyou.txt"
        # Both hashcat and john need the wordlist file. Check up front so a
        # missing wordlist isn't mis-attributed to a missing binary.
        if not os.path.exists(wordlist):
            return (
                f"[error] wordlist not found at {wordlist}. "
                "Both hashcat and john require this file to crack the hash; "
                "provision it (e.g. rockyou.txt) before running hash_crack."
            )

        result = await run_cmd(
            "hashcat", "-m", hc_mode, "-a", "0", "--quiet",
            "--potfile-disable", h, wordlist,
        )
        if "[error] tool not found" in result:
            # fallback to john: it needs the hash in a file, not on stdin
            hash_file = write_tempfile(h.encode(), suffix=".hash")
            try:
                john_args = ["john", "--wordlist=" + wordlist]
                john_format = JOHN_FORMATS.get(mode_name)
                if john_format:
                    john_args.append(f"--format={john_format}")
                john_args.append(hash_file)
                result = await run_cmd(*john_args)
                shown = await run_cmd("john", "--show", hash_file)
                if shown and "0 password hashes cracked" not in shown:
                    result += f"\n\n{shown}"
            finally:
                os.unlink(hash_file)
        return result or "[no crack found]"

    if name == "xor_bruteforce":
        raw = decode_input(args["data"])
        key_str = args.get("key", "")

        if key_str:
            # Known keys are almost always typed literally (e.g. "flag"),
            # so don't auto-reinterpret hex-looking keys unless "0x"-prefixed.
            key = decode_input(key_str, assume_hex=False)
            decrypted = _xor_bytes(raw, key)
            return decrypted.decode(errors="replace")

        # single-byte brute-force
        top_n = args.get("top_n", 5)
        results = []
        for k in range(256):
            decrypted = _xor_bytes(raw, bytes([k]))
            score = _score_english(decrypted)
            results.append((score, k, decrypted))
        results.sort(reverse=True)
        lines = [f"Top {top_n} single-byte XOR keys by English frequency score:\n"]
        for score, k, dec in results[:top_n]:
            preview = dec.decode(errors="replace")[:80].replace("\n", " ")
            lines.append(f"  key=0x{k:02x} ({k:3d})  score={score:.0f}  {preview}")
        return "\n".join(lines)

    if name == "frequency_analysis":
        text = args["ciphertext"].upper()
        counts: dict[str, int] = {}
        total = 0
        for ch in text:
            if ch.isalpha():
                counts[ch] = counts.get(ch, 0) + 1
                total += 1
        if total == 0:
            return "[error] no alphabetic characters found"
        sorted_chars = sorted(counts.items(), key=lambda x: -x[1])
        top_n = args.get("top_n", 10)
        lines = [f"Frequency analysis (total letters: {total})\n",
                 f"{'Letter':<8} {'Count':<8} {'%':<8} {'Likely plaintext (if sub cipher)'}"]
        for i, (ch, cnt) in enumerate(sorted_chars[:top_n]):
            pct = cnt / total * 100
            hint = ENGLISH_FREQ[i].upper() if i < len(ENGLISH_FREQ) else "?"
            lines.append(f"  {ch:<8} {cnt:<8} {pct:<8.1f} → possibly '{hint}'")
        return "\n".join(lines)

    if name == "run_crypto":
        return await run_python(args["code"])

    return f"[error] unknown crypto tool: {name}"
