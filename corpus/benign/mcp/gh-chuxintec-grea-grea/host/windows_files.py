"""Handle-based Windows file identity and reparse refusal, without CRT stat IDs."""
import ctypes as c
from ctypes import wintypes as w
import os
from grea.host.paths import Path

class Info(c.Structure):
 _fields_=[('attributes',w.DWORD),('created',w.FILETIME),('accessed',w.FILETIME),('written',w.FILETIME),
           ('volume',w.DWORD),('sizeHigh',w.DWORD),('sizeLow',w.DWORD),('links',w.DWORD),('indexHigh',w.DWORD),('indexLow',w.DWORD)]

def kernel():
 k=c.WinDLL('kernel32',use_last_error=True)
 k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE];k.CreateFileW.restype=w.HANDLE
 k.GetFileInformationByHandle.argtypes=[w.HANDLE,c.POINTER(Info)];k.GetFileInformationByHandle.restype=w.BOOL
 k.GetFinalPathNameByHandleW.argtypes=[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD];k.GetFinalPathNameByHandleW.restype=w.DWORD
 k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
 return k

def handle_token(handle):
 k=kernel();i=Info()
 if not k.GetFileInformationByHandle(handle,c.byref(i)):raise c.WinError(c.get_last_error())
 if i.attributes&0x400:raise OSError('Reparse-point input refused')
 return (i.volume,i.indexHigh,i.indexLow,i.sizeHigh,i.sizeLow,i.written.dwHighDateTime,i.written.dwLowDateTime,i.created.dwHighDateTime,i.created.dwLowDateTime,i.attributes)

def open_file(path, access=0x80000000):
 k=kernel();path=Path(path).absolute()
 for p in (path,*path.parents):
  if p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400:raise OSError('Reparse-point ancestor refused')
 path=path.resolve(strict=True)
 handle=k.CreateFileW(str(path),access,1,None,3,0x200000|0x02000000,None)
 if handle in (None,w.HANDLE(-1).value):raise c.WinError(c.get_last_error())
 try:
  handle_token(handle)
  from .paths import final_name
  final=final_name(k,handle,path)
  if os.path.normcase(final)!=os.path.normcase(str(path)):raise OSError('Input path changed or escaped')
  return handle
 except BaseException:k.CloseHandle(handle);raise

def path_token(path):
 k=kernel();h=open_file(path,0x80)
 try:return handle_token(h)
 finally:k.CloseHandle(h)

def open_fd(path):
 import msvcrt
 h=open_file(path)
 try:return msvcrt.open_osfhandle(h,os.O_RDONLY|os.O_BINARY)
 except BaseException:kernel().CloseHandle(h);raise

def fd_token(fd):
 import msvcrt
 return handle_token(msvcrt.get_osfhandle(fd))
