"""Inject text into the focused application.

Default method: put text on the clipboard, send Ctrl+V via SendInput,
then restore the previous clipboard text. Fast, unicode-safe, works in
almost every app. Fallback: character-by-character KEYEVENTF_UNICODE
typing for apps that block paste.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_V = 0x56

_MODIFIER_VKS = (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN)

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class _INPUT_UNION(ctypes.Union):
    _fields_ = (("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = (("type", wintypes.DWORD), ("u", _INPUT_UNION))


def _key_input(vk: int = 0, scan: int = 0, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    return inp


def _send(inputs: list[INPUT]) -> None:
    if not inputs:
        return
    array = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise ctypes.WinError(ctypes.get_last_error())


def wait_modifiers_released(timeout: float = 2.0) -> bool:
    """Block until Ctrl/Shift/Alt/Win are all physically up, so our paste
    isn't turned into Win+V or Ctrl+Shift+V by keys the user still holds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(not (user32.GetAsyncKeyState(vk) & 0x8000) for vk in _MODIFIER_VKS):
            return True
        time.sleep(0.01)
    return False


def send_ctrl_v() -> None:
    _send([
        _key_input(vk=VK_CONTROL),
        _key_input(vk=VK_V),
        _key_input(vk=VK_V, flags=KEYEVENTF_KEYUP),
        _key_input(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP),
    ])


def type_text(text: str, chunk: int = 40, delay: float = 0.005) -> None:
    """Send text as KEYEVENTF_UNICODE events (handles emoji via surrogates)."""
    batch: list[INPUT] = []
    for ch in text:
        if ch == "\n":
            batch.append(_key_input(vk=VK_RETURN))
            batch.append(_key_input(vk=VK_RETURN, flags=KEYEVENTF_KEYUP))
        elif ch == "\t":
            batch.append(_key_input(vk=VK_TAB))
            batch.append(_key_input(vk=VK_TAB, flags=KEYEVENTF_KEYUP))
        elif ch == "\r":
            continue
        else:
            for unit in _utf16_units(ch):
                batch.append(_key_input(scan=unit, flags=KEYEVENTF_UNICODE))
                batch.append(_key_input(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        if len(batch) >= chunk * 2:
            _send(batch)
            batch = []
            time.sleep(delay)
    _send(batch)


def _utf16_units(ch: str) -> list[int]:
    raw = ch.encode("utf-16-le")
    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]


def _open_clipboard(retries: int = 10) -> None:
    import win32clipboard

    for attempt in range(retries):
        try:
            win32clipboard.OpenClipboard()
            return
        except Exception:
            time.sleep(0.03 * (attempt + 1))
    win32clipboard.OpenClipboard()  # final attempt, let it raise


def get_clipboard_text() -> str | None:
    import win32clipboard

    _open_clipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        return None
    finally:
        win32clipboard.CloseClipboard()


def set_clipboard_text(text: str) -> None:
    import win32clipboard

    _open_clipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    previous = get_clipboard_text() if restore_clipboard else None
    set_clipboard_text(text)
    time.sleep(0.03)
    send_ctrl_v()
    time.sleep(0.18)  # give the target app time to read the clipboard
    if restore_clipboard and previous is not None:
        try:
            set_clipboard_text(previous)
        except Exception:
            pass


def inject_text(text: str, method: str = "paste", restore_clipboard: bool = True) -> None:
    if not text:
        return
    wait_modifiers_released()
    if method == "type":
        type_text(text)
        return
    try:
        paste_text(text, restore_clipboard=restore_clipboard)
    except Exception:
        type_text(text)
