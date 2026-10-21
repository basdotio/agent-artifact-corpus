"""Apply an operation's edit to the exact source it was computed from.

A suggest patch and a sorry2lemma transformation each name the SHA-256 of the
source they were computed from and of the source they produce. The edit is
applied only to those exact bytes, and the result must hash as promised, so a
stale or tampered result can never silently rewrite a different file.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .outcome import SUGGESTION_VERIFICATIONS

EDITING_KINDS = frozenset({"suggest", "sorry2lemma"})


class EditError(ValueError):
    """The result cannot be applied to this source."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def edited_sha256(kind: str, result: Mapping[str, Any]) -> object:
    """The checksum the result promises for the edited file."""
    return result.get("patched_source_sha256" if kind == "suggest" else "transformed_source_sha256")


def edited_source(kind: str, result: Mapping[str, Any], source: str) -> str:
    """The file after the edit; raises EditError unless every hash matches."""
    if kind not in EDITING_KINDS:
        raise EditError(f"{kind} results contain no edit to apply")
    if result.get("source_sha256") != _sha256(source):
        raise EditError("the file has changed since this result; run the operation again")
    if kind == "suggest":
        if (
            result.get("status") != "closed"
            or result.get("verification") not in SUGGESTION_VERIFICATIONS
        ):
            raise EditError("the suggestion closed no hole")
        patch = result.get("patch")
        start = patch.get("start_utf8_offset") if isinstance(patch, dict) else None
        end = patch.get("end_utf8_offset") if isinstance(patch, dict) else None
        replacement = patch.get("replacement") if isinstance(patch, dict) else None
        encoded = source.encode("utf-8")
        if (
            type(start) is not int
            or type(end) is not int
            or not isinstance(replacement, str)
            or not 0 <= start <= end <= len(encoded)
        ):
            raise EditError("the suggestion's patch is malformed")
        try:
            edited = (encoded[:start] + replacement.encode("utf-8") + encoded[end:]).decode()
        except UnicodeDecodeError:
            raise EditError("the suggestion's patch splits a character") from None
    else:
        if result.get("status") not in {"extracted", "partial"}:
            raise EditError("the extraction did not complete")
        if result.get("source_changed") is not True:
            raise EditError("the extraction left the file unchanged")
        transformed = result.get("transformed_source")
        if not isinstance(transformed, str):
            raise EditError("the extraction returned no transformed file")
        edited = transformed
    if _sha256(edited) != edited_sha256(kind, result):
        raise EditError("the edited file does not match the result's checksum")
    return edited
