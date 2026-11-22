"""Bounded, read-only logical-size scanning and duplicate previews.

Not a measurement of allocated NTFS space and never a license to delete files.
No writes, ACL changes, junction traversal, external requests or telemetry.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import heapq
import os
from pathlib import Path
import stat
import time

def _root(folder):
    path = Path(folder).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    return path

def _walk(root, on_file, *, cancel=None, progress=None,
          max_files=2_000_000, max_dirs=250_000):
    if min(max_files, max_dirs) < 1:
        raise ValueError("Scan limits must be positive.")
    stack = [root]
    count = dirs = unreadable = links = total = 0
    reason = None
    last_progress = 0.0
    while stack:
        if cancel is not None and cancel.is_set():
            reason = "cancelled"
            break
        if dirs >= max_dirs:
            reason = "directory limit reached"
            break
        folder = stack.pop()
        dirs += 1
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if cancel is not None and cancel.is_set():
                        reason = "cancelled"
                        break
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or stat.S_ISLNK(info.st_mode) or (
                                getattr(info, "st_file_attributes", 0) & 0x400):
                            links += 1
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            stack.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        if count >= max_files:
                            reason = "file limit reached"
                            break
                        count += 1
                        total += info.st_size
                        on_file(Path(entry.path), info)
                    except (OSError, ValueError):
                        unreadable += 1
                    if progress is not None and time.monotonic() - last_progress > 0.3:
                        progress({"files": count, "dirs": dirs, "bytes": total})
                        last_progress = time.monotonic()
        except (OSError, ValueError):
            unreadable += 1
        if reason:
            break
    if progress is not None:
        progress({"files": count, "dirs": dirs, "bytes": total})
    return {"root": str(root), "files": count, "dirs": dirs, "bytes": total,
            "unreadable": unreadable, "links": links,
            "complete": reason is None, "reason": reason}

def scan_sizes(folder, *, cancel=None, progress=None,
               max_files=2_000_000, max_dirs=250_000, top_limit=70):
    """Sum logical file lengths by first-level child; does not follow junctions."""
    root = _root(folder)
    sizes, counts, biggest = {}, {}, []
    seq = 0
    def collect(path, info):
        nonlocal seq
        relative = path.relative_to(root)
        name = relative.parts[0] if len(relative.parts) > 1 else "[Root files]"
        sizes[name] = sizes.get(name, 0) + info.st_size
        counts[name] = counts.get(name, 0) + 1
        seq += 1
        record = (info.st_size, seq,
                  {"size": info.st_size, "path": str(path),
                   "modified": dt.datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d")})
        if len(biggest) < top_limit:
            heapq.heappush(biggest, record)
        elif record[0] > biggest[0][0]:
            heapq.heapreplace(biggest, record)
    result = _walk(root, collect, cancel=cancel, progress=progress,
                   max_files=max_files, max_dirs=max_dirs)
    result["folders"] = [
        {"path": str(root if name == "[Root files]" else root / name),
         "size": size, "files": counts[name]}
        for name, size in sorted(sizes.items(), key=lambda p: p[1], reverse=True)]
    result["largest"] = [r[2] for r in sorted(biggest, reverse=True)]
    result["limitations"] = (
        "Logical lengths only, not physical allocated space. Hard links, "
        "compression, sparse files, NTFS metadata, skipped junctions and "
        "inaccessible entries can change real disk usage. No files were changed.")
    return result

def find_duplicates(folder, *, cancel=None, progress=None,
                    max_files=200_000, max_dirs=50_000,
                    min_size=1024*1024, hash_limit=10*1024**3):
    """Show full SHA-256 verified possible duplicate copies, never delete."""
    root = _root(folder)
    sizes = {}
    def collect(path, info):
        if info.st_size >= min_size:
            sizes.setdefault(info.st_size, []).append(
                (path, info.st_mtime_ns, info.st_dev, info.st_ino))
    result = _walk(root, collect, cancel=cancel, progress=progress,
                   max_files=max_files, max_dirs=max_dirs)
    found = {}
    hashed = 0
    reason = None
    for size, candidates in sizes.items():
        if len(candidates) < 2:
            continue
        for path, expected_time, device, inode in candidates:
            if cancel is not None and cancel.is_set():
                reason = "cancelled during hashing"
                break
            if hashed + size > hash_limit:
                reason = "hash budget reached"
                break
            try:
                before = path.stat(follow_symlinks=False)
                if not stat.S_ISREG(before.st_mode) or (
                        getattr(before, "st_file_attributes", 0) & 0x400) or (
                        before.st_size != size or before.st_mtime_ns != expected_time):
                    continue
                sha = hashlib.sha256()
                with path.open("rb") as stream:
                    while True:
                        if cancel is not None and cancel.is_set():
                            reason = "cancelled during hashing"
                            break
                        block = stream.read(1024 * 1024)
                        if not block:
                            break
                        sha.update(block)
                if reason:
                    break
                after = path.stat(follow_symlinks=False)
                if after.st_size != before.st_size or (
                        after.st_mtime_ns != before.st_mtime_ns):
                    continue
                hashed += size
                identity = (device, inode) if inode else ("path", str(path))
                found.setdefault((size, sha.hexdigest()), {})[identity] = str(path)
            except OSError:
                result["unreadable"] += 1
        if reason:
            break
    groups = [
        {"size": size, "sha256": digest, "paths": sorted(paths.values())}
        for (size, digest), paths in found.items() if len(paths) > 1]
    groups.sort(key=lambda g: g["size"]*(len(g["paths"])-1), reverse=True)
    return {"groups": groups, "hashed_bytes": hashed,
            "files": result["files"], "unreadable": result["unreadable"],
            "complete": result["complete"] and reason is None and result["unreadable"] == 0,
            "reason": reason or result["reason"],
            "note": "Preview only. Verified matching hashes do not justify automatic deletion."}
