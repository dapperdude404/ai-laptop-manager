"""Opt-in Tkinter Storage Insights 2.1 tab for the existing V2 application."""
from __future__ import annotations
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from maintenance import human_bytes
from storage_insights import scan_sizes, find_duplicates
from cleanup_recommendations import make_recommendations

class StorageInsightsMixin:
    def add_storage_insights_tab(self):
        from ui_compat import BG, SURFACE2, FG, MUTED, ACCENT, label, button
        self._insights_palette = (BG, SURFACE2, FG, MUTED, ACCENT)
        page = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(page, text="Storage Insights 2.1")
        self.headline(page, "Storage Insights 2.1",
                      "Cancellable read-only folder sizes and verified duplicate previews. No deletion.")
        toolbar = tk.Frame(page, bg=BG)
        toolbar.pack(fill="x", padx=10)
        self.insights_path = tk.StringVar(value="C:\\" if os.name == "nt" else str(Path.home()))
        tk.Entry(toolbar, textvariable=self.insights_path, bg=SURFACE2, fg=FG,
                 insertbackground=FG, relief="flat").pack(side="left", fill="x",
                                                         expand=True, ipady=10)
        button(toolbar, "Choose", self.insights_choose).pack(side="left", padx=5)
        button(toolbar, "Scan folder", self.insights_start).pack(side="left", padx=5)
        button(toolbar, "Find duplicates", self.insights_start_duplicates).pack(side="left", padx=5)
        button(toolbar, "Cancel", self.insights_cancel_scan).pack(side="left", padx=5)
        button(toolbar, "Review recommendations", self.insights_recommendations).pack(side="left", padx=5)
        self.insights_note = label(page,
                "Choose C:\\ or a user folder. No scan starts automatically.",
                color=MUTED, wraplength=1100, justify="left")
        self.insights_note.pack(anchor="w", padx=10, pady=(10, 5))
        self.insights_spinner = ttk.Progressbar(page, mode="indeterminate")
        self.insights_spinner.pack(fill="x", padx=10)
        pane = tk.PanedWindow(page, orient="vertical", bg=BG, sashwidth=8, bd=0)
        pane.pack(fill="both", expand=True, padx=10, pady=10)
        first = tk.Frame(pane, bg=BG)
        second = tk.Frame(pane, bg=BG)
        pane.add(first, minsize=130)
        pane.add(second, minsize=130)
        label(first, "Folders ranked by logical file lengths, not allocated disk space",
              color=ACCENT).pack(anchor="w")
        self.insights_folders = self.tree(first, ("Size", "File count", "Folder"),
                                         (140, 120, 700))
        label(second, "Largest files or SHA-256 matched duplicate groups",
              color=ACCENT).pack(anchor="w")
        self.insights_largest = self.tree(second, ("Size", "Modified / Hash", "File"),
                                         (140, 160, 700))
        self.insights_events = queue.Queue()
        self.insights_stop = None
        self.insights_running = False
        self.insights_latest_sizes = None
        self.after(200, self.insights_poll)

    def insights_choose(self):
        folder = filedialog.askdirectory(title="Read-only scan", initialdir=str(Path.home()))
        if folder:
            self.insights_path.set(folder)

    def insights_start(self):
        self._insights_launch("sizes")

    def insights_start_duplicates(self):
        if messagebox.askyesno("Hash duplicate candidates?",
              "A read-only duplicate scan may read up to 10 GiB for SHA-256 hashing. "
              "It never deletes anything. Continue?"):
            self._insights_launch("duplicates")

    def _insights_launch(self, kind):
        if self.insights_running:
            messagebox.showinfo("Scan active", "Finish or cancel the current scan first.")
            return
        root = self.insights_path.get().strip()
        if not root or not Path(root).is_dir():
            messagebox.showerror("Invalid folder", "Choose an existing local folder.")
            return
        self.insights_running = True
        self.insights_stop = threading.Event()
        self.insights_spinner.start(16)
        self.insights_note.config(text="Read-only scan running: " + root)
        stop = self.insights_stop
        def progress(snapshot):
            self.insights_events.put(("progress", snapshot))
        def worker():
            try:
                result = (scan_sizes(root, cancel=stop, progress=progress)
                          if kind == "sizes"
                          else find_duplicates(root, cancel=stop, progress=progress))
                self.insights_events.put(("result", (kind, result)))
            except Exception as exc:
                self.insights_events.put(("error", str(exc)))
        threading.Thread(target=worker, name="read-only-storage-scan", daemon=True).start()

    def insights_cancel_scan(self):
        if self.insights_running and self.insights_stop is not None:
            self.insights_stop.set()
            self.insights_note.config(text="Cancellation requested; stopping at next checkpoint.")

    def insights_poll(self):
        try:
            while True:
                kind, payload = self.insights_events.get_nowait()
                if kind == "progress" and self.insights_running:
                    self.insights_note.config(text=f"Scanned {payload['files']:,} files, "
                        f"{payload['dirs']:,} folders; {human_bytes(payload['bytes'])} logical bytes.")
                elif kind == "error":
                    self.insights_running = False
                    self.insights_spinner.stop()
                    self.insights_note.config(text="Scan failed: " + payload)
                elif kind == "result":
                    self.insights_running = False
                    self.insights_spinner.stop()
                    self.insights_show(*payload)
        except queue.Empty:
            pass
        self.after(200, self.insights_poll)

    def insights_show(self, kind, result):
        self.insights_folders.delete(*self.insights_folders.get_children())
        self.insights_largest.delete(*self.insights_largest.get_children())
        if kind == "sizes":
            self.insights_latest_sizes = result
            for item in result["folders"][:180]:
                self.insights_folders.insert("", "end", values=(
                    human_bytes(item["size"]), item["files"], item["path"]))
            for item in result["largest"]:
                self.insights_largest.insert("", "end", values=(
                    human_bytes(item["size"]), item["modified"], item["path"]))
            status = ("complete" if result["complete"]
                      else "INCOMPLETE (" + str(result["reason"]) + ")")
            self.insights_note.config(text=f"Scan {status}: {result['files']:,} files; "
                f"{result['unreadable']} inaccessible entries; {result['links']} links skipped. "
                + result["limitations"])
        else:
            for group in result["groups"]:
                for path in group["paths"]:
                    self.insights_largest.insert("", "end", values=(
                        human_bytes(group["size"]), "SHA256 " + group["sha256"][:12], path))
            status = ("complete" if result["complete"]
                      else "incomplete (" + str(result["reason"]) + ")")
            self.insights_note.config(text=f"Duplicate preview {status}: "
                f"{len(result['groups'])} verified groups; "
                f"{human_bytes(result['hashed_bytes'])} hashed. Nothing modified.")

    def insights_recommendations(self):
        """Show read-only ranked review suggestions after a folder-size scan."""
        if self.insights_latest_sizes is None:
            messagebox.showinfo("Scan first", "Use Scan folder before reviewing recommendations.")
            return
        report = make_recommendations(self.insights_latest_sizes)
        window = tk.Toplevel(self)
        window.title("Storage Recommendations — Review Only")
        window.geometry("980x600")
        window.configure(bg=self._insights_palette[0])
        window.transient(self)
        window.grab_set()
        text = tk.Text(window, wrap="word", bg=self._insights_palette[1],
                       fg=self._insights_palette[2], font=("Consolas", 10),
                       padx=16, pady=16)
        text.pack(expand=True, fill="both", padx=12, pady=12)
        status = "COMPLETE" if report["scan_complete"] else "INCOMPLETE"
        text.insert("end", f"Scan: {status}. Unreadable entries: {report['unreadable']}\\n")
        if not report["scan_complete"]:
            text.insert("end", f"Reason: {report['scan_reason']}\\n")
        text.insert("end", report["disclaimer"] + "\\n\\n")
        for index, row in enumerate(report["folders"], 1):
            text.insert("end", f"{index}. {row['path']}\\n"
                               f"   Logical size: {human_bytes(row['logical_bytes'])}\\n"
                               f"   Category: {row['category']}\\n"
                               f"   Suggested review: {row['advice']}\\n\\n")
        text.configure(state="disabled")
