"""Read-only storage recommendations from an existing Storage Insights scan.

No files are opened, removed, moved, compressed, or modified by this module.
File sizes are logical sizes, NOT safe-to-reclaim bytes.
"""
from __future__ import annotations

from pathlib import PurePath
import re

GIB = 1024 ** 3
PROTECTED = {
    "windows", "program files", "program files (x86)", "programdata",
    "system volume information", "$recycle.bin", "recovery",
}
PERSONAL = {"desktop", "documents", "pictures", "videos", "music", "downloads"}
CACHE = {"cache", "caches", "dxcache", "glcache", "code cache", "shadercache"}
DEVELOPER = {".git", "node_modules", ".venv", "venv", ".gradle", ".cargo", ".npm"}
KNOWN_APPS = {"steam", "epic games", "riot games", "ubisoft", "electronic arts"}

def _parts(path):
    """Split both Windows and POSIX paths, irrespective of host OS."""
    return [part.casefold() for part in re.split(r"[\\/]+", str(path)) if part]

def classify_folder(path):
    parts = set(_parts(path))
    if parts & PROTECTED:
        return ("system-managed", "Leave system and application files in place. Use official Windows or app tools.")
    if parts & DEVELOPER:
        return ("development", "Review project dependencies, caches and build outputs in their own tools; preserve source and virtual environments.")
    if parts & KNOWN_APPS:
        return ("installed-app", "Use the game's launcher or Windows Apps settings to move/uninstall; never manually move installation folders.")
    if parts & PERSONAL:
        return ("personal", "Back up and review personal files individually; consider moving large media to another drive.")
    if parts & CACHE:
        return ("app-cache", "Review which app owns this cache; close the app and follow its official cleanup guidance.")
    return ("review", "Inspect contents manually before considering backup, relocation or cleanup.")

def make_recommendations(scan, *, free_bytes=None, total_bytes=None, limit=20):
    """Rank *review suggestions*, never imply that scan size is recoverable."""
    if not isinstance(scan, dict) or "folders" not in scan:
        raise ValueError("A Storage Insights folder-size scan is required.")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be 1..100.")
    if (free_bytes is None) != (total_bytes is None):
        raise ValueError("Supply free_bytes and total_bytes together.")
    if free_bytes is not None and (
        not isinstance(free_bytes, (int, float)) or
        not isinstance(total_bytes, (int, float)) or
        total_bytes <= 0 or free_bytes < 0 or free_bytes > total_bytes
    ):
        raise ValueError("Invalid drive free/total capacities.")

    rows = []
    for folder in scan.get("folders", []):
        path, size = str(folder.get("path", "")), folder.get("size", 0)
        if not path or not isinstance(size, (int, float)) or size < 0:
            continue
        kind, instruction = classify_folder(path)
        rows.append({"path": path, "logical_bytes": int(size),
                     "category": kind, "advice": instruction,
                     "can_auto_clean": False})
    rows.sort(key=lambda row: row["logical_bytes"], reverse=True)
    percentage = None if free_bytes is None else round(100 * free_bytes / total_bytes, 1)
    return {
        "folders": rows[:limit],
        "free_percentage": percentage,
        "low_space": percentage is not None and percentage < 15,
        "scan_complete": bool(scan.get("complete", False)),
        "scan_reason": scan.get("reason"),
        "unreadable": int(scan.get("unreadable", 0)),
        "reclaimable_bytes": None,
        "disclaimer": (
            "Read-only recommendations. Listed sizes are logical file lengths, "
            "NOT reclaimable or physical disk usage. No changes performed. "
            "System folders, projects, caches, games and personal files must not "
            "be automatically deleted. Incomplete scans may miss major usage."
        ),
    }
