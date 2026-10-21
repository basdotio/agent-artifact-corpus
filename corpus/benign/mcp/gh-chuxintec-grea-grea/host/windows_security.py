"""Private staging DACL for an actual AppContainer, without changing parent ACLs."""
import ctypes as c
from ctypes import wintypes as w
import uuid
from .paths import Path

class Security(c.Structure):
 _fields_=[('length',w.DWORD),('descriptor',w.LPVOID),('inherit',w.BOOL)]

def private_directory(parent,prefix):
 k=c.WinDLL('kernel32',use_last_error=True);a=c.WinDLL('advapi32',use_last_error=True)
 signatures={
  'GetCurrentProcess':([],w.HANDLE),'CloseHandle':([w.HANDLE],w.BOOL),
  'LocalFree':([w.LPVOID],w.LPVOID),
  'CreateDirectoryW':([w.LPCWSTR,c.POINTER(Security)],w.BOOL)}
 for name,(args,ret) in signatures.items():getattr(k,name).argtypes=args;getattr(k,name).restype=ret
 a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)];a.OpenProcessToken.restype=w.BOOL
 a.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,w.LPVOID,w.DWORD,c.POINTER(w.DWORD)];a.GetTokenInformation.restype=w.BOOL
 a.ConvertSidToStringSidW.argtypes=[w.LPVOID,c.POINTER(w.LPWSTR)];a.ConvertSidToStringSidW.restype=w.BOOL
 a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[w.LPCWSTR,w.DWORD,c.POINTER(w.LPVOID),w.LPVOID];a.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype=w.BOOL
 def require(ok):
  if not ok:raise c.WinError(c.get_last_error())
 token=w.HANDLE();require(a.OpenProcessToken(k.GetCurrentProcess(),8,c.byref(token)))
 text=w.LPWSTR()
 try:
  size=w.DWORD();a.GetTokenInformation(token,31,None,0,c.byref(size))
  if not 0<size.value<65536:raise OSError('Invalid AppContainer SID buffer size')
  data=c.create_string_buffer(size.value);require(a.GetTokenInformation(token,31,data,size,c.byref(size)))
  sid=c.cast(data,c.POINTER(w.LPVOID))[0]
  require(a.ConvertSidToStringSidW(sid,c.byref(text)))
  identity=text.value
 finally:
  if text:k.LocalFree(c.cast(text,w.LPVOID))
  k.CloseHandle(token)
 # Preserve Python 0700's protected owner/system/admin policy and add only the
 # creating lowbox SID. No Everyone/Users grant and no parent permission change.
 descriptor=w.LPVOID()
 sddl='D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;OW)(A;OICI;FA;;;'+identity+')'
 require(a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(descriptor),None))
 try:
  security=Security(c.sizeof(Security),descriptor,False)
  for _ in range(3):
   path=Path(parent)/(prefix+uuid.uuid4().hex)
   if k.CreateDirectoryW(str(path),c.byref(security)):return path
   error=c.get_last_error()
   if error!=183:raise c.WinError(error)
  raise FileExistsError('Private staging name collision')
 finally:k.LocalFree(descriptor)
