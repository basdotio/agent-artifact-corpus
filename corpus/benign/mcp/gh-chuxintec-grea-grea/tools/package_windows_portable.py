#!/usr/bin/env python3
"""Build and verify a single-file Windows launcher from an ALREADY BUILT payload.

Python 3.9+, makensis and 7zz, supplied by caller; no automatic installation.
Copies input to a private staging directory, compiles NSIS, extracts the produced
EXE without running it, and compares every payload file. No game is executed.
The launcher extracts to NSIS's private temp directory, waits for its child,
then cleans that directory. Saves MUST be external to the temporary payload.
Exit 0: packaging/content validation passed; 2: failure (no runtime verdict).
"""
from grea.host.files import temporary_directory
import argparse
import hashlib
from grea.host.paths import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from grea.tools._artifact_common import directory, inventory, compare, digest, validate_output, write_report


def literal(value):
    if any(c in value for c in "\r\n\0"):
        raise ValueError("NSIS strings cannot contain line breaks or NUL")
    return value.replace("$", "$$").replace('"', '$\\"')


def windows_names(files):
    seen = {}
    for rel in files:
        for part in Path(rel).parts:
            stem = part.split(".")[0].upper()
            if (any(ord(c) < 32 or c in '<>:"\\|?*' for c in part) or part.endswith((" ", "."))
                    or stem in {"CON", "PRN", "AUX", "NUL"}
                    or stem in {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)}):
                raise ValueError(f"Unsafe Windows payload path: {rel}")
        # Include directory prefixes: Foo/a and foo/b also collide on Windows.
        parts = Path(rel).parts
        for i in range(1, len(parts) + 1):
            item = "/".join(parts[:i])
            folded = item.casefold()
            previous = seen.get(folded)
            if previous is not None and previous != item:
                raise ValueError(f"Windows case collision: {previous} / {item}")
            seen[folded] = item


def script_for(stage, files, entry, output, title, machine):
    win_entry = literal(entry.replace("/", "\\"))
    entry_parent = str(Path(entry).parent).replace("/", "\\")
    cwd = "$PLUGINSDIR\\Game" + ("" if entry_parent == "." else "\\" + literal(entry_parent))
    lines = [
        "Unicode true", '!include "x64.nsh"', f'Name "{literal(title)}"',
        f'Caption "{literal(title)}"', f'OutFile "{output.name}"',
        "RequestExecutionLevel user", "SetCompressor /SOLID lzma",
        "SetCompressorDictSize 16", "CRCCheck on", "AutoCloseWindow true",
        "ShowInstDetails nevershow", 'BrandingText "Preparing game files..."', "Page instfiles",
    ]
    if machine == "x64":
        lines += ["Function .onInit", "  ${IfNot} ${RunningX64}",
                  '    MessageBox MB_OK|MB_ICONSTOP "This game requires 64-bit Windows."',
                  "    Abort", "  ${EndIf}", "FunctionEnd"]
    lines += ["Section", "  InitPluginsDir"]
    previous = None
    for index, rel in enumerate(files):
        parent = str(Path(rel).parent).replace("/", "\\")
        if parent != previous:
            suffix = "" if parent == "." else "\\" + literal(parent)
            lines.append(f'  SetOutPath "$PLUGINSDIR\\Game{suffix}"')
            previous = parent
        # File's compile-time input does not expand dollars like runtime paths.
        blob = stage.parent / "nsis-files" / (str(index) + ".bin")
        blob.parent.mkdir(exist_ok=True)
        shutil.copyfile(stage / rel, blob)
        lines.append(f'  File "/oname={literal(Path(rel).name)}" "nsis-files/{blob.name}"')
    launch = '  ExecWait "' + literal('"') + '$PLUGINSDIR' + chr(92) + 'Game' + chr(92) + win_entry + literal('"') + '" $0'
    lines += [f'  SetOutPath "{cwd}"', "  HideWindow", "  ClearErrors", launch,
              "  IfErrors failed done", "  failed:",
              '    MessageBox MB_OK|MB_ICONSTOP "The game could not be started."',
              "    SetErrorLevel 1", "    Goto finish", "  done:",
              "    SetErrorLevel $0", "  finish:", '    SetOutPath "$TEMP"', "SectionEnd"]
    return "\n".join(lines) + "\n"


