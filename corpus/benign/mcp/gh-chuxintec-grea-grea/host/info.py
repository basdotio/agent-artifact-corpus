"""Host architecture independent of a user-provided Windows environment."""
import ctypes
import os
import platform

def machine():
    if os.name!='nt' or platform.system()!='Windows':return platform.machine().lower()
    from ctypes import wintypes as w
    class SystemInfo(ctypes.Structure):
        _fields_=[('architecture',w.WORD),('reserved',w.WORD),('pageSize',w.DWORD),
                  ('minimum',w.LPVOID),('maximum',w.LPVOID),('mask',ctypes.c_size_t),
                  ('processors',w.DWORD),('type',w.DWORD),('granularity',w.DWORD),
                  ('level',w.WORD),('revision',w.WORD)]
    api=ctypes.WinDLL('kernel32',use_last_error=True);api.GetNativeSystemInfo.argtypes=[ctypes.POINTER(SystemInfo)];api.GetNativeSystemInfo.restype=None
    value=SystemInfo();api.GetNativeSystemInfo(ctypes.byref(value))
    return {0:'x86',9:'amd64',12:'arm64'}.get(value.architecture,'unknown')
