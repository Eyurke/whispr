"""Real text injection into a focused window via SendInput.

These run on an interactive desktop only (skipped on CI): a Tk window
grabs foreground focus (verified via GetForegroundWindow, like the app's
real target windows have), we inject text exactly like the app does,
and read back what actually arrived in the widget.

NOTE: run these on an otherwise idle desktop - they compete for
foreground focus, so clicking/typing while they run makes them flaky.
"""

import ctypes
import threading
import tkinter as tk

import pytest

from whispr.inject import (
    KEYEVENTF_KEYUP,
    VK_MENU,
    _key_input,
    _send,
    get_clipboard_text,
    inject_text,
    set_clipboard_text,
)

user32 = ctypes.windll.user32
GA_ROOT = 2


def _alt_tap() -> None:
    """Pressing Alt releases Windows' foreground-lock so SetForegroundWindow works."""
    _send([_key_input(vk=VK_MENU), _key_input(vk=VK_MENU, flags=KEYEVENTF_KEYUP)])


def _run_injection(method: str, text: str) -> str | None:
    """Returns widget content, or None if the desktop refused to focus us."""
    root = tk.Tk()
    root.title(f"whispr-inject-{method}")
    root.attributes("-topmost", True)
    widget = tk.Text(root, width=50, height=6)
    widget.pack()
    received: dict = {}
    state = {"tries": 0}

    def target_hwnd() -> int:
        return user32.GetAncestor(root.winfo_id(), GA_ROOT)

    def finish():
        received["value"] = widget.get("1.0", "end").rstrip("\n")
        root.destroy()

    def abort():
        received["value"] = None
        root.destroy()

    def inject_and_read():
        # Inject from a worker thread exactly like the app does, so the
        # target window's event loop stays free to process the paste.
        threading.Thread(target=lambda: inject_text(text, method=method), daemon=True).start()
        root.after(1500, finish)

    def try_focus():
        if user32.GetForegroundWindow() == target_hwnd():
            widget.focus_set()
            root.after(150, inject_and_read)
            return
        state["tries"] += 1
        if state["tries"] > 40:
            abort()
            return
        _alt_tap()
        user32.SetForegroundWindow(target_hwnd())
        root.lift()
        root.focus_force()
        root.after(100, try_focus)

    root.after(200, try_focus)
    root.mainloop()
    return received.get("value")


def _require(result: str | None) -> str:
    if result is None:
        pytest.skip("could not acquire desktop foreground focus")
    return result


@pytest.mark.e2e
def test_paste_injection_lands_in_focused_widget():
    got = _require(_run_injection("paste", "Hello from Whispr paste. "))
    assert got == "Hello from Whispr paste. "


@pytest.mark.e2e
def test_type_injection_handles_unicode_and_newlines():
    got = _require(_run_injection("type", "héllo wörld\nsecond line"))
    assert got == "héllo wörld\nsecond line"


@pytest.mark.e2e
def test_paste_restores_previous_clipboard():
    set_clipboard_text("previous clipboard contents")
    got = _require(_run_injection("paste", "overwriting text "))
    assert got == "overwriting text "
    assert get_clipboard_text() == "previous clipboard contents"
