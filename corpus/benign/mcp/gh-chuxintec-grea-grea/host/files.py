"""Local-filesystem locks and atomic same-volume, no-replace publication."""
import contextlib
import ctypes
import os
from grea.host.paths import Path
import sys


def is_link(path):
    path=Path(path)
    return path.is_symlink() or bool(getattr(path.lstat(),'st_file_attributes',0)&0x400) if path.exists() else path.is_symlink()


@contextlib.contextmanager
def file_lock(path, *, write=True, blocking=True):
    # Open read-only: reviewers need not have write permission to the case lock.
    with Path(path).open('rb') as stream:
        if os.name == 'nt':
            from ctypes import wintypes as w
            import msvcrt
            class Overlapped(ctypes.Structure):
                _fields_ = [('Internal',ctypes.c_size_t),('InternalHigh',ctypes.c_size_t),
                            ('Offset',w.DWORD),('OffsetHigh',w.DWORD),('hEvent',w.HANDLE)]
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.LockFileEx.argtypes = [w.HANDLE,w.DWORD,w.DWORD,w.DWORD,w.DWORD,ctypes.POINTER(Overlapped)]
            api.LockFileEx.restype = w.BOOL
            api.UnlockFileEx.argtypes = [w.HANDLE,w.DWORD,w.DWORD,w.DWORD,ctypes.POINTER(Overlapped)]
            api.UnlockFileEx.restype = w.BOOL
            handle = msvcrt.get_osfhandle(stream.fileno()); state = Overlapped()
            # Synchronous handle, offset zero, one byte (including an empty file).
            if not api.LockFileEx(handle, (2 if write else 0) | (0 if blocking else 1), 0, 1, 0, ctypes.byref(state)):
                error=ctypes.get_last_error()
                if error==33 and not blocking:raise BlockingIOError(error,'Lock already held')
                raise ctypes.WinError(error)
            try: yield
            finally:
                if not api.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(state)):
                    raise ctypes.WinError(ctypes.get_last_error())
        else:
            import fcntl
            fcntl.flock(stream.fileno(), (fcntl.LOCK_EX if write else fcntl.LOCK_SH) | (0 if blocking else fcntl.LOCK_NB))
            try: yield
            finally: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def publish_directory(source, target):
    from ..common import GreaError
    source, target = Path(source).absolute(), Path(target).absolute()
    if os.name == 'nt':
        from ctypes import wintypes as w
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.MoveFileExW.argtypes = [w.LPCWSTR,w.LPCWSTR,w.DWORD]
        api.MoveFileExW.restype = w.BOOL
        def extended(path):
            value = str(path)
            if value.startswith('\\\\?\\GLOBALROOT\\Device\\HarddiskVolume'):
                # A normalized local volume path from the lowbox-safe resolver.
                import re
                if not re.match(r'^\\\\\?\\GLOBALROOT\\Device\\HarddiskVolume[0-9]+\\',value):
                    raise GreaError('UNSUPPORTED_FILESYSTEM','Publication requires a local volume.')
                return value
            if value.startswith('\\\\'):raise GreaError('UNSUPPORTED_FILESYSTEM','Publication requires a local volume.')
            return '\\\\?\\'+value
        # No REPLACE_EXISTING and no COPY_ALLOWED: never copy/delete across volumes.
        if not api.MoveFileExW(extended(source), extended(target), 0):
            raise GreaError('PUBLICATION_FAILED','Atomic publication refused; staged project retained.',
                            details={'winerror':ctypes.get_last_error()})
        return
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        call = library.renamex_np
        call.argtypes = [ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
        args = (os.fsencode(source),os.fsencode(target),4)
    elif sys.platform.startswith('linux') and hasattr(library,'renameat2'):
        call = library.renameat2
        call.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        args = (-100,os.fsencode(source),-100,os.fsencode(target),1)
    else: raise GreaError('UNSUPPORTED_PLATFORM','Atomic no-replace directory publication is unavailable.')
    call.restype = ctypes.c_int
    if call(*args):
        raise GreaError('PUBLICATION_FAILED','Atomic publication refused; staged project retained.',
                        details={'errno':ctypes.get_errno()})


def private_directory(parent=None,prefix='grea-'):
    """Owner-private staging; include the current lowbox SID only when needed."""
    import tempfile,re
    from .paths import in_appcontainer
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,64}',prefix):raise ValueError('Invalid staging prefix')
    if in_appcontainer():
        from .windows_security import private_directory as create
        return create(Path(parent or tempfile.gettempdir()).resolve(strict=True),prefix)
    return Path(tempfile.mkdtemp(prefix=prefix,dir=parent))


@contextlib.contextmanager
def temporary_directory(prefix='grea-',dir=None):
    import shutil
    path=private_directory(dir,prefix)
    try:yield str(path)
    finally:shutil.rmtree(path)
