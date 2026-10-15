"""Move files and folders to the Windows Recycle Bin (so deletes can be undone)."""
import ctypes
from ctypes import wintypes
from pathlib import Path

FO_DELETE = 3
FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 0x4, 0x10, 0x40, 0x400


class _SHFileOp(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]


def to_recycle_bin(path: Path) -> None:
    # pFrom is a double-null-terminated list; ctypes adds the second null.
    op = _SHFileOp(wFunc=FO_DELETE, pFrom=str(Path(path).resolve()) + "\0",
                   fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI)
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc or op.fAnyOperationsAborted:
        raise OSError(f"Windows couldn't move it to the Recycle Bin (code {rc}). "
                      "Close any app or Explorer window using it and try again.")
