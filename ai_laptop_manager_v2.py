"""V2 desktop preview; extends V1 without replacing existing features."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app import LaptopManager
from ui_compat import BG, SURFACE, SURFACE2, FG, ACCENT, MUTED, label, button
from maintenance import human_bytes
from usb_diagnostics import inventory_windows
from future_core import (
    RECOVERY_EXTENSIONS, REPAIR_PRESETS, copy_file_no_overwrite,
    get_wallpaper, list_directory, partition_overview, recovery_plan,
    repair_command, run_readonly_diagnostic, set_wallpaper, volume_overview,
)


from storage_insights_gui import StorageInsightsMixin


class FutureLaptopManager(StorageInsightsMixin, LaptopManager):
    """A nested tools workspace preserves all V1 features."""

    def __init__(self):
        super().__init__()
        self.notebook = self.tabs
        self.build()

    def headline(self, parent, title, detail):
        label(parent, title, size=17, bold=True).pack(anchor="w", padx=10, pady=(12, 4))
        label(parent, detail, color=MUTED, wraplength=1000,
              justify="left").pack(anchor="w", padx=10, pady=(0, 10))

    def tree(self, parent, columns, widths):
        area = tk.Frame(parent, bg=BG)
        area.pack(fill="both", expand=True, pady=5)
        widget = ttk.Treeview(area, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            widget.heading(col, text=col)
            widget.column(col, width=width, minwidth=75, stretch=col == columns[-1])
        bar = ttk.Scrollbar(area, orient="vertical", command=widget.yview)
        widget.configure(yscrollcommand=bar.set)
        widget.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        return widget

    def job(self, title, callback, on_success):
        self.submit(title, callback, on_success)
    def build(self):
        # V1 builds its interface inside LaptopManager.__init__, not build().
        self.title("AI Laptop Manager V2.3 Preview — USB & SSD Diagnostics")
        self.geometry("1220x820")
        self.minsize(980, 650)
        parent = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(parent, text="Future Tools")
        label(parent, "FUTURE TOOLS V2", size=17, color=ACCENT, bold=True).pack(anchor="w", padx=12, pady=(12, 4))
        label(parent, "Local-first • Read-only diagnostics • Manual approval before any changes",
              color=MUTED).pack(anchor="w", padx=12, pady=(0, 8))
        self.future = ttk.Notebook(parent)
        self.future.pack(fill="both", expand=True, padx=12, pady=12)
        for name, build in (
            ("File Manager", self.build_files), ("Disks & USB", self.build_disks),
            ("Repair Center", self.build_repair), ("Recovery Studio", self.build_recovery),
            ("RAM & Registry", self.build_memory), ("Wallpaper", self.build_wallpaper),
        ):
            pane = tk.Frame(self.future, bg=BG)
            self.future.add(pane, text=name)
            build(pane)
        self.add_storage_insights_tab()

    def note(self, parent, value):
        label(parent, value, color=MUTED, wraplength=1070, justify="left").pack(
            anchor="w", padx=10, pady=(9, 7))

    @staticmethod
    def set_text(widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.configure(state="disabled")

    def output(self, parent):
        widget = tk.Text(parent, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", wrap="word", font=("Consolas", 10),
                         padx=15, pady=12)
        widget.pack(fill="both", expand=True, padx=10, pady=9)
        return widget

    def clipboard_command(self, command):
        self.clipboard_clear()
        self.clipboard_append(command)
        messagebox.showinfo("Copied", "Command copied for review. Nothing has been executed.")

    # FILE MANAGER
    def build_files(self, parent):
        self.headline(parent, "Built-in file manager",
                      "Browse locally and copy a single file. Never overwrite, move, or delete your files.")
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=10)
        self.folder = tk.StringVar(value=str(Path.home()))
        entry = tk.Entry(top, textvariable=self.folder, bg=SURFACE2, fg=FG,
                         insertbackground=FG, relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=11)
        entry.bind("<Return>", lambda event: self.refresh_files())
        button(top, "Go", self.refresh_files).pack(side="left", padx=(8, 0))
        button(top, "Up", self.up_folder).pack(side="left", padx=(8, 0))
        button(top, "Browse", self.choose_folder).pack(side="left", padx=(8, 0))
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=10, pady=8)
        button(bar, "Open selected folder", self.open_folder).pack(side="left")
        button(bar, "Copy selected file...", self.copy_selected).pack(side="left", padx=10)
        self.file_status = label(parent, "Choose a folder. Listing is read-only.", color=MUTED)
        self.file_status.pack(anchor="w", padx=10)
        self.file_tree = self.tree(parent, ("Type", "Size", "Modified", "Name"),
                                  (110, 120, 160, 620))
        self.file_map = {}

    def choose_folder(self):
        root = filedialog.askdirectory(title="Browse a folder", initialdir=str(Path.home()))
        if root:
            self.folder.set(root)
            self.refresh_files()

    def up_folder(self):
        self.folder.set(str(Path(self.folder.get()).parent))
        self.refresh_files()

    def refresh_files(self):
        root = self.folder.get()
        self.job("List folder", lambda: list_directory(root), self.show_directory_files)

    def show_directory_files(self, result):
        root, items, clipped = result
        self.folder.set(root)
        self.file_tree.delete(*self.file_tree.get_children())
        self.file_map.clear()
        for item in items:
            row = self.file_tree.insert("", "end",
                values=(item["type"], human_bytes(item["size"]) if item["size"] is not None else "—",
                        item["modified"], item["name"]))
            self.file_map[row] = item
        self.file_status.configure(text=f"{len(items)} entries • {root}" +
                                   (" • showing first 600 entries" if clipped else ""))

    def selected_item(self):
        selected = self.file_tree.selection()
        return self.file_map.get(selected[0]) if selected else None

    def open_folder(self):
        item = self.selected_item()
        if item is None:
            messagebox.showinfo("Select item", "Choose an entry first.")
        elif item["type"] == "Folder":
            self.folder.set(item["path"])
            self.refresh_files()
        elif os.name == "nt":
            subprocess.Popen(["explorer.exe", "/select,", item["path"]])
        else:
            messagebox.showinfo("Windows", "Explorer is Windows-only.")

    def copy_selected(self):
        item = self.selected_item()
        if not item or item["type"] != "File":
            messagebox.showwarning("Ordinary file needed", "Choose an ordinary file, not a folder or link.")
            return
        target = filedialog.askdirectory(title="Choose existing destination directory")
        if not target:
            return
        if not messagebox.askyesno("Confirm file copy",
              f"Copy:\n{item['path']}\n\nTo folder:\n{target}\n\nOriginal will stay. Existing files cannot be replaced."):
            return
        self.job("Copy file", lambda: copy_file_no_overwrite(item["path"], target),
                 lambda path: messagebox.showinfo("Copied", f"Copy created:\n{path}"))

    # PARTITIONS AND USB
    def build_disks(self, parent):
        self.headline(parent, "Disk, partitions & removable-media inspector",
                      "Read-only volume capacity and Windows partition inventory.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=10)
        button(bar, "Refresh volumes and partitions", self.refresh_disks).pack(side="left")
        button(bar, "Read-only USB / SSD health", self.inspect_usb_health).pack(side="left", padx=10)
        button(bar, "Browse selected drive", self.browse_drive).pack(side="left", padx=10)
        self.note(parent, "USB devices may have no drive letter or be unreadable. A 'Healthy' indicator is not a complete "
                          "SSD SMART assessment. Never format or initialize a device to recover lost files.")
        self.drive_tree = self.tree(parent,
              ("Drive", "File system", "Capacity", "Available", "Used", "Partition"),
              (110, 130, 130, 130, 100, 350))
        self.volume_map = {}

    def refresh_disks(self):
        self.job("Drive details", lambda: (volume_overview(), partition_overview()), self.show_disks_v2)

    def show_disks_v2(self, value):
        volumes, (status, parts) = value
        self.drive_tree.delete(*self.drive_tree.get_children())
        self.volume_map.clear()
        partition_by_letter = {
            str(p.get("DriveLetter", "")).upper(): p for p in parts if p.get("DriveLetter")
        }
        for volume in volumes:
            drive = volume["drive"]
            letter = drive[:1].upper()
            p = partition_by_letter.get(letter)
            ptext = (f"Disk {p['DiskNumber']}, partition {p['PartitionNumber']}" if p else "Unknown / removable")
            row = self.drive_tree.insert("", "end", values=(
                drive, volume["fs"], human_bytes(volume["total"]),
                human_bytes(volume["free"]), f"{volume['used_percent']:.0f}%", ptext))
            self.volume_map[row] = drive
        self.status.configure(text=f"{len(volumes)} volumes, {len(parts)} partitions. {status}")

    def inspect_usb_health(self):
        """Windows provider snapshot, not full SMART or a recovery operation."""
        if os.name != "nt":
            messagebox.showinfo("Windows-only", "Disk inventory requires Windows.")
            return
        self.job("USB / SSD health inventory", inventory_windows, self.show_usb_health)

    def show_usb_health(self, result):
        window = tk.Toplevel(self)
        window.title("V2.3 Read-only USB / SSD Inventory")
        window.geometry("940x650")
        window.configure(bg=BG)
        output = tk.Text(window, bg=SURFACE, fg=FG, wrap="word",
                         font=("Consolas", 10), padx=14, pady=12)
        output.pack(fill="both", expand=True, padx=12, pady=12)
        output.insert("end", "READ-ONLY STORAGE PROVIDER SNAPSHOT\n\n")
        for disk in result["disks"]:
            output.insert("end", f"Disk {disk['disk_number']} — {disk['name']}\n")
            output.insert("end", f"  Bus: {disk['bus_type']} | Provider health: {disk['health']} | "
                                 f"Operational: {disk['operational']}\n")
            output.insert("end", f"  Capacity: {human_bytes(disk['size_bytes']) if disk['size_bytes'] is not None else 'Unknown'}\n")
            for p in disk["partitions"]:
                output.insert("end", f"  Partition {p['partition']}: {p['letter'] or '(no drive letter)'}"
                                     f" | {p['filesystem']} | {p['volume_health']}\n")
            for warning in disk["alerts"]:
                output.insert("end", "  WARNING: " + warning + "\n")
            output.insert("end", "\n")
        output.insert("end", result["limitations"] + "\nNo drives were modified.")
        output.configure(state="disabled")

    def browse_drive(self):
        selection = self.drive_tree.selection()
        if not selection:
            messagebox.showinfo("Select drive", "Choose a mounted drive first.")
            return
        self.folder.set(self.volume_map[selection[0]])
        self.future.select(0)
        self.refresh_files()

    # WINDOWS REPAIR COMMAND PREVIEWS
    def build_repair(self, parent):
        self.headline(parent, "Windows repair center",
                      "Trusted diagnostic presets only. Repairs remain manual, not automatic.")
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=10)
        choices = list(REPAIR_PRESETS) + ["CHKDSK read-only"]
        self.repair_name = tk.StringVar(value=choices[0])
        ttk.Combobox(top, textvariable=self.repair_name, values=choices,
                     state="readonly", width=27).pack(side="left")
        label(top, "Drive:", color=MUTED).pack(side="left", padx=(12, 4))
        self.check_drive = tk.StringVar(value="C:")
        tk.Entry(top, textvariable=self.check_drive, width=5,
                 bg=SURFACE2, fg=FG).pack(side="left")
        button(top, "Preview command", self.preview_repair).pack(side="left", padx=8)
        button(top, "Run READ-ONLY", self.run_check).pack(side="left")
        button(top, "Copy command", self.copy_check).pack(side="left", padx=8)
        self.note(parent, "Only allowlisted scan commands can run in-app. SFC /scannow and DISM RestoreHealth modify "
                          "Windows and must be run manually after a backup. On a failed SSD/USB, avoid CHKDSK repairs.")
        self.repair_log = self.output(parent)
        self.repair_plan = None

    def preview_repair(self):
        try:
            p = repair_command(self.repair_name.get(), drive=self.check_drive.get())
        except ValueError as exc:
            self.repair_plan = None
            messagebox.showerror("Invalid choice", str(exc))
            return
        self.repair_plan = p
        level = "Read-only preset" if p["read_only"] else "MODIFYING command: MANUAL ONLY"
        self.set_text(self.repair_log,
            f"{level}\n\n{p['info']}\n\nCommand: {p['command']}\n\nNo command has run.")
    
    def run_check(self):
        self.preview_repair()
        p = self.repair_plan
        if not p:
            return
        if not p["read_only"]:
            messagebox.showwarning("Blocked", "Modifying repairs cannot run from this app.")
            return
        if not messagebox.askyesno("Confirm read-only scan", f"Run {p['command']}?\nAdministrator rights may be required."):
            return
        self.job("Read-only repair diagnostic",
                 lambda: run_readonly_diagnostic(self.repair_name.get(), drive=self.check_drive.get()),
                 lambda result: self.set_text(self.repair_log, json.dumps(result, indent=2)))

    def copy_check(self):
        self.preview_repair()
        if self.repair_plan:
            self.clipboard_command(self.repair_plan["command"])

    # DATA RECOVERY (PREVIEW ONLY)
    def build_recovery(self, parent):
        self.headline(parent, "Photo, video & document recovery studio",
                      "Generate a Microsoft Windows File Recovery command, never silently run it.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=10)
        self.recovery_from = tk.StringVar(value="")
        self.recovery_to = tk.StringVar(value="")
        self.recovery_files = tk.StringVar(value="Photos + videos")
        self.recovery_mode = tk.StringVar(value="extensive")
        for caption, var, choices, width in (
            ("Lost from", self.recovery_from, None, 5),
            ("Save to", self.recovery_to, None, 5),
            ("File types", self.recovery_files, list(RECOVERY_EXTENSIONS), 17),
            ("Mode", self.recovery_mode, ["regular", "extensive"], 11),
        ):
            label(bar, caption + ":", color=MUTED).pack(side="left", padx=(0, 4))
            if choices:
                ttk.Combobox(bar, textvariable=var, values=choices,
                             state="readonly", width=width).pack(side="left", padx=(0, 10))
            else:
                tk.Entry(bar, textvariable=var, width=width, bg=SURFACE2,
                         fg=FG).pack(side="left", padx=(0, 10))
        buttons = tk.Frame(parent, bg=BG)
        buttons.pack(fill="x", padx=10, pady=9)
        button(buttons, "Preview recovery plan", self.preview_recovery).pack(side="left")
        button(buttons, "Copy command", self.copy_recovery).pack(side="left", padx=9)
        button(buttons, "Official recovery instructions", self.open_recovery_doc).pack(side="left")
        self.note(parent, "STOP USING THE SOURCE DEVICE after loss. Recover to a different drive, ideally another physical disk. "
                          "Do not format, write to, or repair the recovery source. SSD TRIM and overwritten sectors may "
                          "make recovery impossible. Physically failing media should be imaged by specialists.")
        self.recovery_log = self.output(parent)
        self.set_text(self.recovery_log, "Prepare a recovery plan. No data recovery will be performed by this preview.")
        self.recovery_plan = None

    def preview_recovery(self):
        try:
            plan = recovery_plan(self.recovery_from.get(), self.recovery_to.get(),
                 self.recovery_files.get(), mode=self.recovery_mode.get())
        except ValueError as exc:
            self.recovery_plan = None
            messagebox.showerror("Invalid recovery plan", str(exc))
            return
        self.recovery_plan = plan
        self.set_text(self.recovery_log, f"NOT EXECUTED\n\n{plan['command']}\n\n{plan['note']}\n\n"
                       "This requires Microsoft's separately installed Windows File Recovery.")

    def copy_recovery(self):
        self.preview_recovery()
        if self.recovery_plan:
            self.clipboard_command(self.recovery_plan["command"])

    @staticmethod
    def open_recovery_doc():
        import webbrowser
        webbrowser.open("https://support.microsoft.com/en-us/windows/experience/backup-recovery/windows-file-recovery")

    # RAM / REGISTRY
    def build_memory(self, parent):
        self.headline(parent, "RAM optimization & registry safety",
                      "No fake RAM boosts and no automated registry 'cleanup'.")
        self.note(parent, "Windows uses available RAM for beneficial caching; forcibly clearing it usually does "
                          "not improve performance. Review large applications and close them normally. "
                          "Registry edits are intentionally blocked in V2 preview.")
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=10)
        button(top, "Inspect memory processes",
               lambda: self.notebook.select(self.views["Processes"])).pack(side="left")
        button(top, "Open Task Manager", self.open_taskmgr).pack(side="left", padx=9)
        button(top, "Open Registry Editor (manual)", self.open_regedit).pack(side="left")
        self.note(parent, "Safeguards: no registry writes, no background cleanup, no forced termination of "
                          "antivirus or Windows processes, no silent command shells, and no automatic partition changes.")

    @staticmethod
    def open_taskmgr():
        if os.name == "nt":
            subprocess.Popen(["taskmgr.exe"])
        else:
            messagebox.showinfo("Windows-only", "Task Manager requires Windows.")

    @staticmethod
    def open_regedit():
        if os.name != "nt":
            messagebox.showinfo("Windows-only", "Registry Editor requires Windows.")
        elif messagebox.askyesno("Advanced Windows tool", "Opening Registry Editor may allow risky manual "
                                 "changes. Back up your files and registry first. Open anyway?"):
            subprocess.Popen(["regedit.exe"])

    # WALLPAPER
    def build_wallpaper(self, parent):
        self.headline(parent, "Wallpaper studio",
                      "Choose a local image and confirm before applying it to your Windows desktop.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=10)
        self.wallpaper_path = tk.StringVar()
        tk.Entry(bar, textvariable=self.wallpaper_path, bg=SURFACE2, fg=FG,
                 insertbackground=FG, relief="flat").pack(side="left", expand=True, fill="x", ipady=10)
        button(bar, "Choose image", self.choose_wallpaper).pack(side="left", padx=9)
        button(bar, "Apply with confirmation", self.apply_wallpaper).pack(side="left")
        self.wallpaper_note = label(parent, "JPG, PNG, BMP. No images uploaded.", color=MUTED)
        self.wallpaper_note.pack(anchor="w", padx=10, pady=16)

    def choose_wallpaper(self):
        name = filedialog.askopenfilename(
            filetypes=[("Pictures", "*.jpg *.jpeg *.png *.bmp")])
        if name:
            self.wallpaper_path.set(name)

    def apply_wallpaper(self):
        name = self.wallpaper_path.get()
        if not name:
            messagebox.showinfo("Choose image", "Pick a local image first.")
            return
        if not messagebox.askyesno("Apply wallpaper?", f"Change your wallpaper to:\n{name}?"):
            return
        try:
            previous = get_wallpaper()
            set_wallpaper(name)
            self.wallpaper_note.config(text=f"Wallpaper applied. Previous path: {previous or '(unknown)'}")
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Wallpaper error", str(exc))


if __name__ == "__main__":
    FutureLaptopManager().mainloop()
