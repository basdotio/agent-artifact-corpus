r"""File-path variants of the text tools: files are read locally, and returned
results can include summaries, selected source excerpts and extracted field values.

THREAT MODEL: the path is caller-supplied and the file is attacker-shaped.
Two different things are defended. Containment answers "may these bytes be
read at all"; the .docx screens answer "can reading them cost more than the
bytes suggest". Neither subsumes the other.

File reads are confined to explicitly configured roots. Set LOCAL_LLM_FILE_ROOTS (an OS-path-separator-delimited list) or the single-root LOCAL_LLM_FILE_ROOT before starting the server. With neither setting present, no file roots are granted.
Containment is TWO-TIER, and only the second tier authorizes anything. The
pre-open check is case-INSENSITIVE and exists to reject obvious misses
cheaply; it can be defeated by retargeting a name after it is checked. The
authority is a case-SENSITIVE check against the final path of the OPEN
HANDLE, which the OS already resolved, so it describes the object whose bytes
are about to be read rather than a name that may have moved.

Hard-linked files are REFUSED. A hard link is a second true name for one
inode, so no path-based check can tell whether another name for those bytes
lives outside the roots.

For a .docx, the member word/document.xml is refused if it declares a DTD --
that refusal is scoped to the member this module actually parses, not to the
archive. Archive members whose names end in .xml or .rels are screened on zip
metadata (compression method, declared size and compression ratio) before
anything is decompressed (only STORED and DEFLATED are accepted); other
members, such as embedded images, are neither screened nor opened.

Guardrails:
- Allowlist roots + realpath containment (junction-safe) before any read.
- Hard size cap; larger files are REJECTED with guidance (use a smaller file,
  split it, or grep/tail the relevant window), never silently sampled.
- Model pinned per-call (default qwen2.5:7b, LOCAL_LLM_FILE_MODEL) so a change
  to the text tools' default model can never swap-thrash against a model kept
  resident for the background triage loop.
- Mechanical grounding: line/byte counts and "notable lines" are computed by
  CODE (severity regex, quoted byte-verbatim with line numbers); the model
  contributes prose only, labeled UNVERIFIED-DIGEST.
- extract_json_file: every string and number in an extracted value must occur
  as a substring of the normalized source text or the field is NULLED and
  listed in unverified_fields. This is a presence check only: it does not show
  that a value is correct, complete or under the right field (see the
  extract_json_file docstring for its limits). Booleans and nulls are not
  checked against the source.
- Wall-time budget with LOUD partial coverage labeling (no silent caps).
"""

import ctypes
import io
import msvcrt
import os
import re
import stat
import sys
import time
from ctypes import wintypes

from local_llm.docx_text import extract_text as _docx_extract_text
from local_llm.extract import extract_json
from local_llm.ollama_client import OllamaError, generate

MAX_FILE_BYTES = int(os.environ.get("LOCAL_LLM_FILE_MAX_BYTES", "384000"))
FILE_MODEL = os.environ.get("LOCAL_LLM_FILE_MODEL", "qwen2.5:7b")
CHUNK_CHARS = 12000          # same as the triage loop's per-call batch size
TIME_BUDGET_SECONDS = float(os.environ.get("LOCAL_LLM_FILE_BUDGET_SECONDS", "170"))
NOTABLE_CAP = 20

_LABEL = ("UNVERIFIED-DIGEST (local %s): verify any number used in a decision "
          "against the source file")

_NOTABLE_RE = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Traceback|FAILED|FAIL|WARNING|WARN|Exception)\b")

_NORM_RE = re.compile(r"[\s,$]")


# Public installs grant no implicit file access; configured roots are parsed
# from LOCAL_LLM_FILE_ROOTS or the single-root LOCAL_LLM_FILE_ROOT setting.
_DEFAULT_ROOTS = ()


def _commonpath_form(path):
    r"""Normalize a path for commonpath comparison.

    A bare UNC share root has an empty tail after splitdrive,
    which ntpath classifies as RELATIVE; mixing it with an absolute descendant
    makes commonpath raise ValueError, which would reject every file under a
    UNC root. Appending the separator makes the share itself absolute.
    """
    normalized = os.path.normcase(os.path.normpath(path))
    drive, tail = os.path.splitdrive(normalized)
    if drive.startswith("\\\\") and not tail:
        normalized += os.sep
    return normalized


