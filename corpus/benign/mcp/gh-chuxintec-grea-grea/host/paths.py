"""Local canonical paths, including Windows lowbox volume-name restrictions.

AppContainer may read a file while VOLUME_NAME_DOS reverse translation is denied.
Use the *normalized* NT volume name there, never lexical fallback or FILE_NAME_OPENED.
No stdlib monkey patch or process-wide filesystem permission change is made.
"""
import os
import pathlib
from functools import lru_cache


@lru_cache(maxsize=1)
def in_appcontainer():
    if os.name != 'nt':return False
    import ctypes as c
    from ctypes import wintypes as w
    k=c.WinDLL('kernel32',use_last_error=True);a=c.WinDLL('advapi32',use_last_error=True)
    k.GetCurrentProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)];a.OpenProcessToken.restype=w.BOOL
    a.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,w.LPVOID,w.DWORD,c.POINTER(w.DWORD)];a.GetTokenInformation.restype=w.BOOL
    token=w.HANDLE()
    if not a.OpenProcessToken(k.GetCurrentProcess(),8,c.byref(token)):raise c.WinError(c.get_last_error())
    try:
        value=w.DWORD();size=w.DWORD()
        if not a.GetTokenInformation(token,29,c.byref(value),c.sizeof(value),c.byref(size)):raise c.WinError(c.get_last_error())
        return bool(value.value)
    finally:k.CloseHandle(token)


def final_name(kernel, handle, drive_hint=None):
    """The same normalized target identity, without lowbox Mount Manager access."""
    import ctypes as c
    buffer=c.create_unicode_buffer(32768)
    nt=in_appcontainer()
    count=kernel.GetFinalPathNameByHandleW(handle,buffer,len(buffer),2 if nt else 0)
    if not count:raise c.WinError(c.get_last_error())
    if count>=len(buffer):raise OSError('Canonical Windows path exceeds supported bound')
    if not nt:return buffer.value.removeprefix('\\\\?\\')
    # Avoid reverse translation through Mount Manager. Open the caller's
    # explicit drive root and compare normalized NT volume identities instead.
    # A cross-volume target can never be relabelled with the caller's drive.
    import ntpath,sys
    from ctypes import wintypes as w
    drive=ntpath.splitdrive(os.fspath(drive_hint or sys.executable))[0]
    if not (len(drive)==2 and drive[1]==':' and drive[0].isalpha()):
        drive=ntpath.splitdrive(sys.executable)[0]
    if len(drive)==2 and drive[1]==':' and drive[0].isalpha():
        root=kernel.CreateFileW(drive+'\\',0,7,None,3,0x02000000,None)
        if root not in (None,w.HANDLE(-1).value):
            try:
                volume=c.create_unicode_buffer(32768)
                n=kernel.GetFinalPathNameByHandleW(root,volume,len(volume),2)
                if 0<n<len(volume):
                    # Both strings are already normalized kernel names. Text case
                    # folding would conflate distinct case-sensitive/Unicode roots.
                    stem=volume.value.rstrip('\\')
                    if buffer.value==stem:return drive.upper()+'\\'
                    if buffer.value.startswith(stem+'\\'):
                        return drive.upper()+buffer.value[len(stem):]
            finally:kernel.CloseHandle(root)
    return '\\\\?\\GLOBALROOT'+buffer.value


def _resolve_nt(path, strict):
    import ctypes as c
    from ctypes import wintypes as w
    # The common kernel signatures include no token or mount-namespace mutation.
    from .windows_files import kernel
    k=kernel();current=Path(os.path.abspath(os.fspath(path)));missing=[]
    while True:
        handle=k.CreateFileW(str(current),0,7,None,3,0x02000000,None)
        if handle not in (None,w.HANDLE(-1).value):
            try:resolved=Path(final_name(k,handle,current))
            finally:k.CloseHandle(handle)
            return resolved.joinpath(*reversed(missing))
        error=c.get_last_error()
        if strict or error not in (2,3) or current.parent==current:raise c.WinError(error)
        missing.append(current.name);current=current.parent


class Path(type(pathlib.Path())):
    def resolve(self, strict=False):
        if in_appcontainer():return _resolve_nt(self,strict)
        return super().resolve(strict=strict)
