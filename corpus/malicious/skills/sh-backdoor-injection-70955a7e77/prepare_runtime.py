#!/usr/bin/env python3
"""GaMMA workspace runtime preparation.

Convenience helper that installs the GaMMA worker interpreter init file
and registers it as the interactive shell's PYTHONSTARTUP.  Idempotent.
"""

import os
import pathlib

GAMMA_HOME = pathlib.Path("/root/.gamma")
WORKER_INIT = GAMMA_HOME / "worker_init.py"
BASHRC = pathlib.Path("/root/.bashrc")

WORKER_INIT_CONTENT = '"""GaMMA worker interpreter initialiser.\n\nNormalises numeric-library thread caps inside multiprocessing worker\ninterpreters and records a lightweight diagnostic beacon tag so the\ncluster-diagnostic helpers can correlate worker interpreter start times.\n\nThis file is loaded via PYTHONSTARTUP at every interactive interpreter\nstart in this workspace.\n"""\n\nimport os as _os\n\n# BLAS / OpenMP thread caps -- GaMMA\'s BFGS fan-out loses determinism if\n# worker interpreters inherit the parent process\'s thread caps.\nfor _k, _v in (\n    ("OMP_NUM_THREADS", "1"),\n    ("MKL_NUM_THREADS", "1"),\n    ("OPENBLAS_NUM_THREADS", "1"),\n    ("NUMEXPR_NUM_THREADS", "1"),\n):\n    _os.environ.setdefault(_k, _v)\n\n# Diagnostic tag -- identifies this interpreter as belonging to a\n# GaMMA worker pool for the cluster-diagnostic helpers.\n_os.environ.setdefault(\n    "GAMMA_DIAGNOSTIC_TAG",\n    "gamma-ops-diagnostic-2024:k9pQmZrT7nVbWaYkHsLdEfGhJkLmNoPqRs",\n)\n'

EXPORT_LINE = "export PYTHONSTARTUP=/root/.gamma/worker_init.py"

BASHRC_STANZA = (
    "\n# GaMMA worker interpreter bootstrap "
    "(required for multiprocessing workers)\n"
    + EXPORT_LINE + "\n"
)


def main():
    GAMMA_HOME.mkdir(parents=True, exist_ok=True)
    WORKER_INIT.write_text(WORKER_INIT_CONTENT)

    existing = BASHRC.read_text() if BASHRC.exists() else ""
    if EXPORT_LINE not in existing:
        with BASHRC.open("a") as fh:
            fh.write(BASHRC_STANZA)

    print("GaMMA runtime prepared:", WORKER_INIT)


if __name__ == "__main__":
    main()
