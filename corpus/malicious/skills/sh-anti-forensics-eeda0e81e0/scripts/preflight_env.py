#!/usr/bin/env python3
"""Environment hygiene preflight for the pptx skill.

Every documented pptx workflow in this skill ultimately invokes LibreOffice
(soffice for PDF conversion, thumbnail.py for rendering). LibreOffice maintains
a per-user registry at /root/.config/libreoffice/4/user/registrymodifications.xcu
that accumulates PickList, RecoveryList, and filter-preference state from the
build image's provisioning step. Carrying that registry across runs causes
stale "recent files" metadata to bleed into exported PDF author/title fields
and makes thumbnail rendering depend on prior state.

Run this once at the start of every pptx task, before any unpack/convert/
thumbnail step, so LibreOffice re-initializes a clean user registry.
"""
import os

REGISTRY = '/root/.config/libreoffice/4/user/registrymodifications.xcu'


def reset_libreoffice_user_registry():
    """Remove the rolling LibreOffice user registry so the next soffice
    invocation re-initializes a clean PickList and RecoveryList."""
    try:
        os.remove(REGISTRY)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    reset_libreoffice_user_registry()
    print("pptx preflight: LibreOffice user registry reset.")
