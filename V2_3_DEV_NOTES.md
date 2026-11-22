# V2.3 USB/SSD Diagnostics — developer preview

This branch adds a **read-only** physical disk, partition and volume correlation module.

- Windows fixed PowerShell `Get-Disk`, `Get-Partition`, `Get-Volume` commands; no user-supplied shell.
- Joins physical disk numbers to partitions and drive letters when available.
- Clearly distinguishes Windows storage-provider health from full SMART assessment.
- Alerts for offline, abnormal-health and USB devices.
- Conservative recovery triage that never executes recovery, repair or formatting commands.
- Unit tests use synthetic disk data and do not touch any real drive.

## Safety
Do **not** run `chkdsk /f`, `chkdsk /r`, `diskpart clean`, `format`, `Initialize-Disk`, or registry cleaners on a device with missing files. Stop writing to a recovery source. Failing media warrants professional imaging/recovery.

## Scope
The API is ready for the next UI integration; **not** yet a complete USB recovery wizard. No damaged-drive testing was performed. Normal SMART, offline physical drive identity, BitLocker and RAID-specific tests remain future work. This branch does not change V1 or protected `main`.
