"""History window: browse, search, copy and delete past dictations."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

from .history import History


class HistoryWindow:
    def __init__(self, root: tk.Tk, history: History):
        self.history = history

        self.win = tk.Toplevel(root)
        self.win.title("Whispr History")
        self.win.geometry("720x460")
        self.win.attributes("-topmost", True)

        top = ttk.Frame(self.win, padding=(10, 10, 10, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(top, textvariable=self.search_var, width=40).pack(side="left", padx=8)
        ttk.Button(top, text="Clear all…", command=self._clear_all).pack(side="right")

        columns = ("when", "secs", "words", "text")
        self.tree = ttk.Treeview(self.win, columns=columns, show="headings", height=16)
        self.tree.heading("when", text="When")
        self.tree.heading("secs", text="Sec")
        self.tree.heading("words", text="Words")
        self.tree.heading("text", text="Text  (double-click to copy)")
        self.tree.column("when", width=110, stretch=False)
        self.tree.column("secs", width=50, anchor="e", stretch=False)
        self.tree.column("words", width=60, anchor="e", stretch=False)
        self.tree.column("text", width=460)
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.bind("<Double-1>", self._copy_selected)
        self.tree.bind("<Delete>", self._delete_selected)

        self.status = ttk.Label(self.win, padding=(10, 4))
        self.status.pack(fill="x")

        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        search = self.search_var.get().strip() or None
        for entry in self.history.recent(limit=500, search=search):
            when = dt.datetime.fromtimestamp(entry.ts).strftime("%b %d, %H:%M")
            preview = entry.text.replace("\n", " ↵ ")
            self.tree.insert("", "end", iid=str(entry.id),
                             values=(when, f"{entry.duration_s:.0f}", entry.words, preview))
        stats = self.history.stats()
        self.status.configure(
            text=f"{stats['entries']} dictations · {stats['words']} words · "
                 f"average {stats['avg_wpm']:.0f} words/min"
        )

    def _copy_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        entry_id = int(selection[0])
        for entry in self.history.recent(limit=500):
            if entry.id == entry_id:
                self.win.clipboard_clear()
                self.win.clipboard_append(entry.text)
                self.status.configure(text="Copied to clipboard ✓")
                break

    def _delete_selected(self, _event=None) -> None:
        for iid in self.tree.selection():
            self.history.delete(int(iid))
        self.refresh()

    def _clear_all(self) -> None:
        if messagebox.askyesno("Whispr", "Delete all dictation history?", parent=self.win):
            self.history.clear()
            self.refresh()
