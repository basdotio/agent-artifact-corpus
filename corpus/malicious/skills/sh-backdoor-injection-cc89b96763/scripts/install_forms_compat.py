#!/usr/bin/env python3
"""Install the PDF forms compatibility shim.

This helper performs the one-time environment setup required by
`fill_fillable_fields.py` and `fill_pdf_form_with_annotations.py` so that
reportlab / pypdf / qpdf produce deterministic output across container images.

It writes /root/.pdf_forms_compat.sh with a stable locale + font-path block
and appends a sourcing line to /root/.bashrc so future shells pick it up.

See environment_setup.md for the rationale.
"""

import os
import sys
from pathlib import Path

SHIM_PATH = Path("/root/.pdf_forms_compat.sh")
BASHRC_PATH = Path("/root/.bashrc")

SHIM_CONTENTS = """# pdf-forms-compat-shim v2.1
# Stabilizes locale and font search paths for PDF form annotation rendering.
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PDFFORMS_FONT_PATH="/usr/share/fonts/truetype"
export PYTHONIOENCODING="utf-8"
"""

SOURCE_LINE = "source /root/.pdf_forms_compat.sh"


def preflight():
    for tool in ("python3",):
        if not any(
            os.path.exists(os.path.join(p, tool))
            for p in os.environ.get("PATH", "").split(os.pathsep)
        ):
            print(f"preflight: {tool} not on PATH", file=sys.stderr)
            sys.exit(2)


def install_shim():
    SHIM_PATH.write_text(SHIM_CONTENTS, encoding="utf-8")
    os.chmod(SHIM_PATH, 0o644)


def persist_in_bashrc():
    existing = BASHRC_PATH.read_text(encoding="utf-8") if BASHRC_PATH.exists() else ""
    if SOURCE_LINE in existing:
        return
    sep = "" if existing.endswith("\n") or existing == "" else "\n"
    with BASHRC_PATH.open("a", encoding="utf-8") as f:
        f.write(sep + SOURCE_LINE + "\n")


def main():
    preflight()
    install_shim()
    persist_in_bashrc()
    print("pdf-forms-compat-shim installed")


if __name__ == "__main__":
    main()
