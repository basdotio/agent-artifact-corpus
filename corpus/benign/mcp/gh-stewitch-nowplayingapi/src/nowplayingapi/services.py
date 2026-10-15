import time
import win32gui
import win32process
import pythoncom
from typing import Optional, List, Tuple
from pycaw.pycaw import AudioUtilities

from .models import SongInfo
from .config import settings

_cache: Optional[Tuple[float, List[SongInfo]]] = None

def get_now_playing_info() -> List[SongInfo]:
    """
    The main service function that finds and returns song information.
    Uses a simple time-to-live (TTL) cache.
    """
    global _cache
    current_time = time.monotonic()
    
    if _cache is not None:
        cached_time, cached_data = _cache
        if (current_time - cached_time) < settings.CACHE_TTL_SECONDS:
            return cached_data
            
    print("Cache miss or expired. Performing full scan...")
    song_list = _scan_for_music()
    _cache = (current_time, song_list)
    return song_list


def _scan_for_music() -> List[SongInfo]:
    """
    Performs the actual scanning of audio processes and window titles.
    This function now correctly handles COM initialization for the thread it runs in.
    """
    # Initialize COM for this thread.
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    
    try:
        results: List[SongInfo] = []
        audio_processes = _get_all_audio_processes()
        for pid, name in audio_processes:
            if name.lower() in settings.TARGET_PROCESS_NAMES:
                windows = _find_windows_by_pid(pid)
                for _, title in windows:
                    results.append(SongInfo(process_name=name, song_title=title.strip()))
        return results
    except Exception as e:
        print(f"ERROR: An exception occurred during the scan: {e}")
        return []
    finally:
        # Uninitialize COM when the work is done.
        pythoncom.CoUninitialize()


def _get_all_audio_processes() -> List[Tuple[int, str]]:
    """
    Retrieves a list of (pid, name) for processes with active audio sessions.
    NOTE: This function is called from within the COM-initialized context of _scan_for_music.
    """
    sessions = AudioUtilities.GetAllSessions()
    return [
        (session.Process.pid, session.Process.name())
        for session in sessions
        if session.Process and session.Process.name()
    ]


def _find_windows_by_pid(target_pid: int) -> List[Tuple[int, str]]:
    """
    Finds all visible windows (hwnd, title) associated with a given PID.
    """
    windows_list: List[Tuple[int, str]] = []

    def enum_windows_callback(hwnd: int, _) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == target_pid:
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows_list.append((hwnd, title))
        return True

    win32gui.EnumWindows(enum_windows_callback, None)
    return windows_list