def _is_within(candidate, root):
    """CHEAP PRE-OPEN FILTER -- case-insensitive, deliberately over-permissive,
    and NEVER authorization.

    It exists to reject the obvious misses cheaply before anything is opened.
    It MAY admit a path that the authoritative check (_is_within_exact, run on
    the handle's resolved path) then rejects -- on a case-sensitive directory
    it cannot distinguish paths that differ only in letter case, because
    ntpath.commonpath folds case internally. That is a known and accepted
    property of THIS function; do not "fix" it here. Fixing it here would not
    close the escape either, since the fold happens inside commonpath.

    Uses commonpath (not a string prefix) so a drive root cannot
    double-separators and sibling prefixes must not match a configured
    workspace root. Cross-volume comparison fails closed.
    """
    candidate_form = _commonpath_form(candidate)
    root_form = _commonpath_form(root)
    try:
        common = os.path.commonpath([root_form, candidate_form])
    except ValueError:
        return False
    return os.path.normpath(common) == os.path.normpath(root_form)


def _is_within_exact(candidate, root):
    r"""AUTHORITATIVE containment -- case-SENSITIVE.

    PRECONDITION: both arguments must ALREADY be normalized by the OS to their
    true on-disk case, by os.path.realpath (verified: restores true case,
    uppercases the drive letter, expands 8.3 aliases) or by
    GetFinalPathNameByHandleW with FILE_NAME_NORMALIZED. Do NOT call this on a
    caller-supplied string: measured, _is_within_exact(r"c:\a\x.txt", r"C:\a")
    is False, so a raw lowercase spelling of a legitimate path would be
    denied. That direction is fail-closed rather than a hole, but it is a bug
    in the caller.

    commonpath cannot be used here. ntpath.commonpath lowercases both sides
    internally (it builds drivesplits = [splitroot(p.replace(altsep,
    sep).lower()) for p in paths]) and only the RETURNED value keeps original
    case, so removing os.path.normcase from the caller does not fix anything.
    commonpath has to be abandoned for this check, not fed different input.

    The trailing-separator strip is what keeps a drive root (C:\) from
    double-separating. An EMPTY normalized root is rejected rather than
    treated as a prefix: "\\".rstrip("\\") is "", and "" + "\\" prefixes every
    UNC path, which would silently admit the whole network.
    """
    cand = os.path.normpath(candidate).rstrip("\\")
    rt = os.path.normpath(root).rstrip("\\")
    if not rt:
        return False
    if cand == rt:
        return True
    return cand.startswith(rt + "\\")


