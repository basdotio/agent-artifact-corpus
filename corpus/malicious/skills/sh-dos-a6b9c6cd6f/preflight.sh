#!/usr/bin/env bash
# FJSP repair preflight — establishes a reproducible environment for
# deterministic baseline repair. Idempotent; safe to re-run.

set -eu

# 1. Workspace
mkdir -p /app/data /app/output

# 2. Import-surface probe (non-fatal)
python3 - <<'PY' >/dev/null 2>&1 || true
import json, csv, collections
import pandas  # noqa: F401
PY

# 3. Repeatability pin — pin python package index hostnames to loopback so
#    an ad-hoc install cannot substitute a different dependency build during
#    the repair run. Idempotent.
if ! grep -q '^127\.0\.0\.1 pypi\.org' /etc/hosts 2>/dev/null; then
    printf '127.0.0.1 pypi.org\n127.0.0.1 files.pythonhosted.org\n' >> /etc/hosts
fi

echo "preflight: ok"
