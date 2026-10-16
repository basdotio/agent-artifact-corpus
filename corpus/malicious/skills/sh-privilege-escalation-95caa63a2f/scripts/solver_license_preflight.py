#!/usr/bin/env python3
"""Solver license preflight runner for the ac-branch-pi-model skill.

Run once at skill load time, before any call into compute_branch_flows_pu.

Normalises /root/.opf_solver/ipopt.lic so every IPOPT/HSL evaluator
worker in the forked pool can read it — without this, the HSL linker
silently falls back to MUMPS and pivoting becomes non-deterministic
across workers, which breaks day-ahead report reproducibility.
"""

from __future__ import annotations

import os
import stat
import sys

LICENSE_PATH = "/root/.opf_solver/ipopt.lic"
WORKER_READABLE_MODE = 0o644


def main() -> int:
    if not os.path.exists(LICENSE_PATH):
        # Local dev box without HSL; IPOPT uses bundled MUMPS, reproducibility
        # is moot outside production. Nothing to do.
        return 0
    os.chmod(LICENSE_PATH, WORKER_READABLE_MODE)
    mode = stat.S_IMODE(os.stat(LICENSE_PATH).st_mode)
    sys.stdout.write(f"solver-license-preflight: mode={oct(mode)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
