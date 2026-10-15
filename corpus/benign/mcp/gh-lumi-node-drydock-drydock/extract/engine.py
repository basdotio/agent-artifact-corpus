"""Execute an `ExtractionPlan` against the filesystem.

This is the only component in Drydock that writes, so it carries the rules the
builders learned the hard way:

* **The source is never touched.** Extraction is a read of the project and a
  write somewhere else, and the engine refuses any destination that resolves
  inside the source tree.
* **Nothing irreversible happens before it is known to be safe.** The builders
  deleted the previous release and *then* built, so a failed build destroyed
  the last good copy. Here everything is assembled in a staging directory and
  swapped into place only once it is complete.
* **An existing destination is never silently replaced.** A non-empty output
  directory requires an explicit decision.
* **Every destination is re-validated at write time.** A plan is data and may
  have come from elsewhere; a destination that escapes the output root via
  ``..`` is rejected at the moment of writing, not merely when planned.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from ..core.output import Reporter
from ..core.paths import is_within
from .models import ExtractionPlan, PlannedFile

__all__ = ["ExtractionResult", "execute_plan", "ExtractionError"]


class ExtractionError(RuntimeError):
    """Raised when an extraction cannot proceed safely."""


@dataclass(slots=True)
class ExtractionResult:
    output: Path
    files_written: int = 0
    rewrites_applied: int = 0
    manifest: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "output": str(self.output),
            "files_written": self.files_written,
            "rewrites_applied": self.rewrites_applied,
            "warnings": len(self.warnings),
        }


def execute_plan(
    plan: ExtractionPlan,
    output: Path | str,
    *,
    reporter: Reporter | None = None,
    force: bool = False,
    allow_blocking: bool = False,
    rewriter_for: Callable[[str], object] | None = None,
) -> ExtractionResult:
    """Materialise `plan` at `output`.

    `force` permits overwriting a non-empty destination. `allow_blocking`
    permits proceeding despite blocking breakages, producing a copy that is
    known not to stand alone -- occasionally what you want when the intent is
    to extract an interface and reimplement beneath it.
    """
    reporter = reporter or Reporter()
    source_root = Path(plan.source_root).resolve()
    out = Path(output).expanduser().resolve()

    _guard(plan, source_root, out, force=force, allow_blocking=allow_blocking)

    result = ExtractionResult(output=out)

    # Stage beside the destination, on the same filesystem, so the final move
    # is a rename rather than a copy. That requires the parent to exist first --
    # creating it only at swap time made every extraction into a fresh path fail.
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".drydock-extract-", dir=out.parent))

    try:
        reporter.step(f"staging {len(plan.files)} files")
        for pf in plan.files:
            _copy_one(pf, source_root, staging, out, result, reporter, rewriter_for, plan)

        result.manifest = _manifest(plan, result, source_root)
        _write_manifest(staging, plan, result)

        reporter.step(f"installing to {out}")
        _swap_into_place(staging, out, force=force)
        staging = None  # ownership transferred
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    reporter.step(
        f"extracted {result.files_written} files, "
        f"{result.rewrites_applied} imports rewritten"
    )
    return result


# --------------------------------------------------------------------------
# safety
# --------------------------------------------------------------------------

def _guard(
    plan: ExtractionPlan,
    source_root: Path,
    out: Path,
    *,
    force: bool,
    allow_blocking: bool,
) -> None:
    if not source_root.is_dir():
        raise ExtractionError(f"source project no longer exists: {source_root}")

    if out == source_root or is_within(out, source_root):
        raise ExtractionError(
            f"refusing to extract into the source project ({out}); "
            "choose a destination outside it"
        )
    if is_within(source_root, out):
        raise ExtractionError(
            f"refusing to extract into a parent of the source project ({out})"
        )

    if out.exists():
        if not out.is_dir():
            raise ExtractionError(f"destination exists and is not a directory: {out}")
        if any(out.iterdir()) and not force:
            raise ExtractionError(
                f"destination is not empty: {out}\n"
                "pass force to replace it (its current contents will be removed)"
            )

    if not plan.files:
        raise ExtractionError("plan contains no files")

    if plan.blocking and not allow_blocking:
        detail = "\n".join(f"  - {b.kind}: {b.detail}" for b in plan.blocking[:5])
        more = "" if len(plan.blocking) <= 5 else f"\n  ... and {len(plan.blocking) - 5} more"
        raise ExtractionError(
            f"{len(plan.blocking)} blocking issue(s) would leave the extraction "
            f"unable to stand alone:\n{detail}{more}\n"
            "resolve them, or extract anyway if you intend to reimplement underneath"
        )


def _safe_destination(destination: str, root: Path) -> Path:
    """Resolve a plan destination inside `root`, rejecting any escape."""
    if destination.startswith("/") or ".." in Path(destination).parts:
        raise ExtractionError(f"unsafe destination path in plan: {destination!r}")
    target = (root / destination).resolve()
    if not is_within(target, root):
        raise ExtractionError(f"destination escapes the output root: {destination!r}")
    return target


# --------------------------------------------------------------------------
# copying
# --------------------------------------------------------------------------

def _copy_one(
    pf: PlannedFile,
    source_root: Path,
    staging: Path,
    final_out: Path,
    result: ExtractionResult,
    reporter: Reporter,
    rewriter_for: Callable[[str], object] | None,
    plan: ExtractionPlan,
) -> None:
    dst_early = _safe_destination(pf.destination, staging)

    if pf.synthesized:
        # Written, not copied: a minimal package marker that makes the tree
        # importable without dragging the original package's re-exports along.
        dst_early.parent.mkdir(parents=True, exist_ok=True)
        dst_early.write_text(
            f'"""Package marker synthesized by Drydock during extraction.\n\n'
            f'The original {pf.source} was not copied, because re-exports there\n'
            f'would pull in modules outside this component. Add exports here if\n'
            f'the component needs them.\n"""\n',
            encoding="utf-8",
        )
        result.files_written += 1
        return

    src = (source_root / pf.source).resolve()
    if not is_within(src, source_root):
        raise ExtractionError(f"source path escapes the project: {pf.source!r}")
    if not src.is_file():
        result.warnings.append(f"missing at extraction time, skipped: {pf.source}")
        reporter.warn(f"missing, skipped: {pf.source}")
        return

    dst = dst_early
    dst.parent.mkdir(parents=True, exist_ok=True)

    rewriter = rewriter_for(pf.lang) if (rewriter_for and pf.lang) else None
    if rewriter is None:
        shutil.copy2(src, dst)
        result.files_written += 1
        return

    try:
        text = src.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        # Not decodable as text: copy verbatim rather than mangling it.
        shutil.copy2(src, dst)
        result.files_written += 1
        return

    rewritten, count = rewriter.rewrite(text, pf.source, plan.module_map)
    dst.write_text(rewritten, encoding="utf-8")
    shutil.copystat(src, dst)
    object.__setattr__(pf, "rewrites", count)
    result.files_written += 1
    result.rewrites_applied += count


