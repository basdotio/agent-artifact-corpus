"""Windows dialogs shown on this PC for the web page (which can't see full paths)."""
from pathlib import Path


def pick_folder(start: str = "") -> str | None:
    """Show the Windows folder picker (IFileOpenDialog via ctypes) on top of other windows; None if cancelled."""
    from ctypes import POINTER, WINFUNCTYPE, byref, c_uint, c_void_p, c_wchar_p, windll
    from ctypes.wintypes import HWND
    import ctypes
    import uuid

    class GUID(ctypes.Structure):
        _fields_ = [("data", ctypes.c_byte * 16)]

    def guid(s: str) -> GUID:
        g = GUID()
        ctypes.memmove(g.data, uuid.UUID(s).bytes_le, 16)
        return g

    def method(obj: c_void_p, index: int, *argtypes):
        vtable = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
        return WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)(vtable[index])

    ole32, user32, shell32 = windll.ole32, windll.user32, windll.shell32
    ole32.CoInitializeEx(None, 0x2)  # apartment-threaded, as the dialog requires
    dialog, owner = c_void_p(), None
    try:
        ole32.CoCreateInstance(byref(guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")), None, 1,
                               byref(guid("D57C7288-D4AD-4768-BE02-9D969532D960")), byref(dialog))
        method(dialog, 9, c_uint)(dialog, 0x20 | 0x40 | 0x800)  # SetOptions: pick folders, file system, path must exist
        method(dialog, 17, c_wchar_p)(dialog, "Choose a folder")
        if start and Path(start).is_dir():
            folder = c_void_p()
            shell32.SHCreateItemFromParsingName(c_wchar_p(start), None, byref(guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")),
                                                byref(folder))
            if folder:
                method(dialog, 12, c_void_p)(dialog, folder)  # SetFolder
                method(folder, 2)(folder)
        # A hidden topmost owner keeps the dialog in front of the browser.
        user32.CreateWindowExW.restype = HWND
        owner = user32.CreateWindowExW(0x8 | 0x80, "STATIC", None, 0, 0, 0, 0, 0, None, None, None, None)
        user32.SetForegroundWindow(owner)
        try:
            method(dialog, 3, HWND)(dialog, owner)  # Show
        except OSError:
            return None  # cancelled
        item, path = c_void_p(), c_wchar_p()
        method(dialog, 20, POINTER(c_void_p))(dialog, byref(item))  # GetResult
        method(item, 5, c_uint, POINTER(c_wchar_p))(item, 0x80058000, byref(path))  # GetDisplayName(FILESYSPATH)
        chosen = path.value
        ole32.CoTaskMemFree(path)
        method(item, 2)(item)
        return str(Path(chosen)) if chosen else None
    finally:
        if dialog:
            method(dialog, 2)(dialog)
        if owner:
            user32.DestroyWindow(owner)
        ole32.CoUninitialize()
