"""V2 opt-in, local-only Windows tools. No arbitrary shell and no registry writes.

Disk repair and recovery are deliberately preview-only. Never run CHKDSK /F,
format, diskpart, REG ADD or data recovery from this module.
"""
from __future__ import annotations

import ctypes
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Sequence

import psutil

MAX_ITEMS = 600
_IMAGE = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.gif", "*.bmp")
_VIDEO = ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.3gp")
_DOCUMENT = ("*.pdf", "*.docx", "*.xlsx", "*.txt", "*.pptx")
RECOVERY_EXTENSIONS = {"Photos": _IMAGE, "Videos": _VIDEO, "Documents": _DOCUMENT,
                       "Photos + videos": _IMAGE + _VIDEO}


def _safe_letter(value: str) -> str:
    """Accept only a drive letter optionally followed by one colon/backslash."""
    text = str(value).strip().upper()
    if not re.fullmatch(r"[A-Z](?::(?:\\)?)?", text):
        raise ValueError("Choose a simple Windows drive letter such as E: (not a path or command).")
    return text[0]


def recovery_plan(source: str, destination: str, kind: str, *, mode: str = "extensive") -> dict:
    """Create a command for Microsoft Windows File Recovery; NEVER execute it."""
    src, dst = _safe_letter(source), _safe_letter(destination)
    if src == dst:
        raise ValueError("Source and destination must be on different drive letters.")
    if kind not in RECOVERY_EXTENSIONS:
        raise ValueError("Select a supported file group.")
    if mode not in ("regular", "extensive"):
        raise ValueError("Unsupported recovery mode.")
    options = " ".join(f"/n {pattern}" for pattern in RECOVERY_EXTENSIONS[kind])
    cmd = f"winfr {src}: {dst}: /{mode} {options}"
    return {"command": cmd, "source": src + ":", "destination": dst + ":", "mode": mode,
            "note": ("Preview only. Stop using the source device immediately if files were deleted. "
                     "Prefer a separate physical disk as destination. Install Microsoft's Windows File Recovery "
                     "before running this in an elevated terminal. Success is never guaranteed; SSD TRIM "
                     "and overwritten sectors can prevent recovery. If the drive is clicking, disconnecting "
                     "or physically failing, consult a professional before attempting scans.")}


def list_directory(folder: str | Path) -> tuple[str, list[dict], bool]:
    """Read one directory only; do not traverse junctions or symbolic links."""
    root = Path(folder).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    rows = []
    truncated = False
    with os.scandir(root) as scanner:
        for i, entry in enumerate(scanner):
            if i >= MAX_ITEMS:
                truncated = True
                break
            try:
                info = entry.stat(follow_symlinks=False)
                kind = "Link/junction" if (entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400) else (
                    "Folder" if stat.S_ISDIR(info.st_mode) else "File")
                rows.append({"name": entry.name, "type": kind, "size": info.st_size if kind == "File" else None,
                             "modified": dt.datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M"),
                             "path": str(Path(entry.path))})
            except (PermissionError, OSError):
                continue
    rows.sort(key=lambda x: (x["type"] != "Folder", x["name"].casefold()))
    return str(root), rows, truncated


def copy_file_no_overwrite(source: str | Path, destination_folder: str | Path) -> Path:
    """Copy a single regular file; reject symlinks and overwrite, never move originals."""
    src = Path(source)
    info = src.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("Only ordinary files can be copied. Links and junctions are excluded.")
    dest = Path(destination_folder).expanduser().resolve(strict=True)
    if not dest.is_dir():
        raise NotADirectoryError(str(dest))
    target = dest / src.name
    if target.exists() or target.is_symlink():
        raise FileExistsError("Destination already contains that filename. No files were overwritten.")
    # Exclusive creation is atomic and avoids overwrite if another process creates the file.
    with src.open("rb") as inp, target.open("xb") as out:
        try:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
        except BaseException:
            out.close()
            target.unlink(missing_ok=True)
            raise
    shutil.copystat(src, target, follow_symlinks=False)
    return target