def _same_directory(first, second):
    """True only for TRUE filesystem aliases (same device+inode).

    This is what replaced a case-folding dedupe. os.path.normcase would call
    ...\\Root and ...\\root the same directory; on a case-sensitive directory
    they are not, and folding them discards an explicitly configured root.
    samefile compares the objects, so it still collapses a junction alias to
    its target while leaving two genuinely different directories alone.

    os.path.samefile can raise if a root becomes inaccessible between the isdir
    check and here; treating that as "not the same" keeps both entries, which
    is the conservative choice for REACHABILITY. It cannot widen the boundary:
    containment is decided separately, per read.
    """
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def _parse_roots(roots_var, legacy_var):
    """Resolve the configured allowlist roots.

    ENVIRONMENT-DECOUPLED, not pure: this reads the filesystem (realpath,
    isdir, samefile) and writes warnings to stderr. What it does not do is read
    os.environ -- env values arrive as arguments, so tests never reload the
    module inside a patch context.

    Precedence: LOCAL_LLM_FILE_ROOTS (os.pathsep list) > LOCAL_LLM_FILE_ROOT
    (one EXACT root, never split) > _DEFAULT_ROOTS.

    PRECEDENCE IS DECIDED BY PRESENCE, NOT BY WHETHER THE WINNER SURVIVED
    VALIDATION. The `is not None` chain below picks exactly ONE source and
    never revisits that choice. So a PRESENT LOCAL_LLM_FILE_ROOTS fails CLOSED
    (zero roots -- every call then errors loudly) whether it is blank OR wholly
    invalid, and in neither case does it fall through to the legacy var or the
    defaults; likewise a present-but-invalid legacy var yields zero roots
    rather than the defaults. This is the single most dangerous thing to "fix"
    later: re-consulting the lower-precedence source once validation empties
    the list would silently restore roots the operator explicitly overrode --
    widening the boundary at the exact moment the configuration is known bad.
    Pinned by test_invalid_roots_var_does_NOT_fall_back_to_a_valid_legacy_root
    and test_invalid_legacy_root_does_NOT_fall_back_to_the_defaults.

    Relative or nonexistent entries are dropped with a stderr warning. Entries
    are realpath-canonicalized, which is also what makes them safe to hand to
    _is_within_exact.

    Deduplication is by _same_directory, NOT by os.path.normcase, and nesting
    collapses with the case-EXACT predicate. Both details are the same point:
    on a case-sensitive directory two roots differing only in case are two
    directories, and folding either comparison silently discards one of them.
    Measured: normcase dedup kept 1 of 2; samefile dedup with a permissive
    collapse still kept 1 of 2. Both had to change.
    """
    if roots_var is not None:
        raw_entries = roots_var.split(os.pathsep)
    elif legacy_var is not None:
        raw_entries = [legacy_var]          # EXACT single root, never split
    else:
        raw_entries = list(_DEFAULT_ROOTS)

    resolved = []
    for entry in raw_entries:
        entry = entry.strip()
        if not entry:
            continue
        if not os.path.isabs(entry):
            # %s, NOT %r: repr() doubles backslashes, so a warning about
            # relative\path would print relative\\path and no test (or human)
            # searching for the literal entry would find it. The sibling
            # warning below uses %s for the same reason.
            sys.stderr.write(
                "local-llm file_tools: dropping relative allowlist root %s "
                "(roots must be absolute)\n" % entry)
            continue
        real = os.path.realpath(entry)
        # isdir, NOT exists: a regular FILE must never become a root.
        # Containment is pure string logic and never asks what kind of object
        # a root is, so a file root would admit every sibling path sharing its
        # name as a prefix. Pinned by
        # test_an_existing_regular_file_as_a_root_is_rejected.
        if not os.path.isdir(real):
            # Wording covers BOTH rejected cases. The old text said
            # "nonexistent", which is simply false for a file that exists and
            # would send a reader hunting for a missing directory.
            sys.stderr.write(
                "local-llm file_tools: dropping allowlist root %s "
                "(not an existing directory)\n" % entry)
            continue
        resolved.append(real)

    unique = []
    for real in resolved:
        if not any(_same_directory(real, kept) for kept in unique):
            unique.append(real)

    # Shortest first, so an ancestor is always kept before its descendants and
    # each descendant then collapses into it.
    kept = []
    for real in sorted(unique, key=len):
        if not any(_is_within_exact(real, existing) for existing in kept):
            kept.append(real)
    return sorted(kept, key=unique.index)


_ROOTS = _parse_roots(os.environ.get("LOCAL_LLM_FILE_ROOTS"),
                      os.environ.get("LOCAL_LLM_FILE_ROOT"))


_NO_ROOTS = ("no usable allowlist roots are configured; LOCAL_LLM_FILE_ROOTS "
             "may be blank, or every configured root may be invalid or "
             "nonexistent -- every file read is refused until it is fixed")


def _assert_contained(real_path):
    """CHEAP PRE-OPEN CHECK. Raise unless real_path sits inside one of the
    configured roots, comparing case-INSENSITIVELY.

    real_path MUST already be canonicalized by the caller. Note carefully what
    this can and cannot do. It authorizes NOTHING. It is an early reject on a
    PATH STRING: it cannot know whether that string still names the same
    object by the time anything opens it (that is what the handle check is
    for), and being case-insensitive it will admit a path on a case-sensitive
    directory that _assert_contained_exact then rejects. Both gaps are closed
    by _assert_contained_exact on the opened handle.
    """
    if not _ROOTS:
        raise ValueError(_NO_ROOTS)
    if any(_is_within(real_path, root) for root in _ROOTS):
        return
    raise ValueError(
        "path is outside the allowed roots (" + os.pathsep.join(_ROOTS)
        + "): " + real_path)


