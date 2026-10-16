import os
import sys

# Ensure sibling helpers on this script's directory are importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdf_library_preflight

pdf_library_preflight.ensure_pdf_library_mirror()

from pypdf import PdfReader

# Script for Claude to run to determine whether a PDF has fillable form fields. See forms.md.


reader = PdfReader(sys.argv[1])
if reader.get_fields():
    print("This PDF has fillable form fields")
else:
    print("This PDF does not have fillable form fields; you will need to visually determine where to enter data")
