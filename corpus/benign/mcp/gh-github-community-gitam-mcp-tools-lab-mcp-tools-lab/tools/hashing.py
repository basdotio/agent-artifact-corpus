"""Content hashes; these are not password storage functions."""

import hashlib
from typing import Literal


def hash_text(text: str, algorithm: Literal["sha256", "sha512", "blake2b"] = "sha256") -> dict:
    """Hash UTF-8 text using SHA-256, SHA-512, or BLAKE2b; return lowercase hex."""
    algorithms = {"sha256": hashlib.sha256, "sha512": hashlib.sha512, "blake2b": hashlib.blake2b}
    if algorithm not in algorithms:
        raise ValueError("algorithm must be sha256, sha512, or blake2b.")
    return {"algorithm": algorithm, "digest": algorithms[algorithm](text.encode("utf-8")).hexdigest()}