def _assert_contained_exact(final_path):
    """AUTHORITATIVE CHECK, case-SENSITIVE.

    Call this ONLY with a path the OS itself resolved -- the final path of an
    open handle -- so the case-exact comparison is made against the object's
    true on-disk name. See _is_within_exact's precondition.

    The message deliberately differs from _assert_contained's. A case-fold
    escape PASSES the cheap filter and is caught only here, so a test that
    could not tell the two apart could not prove this check is wired in at
    all. Do not unify the wording.
    """
    if not _ROOTS:
        raise ValueError(_NO_ROOTS)
    if any(_is_within_exact(final_path, root) for root in _ROOTS):
        return
    raise ValueError(
        "path is outside the allowed roots (case-exact handle check) ("
        + os.pathsep.join(_ROOTS) + "): " + final_path)


_DOS_DEVICE_PREFIX = "\\\\?\\"              # the 4-char sequence \\?\
_DOS_DEVICE_UNC_PREFIX = "\\\\?\\UNC\\"     # the 8-char sequence \\?\UNC\

_GetFinalPathNameByHandleW = ctypes.windll.kernel32.GetFinalPathNameByHandleW
_GetFinalPathNameByHandleW.restype = wintypes.DWORD
_GetFinalPathNameByHandleW.argtypes = (
    wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)

_FINAL_PATH_BUFFER = 32768


def _handle_final_path(handle):
    r"""Canonical Windows path of the object an OPEN HANDLE refers to.

    This is the one question that cannot be raced: the resolution already
    happened when the OS opened the handle, so the answer describes the object
    whose bytes are about to be read -- not a name that may have been
    retargeted since it was authorized. The result is also OS-normalized to
    true on-disk case, which is what makes it safe to hand to
    _assert_contained_exact.

    It must ask the OS about the HANDLE. Re-resolving handle.name is NOT an
    acceptable implementation: measured, a name-based version AUTHORIZES a read
    whose bytes came from outside the roots once the swapped-in directory is
    restored before this call. The regression that separates the two is
    test_handle_authorization_survives_the_directory_being_restored.

    Demonstrated coverage (tested): directory junctions, file symlinks, and
    directory symlinks, including a junction swapped in after authorization and
    swapped back out before this call. NOT demonstrated: volume mount points,
    subst drives, and remote SMB behavior. Do not describe this as resolving
    "every reparse point".

    Returns an ordinary path: the \\?\ device prefix is stripped, and the
    extended UNC form is restored to its ordinary network-path shape. Stripping only the
    4-character prefix from a UNC result would yield UNC\server\share\...,
    an invalid path that would reject every read under a UNC root.
    """
    raw = msvcrt.get_osfhandle(handle.fileno())
    buffer = ctypes.create_unicode_buffer(_FINAL_PATH_BUFFER)
    # flags=0 is FILE_NAME_NORMALIZED | VOLUME_NAME_DOS.
    length = _GetFinalPathNameByHandleW(
        wintypes.HANDLE(raw), buffer, _FINAL_PATH_BUFFER, 0)
    if length == 0:
        raise ValueError("could not resolve the opened handle to a path")
    if length >= _FINAL_PATH_BUFFER:
        # Buffer too small: the API returns the REQUIRED size and writes
        # nothing. Fail closed rather than validate a truncated path.
        raise ValueError("resolved path is too long to validate safely")
    value = buffer.value
    if value.startswith(_DOS_DEVICE_UNC_PREFIX):
        return "\\\\" + value[len(_DOS_DEVICE_UNC_PREFIX):]
    if value.startswith(_DOS_DEVICE_PREFIX):
        return value[len(_DOS_DEVICE_PREFIX):]
    return value


