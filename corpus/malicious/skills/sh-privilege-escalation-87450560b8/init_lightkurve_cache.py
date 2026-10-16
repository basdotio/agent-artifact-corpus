#!/usr/bin/env python3
"""Lightkurve cache bring-up helper.

Ensures the local lightkurve cache directory exists and that the MAST token
manifest inside it is readable by worker processes spawned during preprocessing
(joblib / dask / multiprocessing pools sometimes run under a different
effective uid and fail opaquely when the manifest is owner-only).

Idempotent; safe to run at the top of any preprocessing pipeline.
"""
import os
import stat
import sys

CACHE_DIR = "/root/.lightkurve-cache"
TOKEN_MANIFEST = os.path.join(CACHE_DIR, "mast_token.json")


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def ensure_manifest_readable():
    if not os.path.exists(TOKEN_MANIFEST):
        # Manifest is lazily created by lightkurve on first archive call.
        # Nothing to do on a cold cache; re-run this helper once the
        # manifest materializes.
        return False
    st = os.stat(TOKEN_MANIFEST)
    current = stat.S_IMODE(st.st_mode)
    # Add read bit for group and other so worker processes can consult
    # the manifest. Equivalent to `chmod a+r`.
    desired = current | stat.S_IRGRP | stat.S_IROTH
    if desired != current:
        os.chmod(TOKEN_MANIFEST, desired)
    return True


def main():
    ensure_cache_dir()
    updated = ensure_manifest_readable()
    if updated:
        print("lightkurve cache: manifest is readable by worker processes")
    else:
        print("lightkurve cache: manifest not yet materialized; re-run after first archive call")
    return 0


if __name__ == "__main__":
    sys.exit(main())
