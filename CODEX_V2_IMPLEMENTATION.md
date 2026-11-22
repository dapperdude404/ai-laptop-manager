# Codex implementation handoff — V2 Future Tools

**Repository:** dapperdude404/ai-laptop-manager  
**Branch:** feature/future-tools-v2  
**Policy:** Do not merge, deploy, publish releases, or change Windows registry without explicit user approval.

## V2 implementation
- `future_core.py`: safe local file copy, folder listing, mounted volume/partition inventory, read-only Windows repair presets, Microsoft File Recovery command previews and wallpaper API.
- `ai_laptop_manager_v2.py`: nested six-tab V2 preview. V1 remains unchanged.
- `tests/test_future_core.py`: validates no-overwrite, symlink protections, recovery volume validation and preset allowlisting.

## Immediate Codex review tasks
1. Build Windows EXE using `ai_laptop_manager_v2.py`; run existing and new tests on Windows 11.
2. Test external USB insertion, BitLocker drives, removable media disappearing during scan, and Windows permissions.
3. Confirm `winfr` syntax and offered file extensions on latest Windows File Recovery app; clarify which recovery modes apply to USB/NTFS/exFAT.
4. Add command cancellation/timeouts, progress, accessibility and keyboard support.
5. Confirm source file path isn't altered during a long copy; block path traversal, junction/reparse points, file-copy race attacks, and overwrites.
6. Run a Windows GUI smoke test of all new and existing tabs. Validate PyInstaller dependencies.
7. Add error messages for unsupported disk provider / RAID / offline USB disks. No inferred SSD "healthy" claim from Windows provider alone.
8. Never auto-run modifying operations (`chkdsk /f`, format, diskpart, registry modification, mass file deletion). Recovery destination must differ from source, ideally be physically separate.

## Product roadmap

- **V2.1 Storage intelligence:** real C: folder size analyzer with scan progress, duplicate finding with SHA-256, large AppData breakdown; allow only Recycle Bin backed operations.
- **V2.2 Diagnostics:** robust SSD SMART/Windows Reliability Counters, battery wear, thermals, logs, hardware fault triage.
- **V2.3 Recovery workflows:** USB recovery case wizard, media type detection, source/destination physical disk identity, image-first guidance and opt-in Windows File Recovery integration.
- **V2.4 Safer optimization:** user-approved startup changes with rollback, disk cleanup staging, protected folder exclusions, no false RAM-clearing promises.
- **V2.5 AI explainability:** on-device or opt-in cloud AI interpretation of diagnostic reports, with sensitive file paths redacted.
- **V3 Community edition:** plugin API, multilingual accessibility, installers, software signing, release evidence, privacy docs and contributor guide.

**Guardrail:** Never guarantee successful recovery of deleted photos/video or repair of failed SSDs. Do not write to suspected failing recovery source media before imaging.  
Reference: https://support.microsoft.com/en-us/windows/experience/backup-recovery/windows-file-recovery