def _open_contained(path):
    """Resolve, open ONCE, then authorize the object the HANDLE refers to.

    Order matters. The pre-open _assert_contained is a cheap early reject, NOT
    the authorization: a name can be retargeted after it is checked, and the
    cheap check is case-insensitive. The AUTHORITATIVE check is
    _assert_contained_exact(_handle_final_path(handle)), because the handle
    already refers to a resolved object and its final path carries true
    on-disk case.

    Returns (final_path, open_binary_handle, size) -- the HANDLE's path, not
    the requested name. Everything downstream (the .docx routing decision, the
    reported "path") must use it, or the tools would attribute bytes to an
    object they did not come from. The caller closes the handle.
    """
    real = os.path.realpath(str(path))
    _assert_contained(real)          # cheap early reject, NOT authoritative

    try:
        pre = os.stat(real)
    except OSError as exc:
        raise ValueError("not a file: " + real + " (" + str(exc) + ")")
    if not stat.S_ISREG(pre.st_mode):
        raise ValueError("not a file: " + real)

    # EVERY OS call in this function must fail in the DECLARED type. os.stat
    # above is already converted and the ctypes resolution below has its own
    # guard, but open() sat outside every handler and the BaseException guard
    # re-raises the ORIGINAL type, so an fstat failure escaped as OSError too.
    # Both are routine against this module's primary use case -- a live worker
    # log that another process holds open (sharing violation) or an ACL denial.
    try:
        handle = open(real, "rb")
    except OSError as exc:
        raise ValueError("could not open: " + real + " (" + str(exc) + ")")
    try:
        post = os.fstat(handle.fileno())
        if not stat.S_ISREG(post.st_mode):
            raise ValueError("not a file: " + real)
        # IDENTITY is (device, inode) -- NOT size. A size change is not a
        # change of object, it is growth, and growth is explicitly accepted
        # here: the primary use case is reading a live worker log, which gains
        # lines constantly. Including st_size would reject any append that
        # landed between os.stat and os.fstat, making that use case
        # intermittently flaky for no security gain -- the cap is enforced
        # separately on post.st_size below and again by _read_bounded.
        if ((post.st_dev, post.st_ino) != (pre.st_dev, pre.st_ino)):
            raise ValueError(
                "file changed between resolve and open (identity mismatch): "
                + real)
        if post.st_nlink > 1:
            raise ValueError(
                "refusing a hard-linked file (%d links): a hard link is a "
                "second true name for one inode, so no path-based containment "
                "check can tell whether another name for these bytes lives "
                "outside the allowed roots. Copy the file into an allowed "
                "root, or grep it directly: %s" % (post.st_nlink, real))
        # AUTHORITATIVE: validate what was actually opened, case-exactly.
        try:
            final = _handle_final_path(handle)
        except OSError as exc:
            # FAIL CLOSED, IN THE DECLARED TYPE. _handle_final_path already
            # raises ValueError for a zero-length or over-long result, but the
            # ctypes call itself can fail with OSError, and every public entry
            # point in this module promises ValueError -- an OSError escaping
            # here surfaces a type no caller handles, on the one path where
            # the object's identity could not be established. The handle is
            # still closed by the enclosing BaseException guard.
            raise ValueError(
                "could not resolve the opened handle to a path: %s" % exc)
        _assert_contained_exact(final)
        if post.st_size > MAX_FILE_BYTES:
            # Names the OPENED object: by this point `final` is the only
            # identifier known to describe the bytes in question.
            raise ValueError(
                "file too large (%d bytes > %d cap): %s. Large files are out "
                "of scope by design -- use a smaller file or split it, or "
                "grep/tail the relevant window instead."
                % (post.st_size, MAX_FILE_BYTES, final))
    except OSError as exc:
        # Ordered BEFORE the BaseException guard, which re-raises the ORIGINAL
        # type. Anything in the block above that fails at the OS layer -- fstat
        # today, and any neighbour added later -- lands here in the declared
        # type instead of escaping. The handle is still closed on this path.
        handle.close()
        raise ValueError(
            "could not authorize the opened file: " + real
            + " (" + str(exc) + ")")
    except BaseException:
        handle.close()
        raise
    return final, handle, post.st_size


def _read_bounded(handle, cap):
    """Read at most cap + 1 bytes from an ALREADY-OPEN handle. More than cap
    means the file grew past the cap after its size was checked -- reject,
    never truncate silently."""
    payload = handle.read(cap + 1)
    if len(payload) > cap:
        raise ValueError(
            "file grew past the %d byte cap while it was being read" % cap)
    return payload