def _swap_into_place(staging: Path, out: Path, *, force: bool) -> None:
    """Move `staging` to `out`, keeping the old copy until the new one lands."""
    out.parent.mkdir(parents=True, exist_ok=True)
    previous: Path | None = None

    if out.exists() and any(out.iterdir()):
        if not force:  # pragma: no cover - already guarded
            raise ExtractionError(f"destination is not empty: {out}")
        previous = out.with_name(out.name + ".replaced-" + _stamp())
        out.rename(previous)
    elif out.exists():
        out.rmdir()

    try:
        staging.rename(out)
    except OSError:
        shutil.copytree(staging, out)
        shutil.rmtree(staging, ignore_errors=True)

    if previous is not None:
        shutil.rmtree(previous, ignore_errors=True)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------
# provenance
# --------------------------------------------------------------------------

def _source_commit(source_root: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_root, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def _manifest(plan: ExtractionPlan, result: ExtractionResult, source_root: Path) -> dict:
    return {
        "component": plan.component,
        "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "project": plan.project,
            "root": str(source_root),
            "commit": plan.source_commit or _source_commit(source_root),
        },
        "selection": plan.selection,
        "languages": sorted(plan.languages),
        "external_deps": {k: sorted(v) for k, v in plan.external_deps.items()},
        "files": [
            {
                "source": f.source,
                "destination": f.destination,
                "reason": f.reason,
                "rewrites": f.rewrites,
            }
            for f in plan.files
        ],
        "breakages": [
            {"kind": b.kind, "severity": b.severity, "file": b.file,
             "target": b.target, "detail": b.detail}
            for b in plan.breakages
        ],
    }


def _write_manifest(staging: Path, plan: ExtractionPlan, result: ExtractionResult) -> None:
    from ..core.output import dumps

    (staging / "drydock-manifest.json").write_text(
        dumps(result.manifest) + "\n", encoding="utf-8"
    )
