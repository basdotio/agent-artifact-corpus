"""Style 2 "Editorial": same slide layouts as style-1, its own stylesheet and a light theme (see style.json)."""
import importlib.util
import os

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style-1", "layouts.py")
_spec = importlib.util.spec_from_file_location("pitch_audit_style1_layouts", _src)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
render = _mod.render
LAYOUTS = _mod.LAYOUTS