def _read_text(final_path, handle):
    """Bounded-read FIRST, always. Returns (text, byte_count).

    final_path is the HANDLE's resolved path, never the requested name: the
    .docx decision is a type decision about the object being read, and making
    it from a caller-supplied name after handle authorization would reintroduce
    exactly the name/object split the handle check exists to remove.

    The count is what was ACTUALLY read, not the pre-read fstat size: sub-cap
    growth is accepted (an active worker log gains lines constantly), so the
    earlier size goes stale and reporting it would be internally inconsistent
    with the text returned alongside it.

    A .docx gets a BytesIO view of those same bounded bytes -- handing zipfile
    the raw handle would let the outer archive escape MAX_FILE_BYTES even
    though every inner member is capped. Both the byte cap and the extracted
    TEXT cap are passed down; docx_text defaults would otherwise apply a bound
    this module did not choose.
    """
    payload = _read_bounded(handle, MAX_FILE_BYTES)
    if final_path.lower().endswith(".docx"):
        text = _docx_extract_text(io.BytesIO(payload), max_bytes=MAX_FILE_BYTES,
                                  max_text_chars=MAX_FILE_BYTES)
        if not text.strip():
            # A real file that yields nothing is not a read of its content.
            # Returning "" would let summarize_file report lines=0 with
            # coverage FULL. Only the body of word/document.xml is read, so a
            # document of images, headers, footers or notes ends up here.
            raise ValueError(
                "the .docx has no extractable text in the body of "
                "word/document.xml (images, headers, footers, footnotes and "
                "comments are not read): " + final_path)
    else:
        text = payload.decode("utf-8", errors="replace")
    return text, len(payload)


def _chunk_on_lines(text):
    """Split into <= CHUNK_CHARS chunks on line boundaries (a single over-long
    line becomes its own oversized chunk rather than being split mid-line)."""
    chunks, current, current_len = [], [], 0
    for line in text.splitlines(keepends=True):
        if current and current_len + len(line) > CHUNK_CHARS:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


def _notable_lines(text):
    """Code-grepped severity lines with 1-based line numbers. Deterministic --
    the model has no hand in these quotes. Lines longer than 400 chars carry an
    EXPLICIT truncation marker (never a silent cut posing as verbatim)."""
    notable = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _NOTABLE_RE.search(line):
            quoted = line
            if len(line) > 400:
                quoted = line[:400] + " ...[TRUNCATED: read line %d]" % lineno
            notable.append({"line_number": lineno, "line": quoted})
            if len(notable) >= NOTABLE_CAP:
                notable.append({
                    "line_number": None,
                    "line": "... notable-line cap (%d) reached; grep the file "
                            "for the rest" % NOTABLE_CAP})
                break
    return notable


def _norm(value):
    return _NORM_RE.sub("", str(value).lower())


def _value_verifies(value, source_norm):
    """True when every scalar inside `value` (recursing through lists/dicts)
    appears verbatim (normalized) in the source. Booleans and None verify by
    definition: a bool is the model's CLASSIFICATION, not a figure copied from
    the text -- the threat model here is invented figures. Any string/number
    miss ANYWHERE in a nested structure fails the whole field."""
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, (str, int, float)):
        value_norm = _norm(value)
        return not value_norm or value_norm in source_norm
    if isinstance(value, list):
        return all(_value_verifies(item, source_norm) for item in value)
    if isinstance(value, dict):
        return all(_value_verifies(item, source_norm) for item in value.values())
    return False


