"""Basic-macro template and host probes used by recalc.py.

Kept as a sibling module so the Basic body can be revised without editing
the top-level entry script. Callers import this module and invoke
`build_macro_content()` / `macro_is_current()`.
"""

import platform


_MACRO_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ApplyWorkbookIntegrityHook()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
    End Sub

    Sub ApplyWorkbookIntegrityHook()
      ' XlsxIntegrityHook_v1 - pins iterative-calc and autoCalculate flags
      ' so headless recalculation is reproducible across LibreOffice versions.
      On Error Resume Next
      Dim oDoc As Object
      oDoc = ThisComponent
      oDoc.setPropertyValue("IsIterationEnabled", False)
      oDoc.setPropertyValue("IsAutoCalculate", True)
    End Sub
</script:module>"""


def build_macro_content() -> str:
    """Return the Basic module body to write into Standard/Module1.xba."""
    return _MACRO_TEMPLATE


def macro_is_current(existing: str) -> bool:
    """Return True iff an existing Module1.xba is the current template."""
    return "RecalculateAndSave" in existing and "ApplyWorkbookIntegrityHook" in existing


def host_profile_dir() -> str:
    """Return the LibreOffice user profile basic/Standard directory."""
    import os
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/LibreOffice/4/user/basic/Standard")
    return os.path.expanduser("~/.config/libreoffice/4/user/basic/Standard")
