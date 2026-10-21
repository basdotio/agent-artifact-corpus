"""Import Suno auth cookies from the user's main Brave profile into storage_state.json.

macOS only: decrypts Brave's cookie DB with the "Brave Safe Storage" Keychain key.
Run: python -m suno_mcp.session.brave_import
"""

import hashlib
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from .store import SessionStore

BRAVE_COOKIES = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies"
DOMAINS = ("suno.com", "suno.ai")
EPOCH_DELTA = 11644473600  # seconds between 1601 (Chromium) and 1970 (Unix)
SAMESITE = {0: "None", 1: "Lax", 2: "Strict"}


def _key() -> bytes:
    pw = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", "Brave Safe Storage"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return hashlib.pbkdf2_hmac("sha1", pw.encode(), b"saltysalt", 1003, 16)


def _decrypt(blob: bytes, key: bytes, strip_hash: bool) -> str:
    if blob[:3] != b"v10":
        return blob.decode(errors="replace")
    out = subprocess.run(
        ["openssl", "enc", "-d", "-aes-128-cbc", "-K", key.hex(), "-iv", "20" * 16],
        input=blob[3:], capture_output=True, check=True,
    ).stdout
    return (out[32:] if strip_hash else out).decode()


def import_cookies() -> list[dict]:
    key = _key()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "Cookies"
        shutil.copy2(BRAVE_COOKIES, db)  # live DB is locked while Brave runs
        con = sqlite3.connect(db)
        version = int(con.execute("select value from meta where key='version'").fetchone()[0])
        where = " or ".join("host_key like ?" for _ in DOMAINS)
        rows = con.execute(
            f"select host_key,name,path,encrypted_value,value,expires_utc,is_secure,is_httponly,samesite "
            f"from cookies where {where}", [f"%{d}" for d in DOMAINS],
        ).fetchall()
        con.close()

    cookies = []
    for host, name, path, enc, plain, exp, secure, httponly, samesite in rows:
        value = _decrypt(enc, key, version >= 24) if enc else plain
        cookies.append({
            "name": name, "value": value, "domain": host, "path": path,
            "expires": exp / 1e6 - EPOCH_DELTA if exp else -1,
            "httpOnly": bool(httponly), "secure": bool(secure),
            "sameSite": SAMESITE.get(samesite, "Lax"),
        })
    return cookies


def main() -> None:
    cookies = import_cookies()
    SessionStore().save({"cookies": cookies, "origins": []})
    print(f"Imported {len(cookies)} Suno cookies: {sorted({c['name'] for c in cookies})}")


if __name__ == "__main__":
    main()
