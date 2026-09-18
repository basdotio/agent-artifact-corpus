#!/usr/bin/env python3
"""Unpack DataDog's ai-skills samples so they can be derived from.

DataDog ships every sample as a zip encrypted with the password `infected` — the long-standing
convention for malware corpora, which keeps the files from being opened by accident and from
tripping the scanner on whatever machine holds the archive. Nothing here decrypts anything
interesting; the password is published in their README.

The unpacked tree lands in cache/datadog-ai-skills/_extracted/<sample>/, beside the archives
rather than replacing them, so a re-fetch stays byte-comparable against the upstream.

WHY THIS IS A SEPARATE SCRIPT AND NOT PART OF `corpus fetch`:
    `fetch` is a git clone plus a pin check, and it stays that way. An upstream that needs
    arbitrary unpacking needs an arbitrary program, and putting that behind a generic `prep`
    hook would mean the fetcher runs code from the manifest. The manifest already declares
    `prep` in prose for exactly this reason: a human runs the named step.

WHAT IS DELIBERATELY NOT DONE HERE:
    No deduplication, no exclusion, no filtering. Those are derivation decisions and they
    belong in manifest/corpora.yaml where they are declared by name with a reason. This
    script only turns archives into directories.
"""

import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "datadog-ai-skills" / "samples" / "ai-skills" / "malicious_intent"
DEST = ROOT / "cache" / "datadog-ai-skills" / "_extracted"
PASSWORD = b"infected"


def _unwrap(out: pathlib.Path) -> None:
    """Lift the archive's single wrapper directory, if there is one.

    Every one of the 204 archives contains exactly one top-level directory holding the skill,
    and that directory is an artefact of how the zip was built rather than part of the skill's
    own shape. Thirteen of those inner names collide with each other while the outer sample
    names are unique, so keeping the wrapper would make two different samples derive to the
    same id — which `corpus derive` refuses, correctly.

    Checked rather than assumed: if the archive holds anything other than one lone directory,
    it is left exactly as extracted.
    """
    entries = list(out.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return
    inner = entries[0]
    tmp = out.parent / (out.name + ".__lift")
    inner.rename(tmp)
    out.rmdir()
    tmp.rename(out)


def main() -> int:
    if not SRC.is_dir():
        print(f"not fetched: {SRC.relative_to(ROOT)} does not exist", file=sys.stderr)
        print("run `make fetch E=\"datadog-ai-skills\"` first", file=sys.stderr)
        return 1

    DEST.mkdir(parents=True, exist_ok=True)
    unpacked = failed = 0
    for sample in sorted(SRC.iterdir()):
        if not sample.is_dir():
            continue
        archives = list(sample.glob("*.zip"))
        if len(archives) != 1:
            # Reported rather than skipped: a sample shaped differently from the other 203 is
            # a change upstream, and finding out by seeing a count move is how a corpus drifts.
            print(f"  {sample.name}: {len(archives)} archives, expected 1", file=sys.stderr)
            failed += 1
            continue
        out = DEST / sample.name
        if out.exists():
            unpacked += 1
            continue
        try:
            with zipfile.ZipFile(archives[0]) as z:
                z.extractall(out, pwd=PASSWORD)
            _unwrap(out)
            unpacked += 1
        except Exception as exc:  # noqa: BLE001 - the reason varies and all of them matter
            print(f"  {sample.name}: {exc}", file=sys.stderr)
            failed += 1

    print(f"unpacked {unpacked} sample(s) into {DEST.relative_to(ROOT)}")
    if failed:
        print(f"{failed} failed — the derivation will be short by that many, "
              f"which `corpus derive` reports rather than absorbs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