def volume_overview() -> list[dict]:
    """Filesystem volume summary including removable/USB-style mountpoints if mounted."""
    found = []
    seen = set()
    for vol in psutil.disk_partitions(all=True):
        drive = vol.mountpoint
        key = drive.casefold()
        if key in seen or not drive:
            continue
        seen.add(key)
        if not vol.fstype and not Path(drive).exists():
            continue
        try:
            usage = psutil.disk_usage(drive)
        except (PermissionError, OSError):
            continue
        found.append({"drive": drive, "device": vol.device, "fs": vol.fstype or "Unknown",
                      "total": usage.total, "free": usage.free, "used_percent": usage.percent,
                      "options": vol.opts})
    return sorted(found, key=lambda d: d["drive"].lower())


def partition_overview() -> tuple[str, list[dict]]:
    """Read-only Get-Partition details, no diskpart/format/Initialize-Disk."""
    if os.name != "nt":
        return "Windows-only partition provider", []
    script = ("Get-Partition | Select-Object DiskNumber,PartitionNumber,DriveLetter,"
              "Type,Size,IsBoot,IsSystem | ConvertTo-Json -Depth 3 -Compress")
    try:
        p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                           timeout=20, capture_output=True, text=True, creationflags=0x08000000)
        if p.returncode != 0 or not p.stdout.strip():
            return "Partition information unavailable or access restricted", []
        result = json.loads(p.stdout)
        return "Read-only PowerShell Get-Partition results", result if isinstance(result, list) else [result]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "Partition information unavailable", []


REPAIR_PRESETS = {
    "DISM quick check": {"args": ["DISM.exe", "/Online", "/Cleanup-Image", "/CheckHealth"],
                         "read_only": True, "info": "Read corruption state without repairing the Windows image."},
    "DISM thorough scan": {"args": ["DISM.exe", "/Online", "/Cleanup-Image", "/ScanHealth"],
                           "read_only": True, "info": "Slower component-store health scan; does not repair."},
    "SFC verification": {"args": ["sfc.exe", "/verifyonly"], "read_only": True,
                         "info": "Verify protected system files; no automatic repair."},
    "DISM repair (manual)": {"args": ["DISM.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"],
                             "read_only": False, "info": "Modifies Windows components. Requires user-run elevated terminal."},
    "SFC repair (manual)": {"args": ["sfc.exe", "/scannow"], "read_only": False,
                            "info": "Repairs protected Windows files. Requires user-run elevated terminal."},
}


def repair_command(name: str, *, drive: str | None = None) -> dict:
    """Strict preset-only commands. CHKDSK scan is non-repairing."""
    if name == "CHKDSK read-only":
        letter = _safe_letter(drive or "")
        args = ["chkdsk.exe", letter + ":"]
        return {"args": args, "command": " ".join(args), "read_only": True,
                "info": "Read-only filesystem check. Never run /f or /r on a recovery source."}
    if name not in REPAIR_PRESETS:
        raise ValueError("Unknown diagnostic preset; arbitrary commands are not accepted.")
    entry = REPAIR_PRESETS[name]
    return {**entry, "command": " ".join(entry["args"])}


def run_readonly_diagnostic(name: str, *, drive: str | None = None, timeout: int = 600) -> dict:
    """Run only a whitelisted read-only preset, without cmd.exe, shell or elevation."""
    if os.name != "nt":
        raise RuntimeError("Windows only")
    task = repair_command(name, drive=drive)
    if not task["read_only"]:
        raise PermissionError("Repair commands are preview-only and must be run manually by the user.")
    run = subprocess.run(task["args"], timeout=timeout, capture_output=True, text=True,
                         errors="replace", creationflags=0x08000000, shell=False)
    return {"command": task["command"], "exit_code": run.returncode,
            "output": (run.stdout + "\n" + run.stderr)[-18000:]}


def get_wallpaper() -> str:
    """Windows desktop wallpaper path (may be empty for theme backgrounds)."""
    if os.name != "nt":
        return ""
    buffer = ctypes.create_unicode_buffer(32768)
    ok = ctypes.windll.user32.SystemParametersInfoW(0x0073, len(buffer), buffer, 0)
    return buffer.value if ok else ""


def set_wallpaper(path: str | Path) -> None:
    """User-confirmed only; Windows changes just the current user's wallpaper."""
    if os.name != "nt":
        raise RuntimeError("Windows only")
    candidate = Path(path).expanduser().resolve(strict=True)
    if not candidate.is_file() or candidate.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
        raise ValueError("Choose an existing JPG, PNG, or BMP image")
    if ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, str(candidate), 0x0001 | 0x0002) == 0:
        raise OSError("Windows could not apply that wallpaper")