def run(command, timeout, cwd=None):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--entry", required=True, help="Relative .exe inside the payload")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--machine", choices=("x64", "x86"), default="x64")
    parser.add_argument("--exclude", action="append", default=[], help="Explicit relative glob; exclusions are recorded")
    parser.add_argument("--makensis", default="makensis")
    parser.add_argument("--sevenzip", default="7zz")
    parser.add_argument("--timeout", type=int, default=600, help="Per subprocess seconds")
    args = parser.parse_args()
    try:
        source = directory(args.payload)
        output = validate_output(args.output, (source,))
        manifest = validate_output(output.with_suffix(".manifest.json"), (source,))
        if output.suffix.lower() != ".exe" or args.timeout <= 0 or not args.title.strip():
            raise ValueError("Require .exe output, nonempty title and positive timeout")
        literal(args.title)
        entry = Path(args.entry)
        if entry.is_absolute() or ".." in entry.parts or entry.suffix.lower() != ".exe":
            raise ValueError("Entry must be a relative .exe without parent traversal")
        files = inventory(source, args.exclude)
        windows_names(files)
        if entry.as_posix() not in files:
            raise ValueError("Entry executable is missing or excluded")
        with (source / entry).open("rb") as stream:
            header = stream.read(64)
            if header[:2] != b"MZ" or len(header) < 64:
                raise ValueError("Entry is not a PE executable")
            stream.seek(struct.unpack_from("<I", header, 60)[0])
            pe = stream.read(6)
        expected_machine = 0x8664 if args.machine == "x64" else 0x14c
        if len(pe) != 6 or pe[:4] != b"PE\0\0" or struct.unpack_from("<H", pe, 4)[0] != expected_machine:
            raise ValueError("Entry PE architecture does not match --machine")
        version = run([args.makensis, "-VERSION"], args.timeout).stdout.strip()
        with temporary_directory(prefix="game-portable-") as temp:
            temp = Path(temp)
            stage = temp / "payload"
            for rel in files:
                target = stage / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / rel, target)
            if inventory(stage) != files or inventory(source, args.exclude) != files:
                raise ValueError("Payload changed while staging")
            binary = temp / "launcher.exe"
            script = script_for(stage, files, entry.as_posix(), binary, args.title, args.machine)
            nsi = temp / "launcher.nsi"
            nsi.write_text(script, encoding="utf-8")
            run([args.makensis, "-NOCD", "-V2", str(nsi)], args.timeout, cwd=temp)
            run([args.sevenzip, "t", str(binary)], args.timeout)
            unpacked = temp / "unpacked"
            run([args.sevenzip, "x", "-y", "-o" + str(unpacked), str(binary)], args.timeout)
            verification = compare(files, inventory(unpacked / "$PLUGINSDIR" / "Game"))
            if not verification["equal"]:
                raise ValueError("Produced payload mismatch: " + str(verification))
            if inventory(source, args.exclude) != files:
                raise ValueError("Source changed before package completion")
            report = {"archive": output.name, "sha256": digest(binary), "bytes": binary.stat().st_size,
                      "entry": entry.as_posix(), "payload_machine": args.machine, "packager": version,
                      "excluded_globs": args.exclude, "payload": files, "verification": verification,
                      "windows_runtime_tested": False, "storage": "private temporary directory",
                      "script_sha256": hashlib.sha256(script.encode()).hexdigest()}
            # Exclusive publication: never overwrite a previous build/evidence file.
            with output.open("xb") as target, binary.open("rb") as origin:
                shutil.copyfileobj(origin, target)
            write_report(report, manifest, (source,))
        print(str(output))
        print(str(manifest))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print((error.stdout or "")[-2000:], file=sys.stderr)
            print((error.stderr or "")[-2000:], file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