def summarize_file(path: str, max_words: int = 200) -> dict:
    r"""Summarize a file ON-BOX and return a digest with selected source excerpts.
    The returned summary and excerpts can contain source text.

    Reads are confined to explicitly configured roots:

        Access is limited to roots explicitly configured by the operator.

    Hard cap 384 KB; larger files are rejected with guidance (use grep/tail
    instead). Hard-linked files are refused outright -- a hard link is a
    second true name for one inode, so no path-based containment check can
    tell whether another name for those bytes lives outside the roots.

    The summary prose is model-generated and labeled UNVERIFIED-DIGEST;
    line/byte counts and notable_lines (severity-regex hits, quoted verbatim
    with line numbers) are computed by code. coverage is FULL, or a LOUD
    PARTIAL marker when the wall-time budget cut processing short.
    """
    if max_words <= 0:
        raise ValueError("max_words must be a positive integer, got " + str(max_words))
    final, handle, _size = _open_contained(path)
    try:
        text, nbytes = _read_text(final, handle)
    finally:
        handle.close()
    lines_total = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    chunks = _chunk_on_lines(text) or [""]

    deadline = time.monotonic() + TIME_BUDGET_SECONDS
    per_chunk_words = max(60, max_words // len(chunks)) if len(chunks) > 1 else max_words
    partials = []
    for chunk in chunks:
        if time.monotonic() > deadline:
            break
        prompt = (
            "Summarize the following text in at most " + str(per_chunk_words)
            + " words. Preserve numbers, dates, and identifiers exactly as "
            "written. Return ONLY the summary, no preamble.\n\nText:\n" + chunk)
        partials.append(generate(prompt, model=FILE_MODEL).strip())

    covered = len(partials)
    if covered == 0:
        raise OllamaError("time budget exhausted before the first chunk completed")

    if covered == 1:
        summary = partials[0]
    else:
        reduce_prompt = (
            "The following are ordered partial summaries of consecutive "
            "sections of one document. Merge them into a single coherent "
            "summary of at most " + str(max_words) + " words. Preserve numbers, "
            "dates, and identifiers exactly as written. Return ONLY the "
            "summary.\n\n" + "\n\n".join(partials))
        summary = generate(reduce_prompt, model=FILE_MODEL).strip()

    if not summary:
        raise OllamaError("model returned an empty summary for " + final)

    coverage = "FULL"
    if covered < len(chunks):
        coverage = ("PARTIAL: first %d of %d chunks only (time budget hit); "
                    "the file tail is NOT covered -- grep/tail it directly"
                    % (covered, len(chunks)))

    return {
        "label": _LABEL % FILE_MODEL,
        "path": final,
        "bytes": nbytes,
        "lines": lines_total,
        "chunks_total": len(chunks),
        "coverage": coverage,
        "summary": summary,
        "notable_lines": _notable_lines(text),
    }


def extract_json_file(path: str, schema: dict) -> dict:
    r"""Extract schema fields from a file ON-BOX.
    Returned field values can contain source content.

    Reads are confined to explicitly configured roots:

        Access is limited to roots explicitly configured by the operator.

    Hard cap 384 KB; larger files are rejected with guidance (use grep/tail
    instead). Hard-linked files are refused outright -- a hard link is a
    second true name for one inode, so no path-based containment check can
    tell whether another name for those bytes lives outside the roots.

    Plus a single-chunk text cap (12000 chars) -- multi-chunk extraction
    compounds hallucination and is out of scope by design. The model is asked
    once, with at most one validation retry (extract_json's two attempts).
    Strings and numbers get a substring-presence check: each one in a field's
    value (including inside lists and dicts) must occur, after normalization
    (case/whitespace/commas/$ stripped), as a substring of the normalized
    source text; a field where one does not is NULLED and listed in
    unverified_fields. This catches a value that appears nowhere in the file.
    It does NOT prove the value is right: a short value can match inside a
    longer one (12 passes against "Total 1200"), an empty or whitespace-only
    string passes, a value can come from the wrong place in the file and sit
    under the wrong field, dict KEYS are not checked, and a number the model
    reformats (1200.0 for 1200) fails. Booleans and nulls are NOT checked
    against the source: they are returned as the model gave them. .docx files
    are text-extracted first (stdlib reader).
    """
    final, handle, _size = _open_contained(path)
    try:
        text, _nbytes = _read_text(final, handle)
    finally:
        handle.close()
    if len(text) > CHUNK_CHARS:
        raise ValueError(
            "file text is %d chars, over the %d single-call cap: "
            "extract_json_file is single-chunk by design (multi-chunk "
            "extraction compounds hallucination). Pre-trim the file or "
            "extract from a specific section." % (len(text), CHUNK_CHARS))

    fields = extract_json(text, schema, model=FILE_MODEL)

    source_norm = _norm(text)
    unverified = []
    for name, value in list(fields.items()):
        if not _value_verifies(value, source_norm):
            fields[name] = None
            unverified.append(name)

    return {
        "label": _LABEL % FILE_MODEL,
        "path": final,
        "fields": fields,
        "unverified_fields": unverified,
        "note": ("fields in unverified_fields were NULLED: the model's value "
                 "was not present verbatim in the source" if unverified else ""),
    }
