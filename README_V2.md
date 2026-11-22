# AI Laptop Manager 2.0 — Future Tools preview

This branch is an **experimental development preview**. Do not merge or distribute as a verified release until Windows 11 and USB-drive testing is complete.

## New V2 modules

- **File Manager:** browse a local folder; copy files without overwrite after approval.
- **Disks & USB:** list mounted volumes and partitions, inspect removable storage without modification.
- **Repair Center:** whitelisted read-only SFC, DISM and CHKDSK checks; modifying repair commands are displayed for manual review only.
- **Recovery Studio:** prepare a Microsoft Windows File Recovery (`winfr`) command for photos, videos, and documents. The app does **not** automatically run recovery.
- **RAM & Registry:** process inspection and manual system tools. No misleading automatic RAM cleaning or registry changes.
- **Wallpaper:** explicitly selected local JPG/PNG/BMP wallpaper.

## Important recovery limitations

Stop using a drive immediately after losing data. Recover to a *different physical drive* when possible. SSD TRIM and overwritten sectors can make recovery impossible. Do not format the source, run filesystem repairs such as `chkdsk /f`, or install software onto it before recovery. If the disk is physically failing or repeatedly disconnecting, consider professional imaging first.

Official documentation: https://support.microsoft.com/en-us/windows/experience/backup-recovery/windows-file-recovery

## Windows command safety

Diagnostics use argument lists and never `shell=True`; only known read-only commands can be run in-app. `sfc /scannow` and `DISM /RestoreHealth` are preview-only and must be started manually in an elevated terminal if appropriate. No `diskpart clean`, format, registry writes, or automatic data-removal features.

## Developer setup

Install `requirements.txt` dependencies using Python 3.10+; run `python -m unittest discover -s tests -v`. Run `python ai_laptop_manager_v2.py` to start the expanded desktop interface once the Windows GUI is reviewed.

## Status

Initial code and unit tests are under review; no actual file-recovery success, SSD SMART diagnosis, registry repair or data recovery has been validated on the user's laptop. Local-first and no telemetry by default.


## V2.1 storage analyzer (development preview)

New **Storage Insights 2.1** tab: opt-in, cancellable read-only scans of a selected folder (including C:\), ranked top-level logical folder sizes and largest files, plus SHA-256 verified duplicate *previews*. It does **not** delete, move, quarantine or modify files, alter registry keys or change drive partitions.

Totals are logical byte lengths, not allocated NTFS space. Results can be incomplete due to Windows permissions, symlinks/junctions, scan limits, cancellation, compressed/sparse data, hard links and NTFS metadata. A duplicate match is never permission to delete a file. Do not run intensive scans against a failing drive or on a valuable data-recovery source before imaging/preserving it.

Dev checks: python -m unittest discover -s tests -v; then validate Windows GUI and removable media in a test environment before release.
