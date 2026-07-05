"""Small Win32 helpers: DPI awareness, single instance, click-through
overlay styling, and start-with-Windows registration."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "Whispr"

_mutex_handle = None  # keep alive for process lifetime


def set_dpi_aware() -> None:
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def acquire_single_instance(name: str = "Local\\WhisprSingleInstance") -> bool:
    """True if we are the only Whispr; False if another instance holds the mutex."""
    global _mutex_handle
    _mutex_handle = kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def make_overlay_window(hwnd: int) -> None:
    """Tool window that never steals focus from the app being dictated into."""
    get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    style = get_long(hwnd, GWL_EXSTYLE)
    set_long(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)


def _pythonw() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return str(pythonw if pythonw.exists() else exe)


def _launcher_path() -> Path:
    return Path(__file__).resolve().parents[1] / "run_whispr.pyw"


def autostart_command() -> str:
    return f'"{_pythonw()}" "{_launcher_path()}"'


def set_autostart(enabled: bool) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, _RUN_VALUE)
            except FileNotFoundError:
                pass


def get_autostart() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _RUN_VALUE)
            return True
    except FileNotFoundError:
        return False
