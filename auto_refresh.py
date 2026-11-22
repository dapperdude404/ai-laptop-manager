"""V2.4 lightweight, optional dashboard/process auto-refresh.

Only psutil-backed snapshots are queried. Never triggers file scans,
elevation prompts, recovery, CHKDSK, repair or deletion.
"""
from __future__ import annotations
import time
import tkinter as tk
from tkinter import ttk
import maintenance as m

INTERVALS = (10, 30, 60)

def valid_interval(value):
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        raise ValueError("Choose 10, 30 or 60 seconds.") from None
    if parsed not in INTERVALS:
        raise ValueError("Choose 10, 30 or 60 seconds.")
    return parsed

def should_refresh(*, enabled, elapsed, interval, busy):
    return bool(enabled and not busy and elapsed >= valid_interval(interval))

class AutoRefreshMixin:
    def add_auto_refresh(self):
        page = self.views["Dashboard"]
        bar = tk.Frame(page, bg="#101522")
        bar.pack(fill="x", padx=10, pady=(4, 4), before=self.metrics)
        self.auto_enabled = tk.BooleanVar(value=True)
        self.auto_interval = tk.StringVar(value="30")
        self.auto_busy = False
        self.auto_last = time.monotonic()
        tk.Checkbutton(bar, text="Automatic refresh (lightweight)", variable=self.auto_enabled,
                       bg="#101522", fg="#ecf3ff", selectcolor="#253047",
                       activebackground="#101522", activeforeground="#ecf3ff",
                       command=self.auto_refresh_toggle).pack(side="left", padx=(0, 14))
        tk.Label(bar, text="Every", bg="#101522", fg="#afc0d6").pack(side="left")
        ttk.Combobox(bar, textvariable=self.auto_interval, values=["10", "30", "60"],
                     state="readonly", width=5).pack(side="left", padx=6)
        tk.Label(bar, text="seconds  •  dashboard and open Processes tab only",
                 bg="#101522", fg="#afc0d6").pack(side="left")
        self.auto_note = tk.Label(page, text="Auto refresh: on (every 30 seconds)",
                                  bg="#101522", fg="#afc0d6", anchor="w")
        self.auto_note.pack(fill="x", padx=10, pady=(0, 3), before=self.metrics)
        self.after(1000, self.auto_refresh_tick)

    def auto_refresh_toggle(self):
        # Reset the clock on resume: do not burst queries from a long pause.
        self.auto_last = time.monotonic()
        self.auto_note.configure(
            text=("Auto refresh: on (every " + self.auto_interval.get() + " seconds)"
                  if self.auto_enabled.get() else "Auto refresh: paused")
        )

    def auto_refresh_tick(self):
        if not self.winfo_exists():
            return
        try:
            elapsed = time.monotonic() - self.auto_last
            interval = valid_interval(self.auto_interval.get())
            if should_refresh(enabled=self.auto_enabled.get(), elapsed=elapsed,
                              interval=interval, busy=self.auto_busy):
                self.auto_last = time.monotonic()
                self.auto_busy = True
                processes_visible = self.tabs.select() == str(self.views["Processes"])
                def snapshot():
                    try:
                        data = m.system_snapshot()
                        processes = m.top_processes() if processes_visible else None
                        return {"snapshot": data, "processes": processes}
                    except Exception as exc:
                        return {"error": str(exc)}
                self.submit("Automatic health snapshot", snapshot, self.auto_show)
        finally:
            if self.winfo_exists():
                self.after(1000, self.auto_refresh_tick)

    def auto_show(self, value):
        self.auto_busy = False
        if "error" in value:
            self.auto_note.configure(text="Automatic refresh unavailable: " + value["error"][:160])
            return
        self.show_dashboard(value["snapshot"])
        if value["processes"] is not None:
            self.show_processes(value["processes"])
        self.auto_note.configure(text="Auto refresh: updated at " +
                                 time.strftime("%H:%M:%S") +
                                 " (every " + self.auto_interval.get() + " seconds)")
