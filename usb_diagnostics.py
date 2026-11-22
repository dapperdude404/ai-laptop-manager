"""Windows USB/SSD read-only inventory and conservative triage.

Never formats, initializes, repairs, writes to, or mounts a drive.
Device availability and health values are informational, not a SMART verdict.
"""
from __future__ import annotations

import json
import os
import subprocess

POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$disks = @(Get-Disk | Select-Object Number,FriendlyName,BusType,HealthStatus,OperationalStatus,PartitionStyle,Size,IsOffline,IsReadOnly)
$partitions = @(Get-Partition | Select-Object DiskNumber,PartitionNumber,DriveLetter,Size,Type)
$volumes = @(Get-Volume | Select-Object DriveLetter,FileSystem,FileSystemLabel,HealthStatus,Size,SizeRemaining,DriveType)
@{ disks=$disks; partitions=$partitions; volumes=$volumes } | ConvertTo-Json -Depth 6 -Compress
"""

def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]

def _int_or_none(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None

def _status(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "Unknown")

def normalize_inventory(payload):
    """Join provider records by disk number, partition number and drive letter.

    A missing drive letter, offline disk, encrypted volume or USB unplug event
    can prevent mapping. Never assume different letters imply physical disks.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected object from Windows storage providers.")
    disks, partitions, volumes = (as_list(payload.get(k)) for k in ("disks","partitions","volumes"))
    volume_map = {}
    for item in volumes:
        if not isinstance(item, dict):
            continue
        letter = str(item.get("DriveLetter") or "").strip().upper()
        if len(letter) == 1 and letter.isalpha():
            volume_map[letter] = item
    grouped = {}
    for part in partitions:
        if not isinstance(part, dict):
            continue
        number = _int_or_none(part.get("DiskNumber"))
        if number is None:
            continue
        letter = str(part.get("DriveLetter") or "").strip().upper()
        vol = volume_map.get(letter, {})
        grouped.setdefault(number, []).append({
            "partition": _int_or_none(part.get("PartitionNumber")),
            "letter": letter + ":" if len(letter)==1 and letter.isalpha() else None,
            "size_bytes": _int_or_none(part.get("Size")),
            "filesystem": str(vol.get("FileSystem") or "Unknown"),
            "volume_health": _status(vol.get("HealthStatus")),
            "free_bytes": _int_or_none(vol.get("SizeRemaining")),
        })
    results = []
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        number = _int_or_none(disk.get("Number"))
        if number is None:
            continue
        bus = _status(disk.get("BusType"))
        health = _status(disk.get("HealthStatus"))
        operational = _status(disk.get("OperationalStatus"))
        offline = disk.get("IsOffline") is True
        read_only = disk.get("IsReadOnly") is True
        alerts = []
        if offline:
            alerts.append("Disk is offline: do not initialize, format or repair for recovery.")
        if health.casefold() not in ("healthy", "unknown"):
            alerts.append("Storage provider reports non-healthy status: back up and assess professionally.")
        if operational.casefold() not in ("online", "ok", "unknown"):
            alerts.append("Storage provider reports abnormal operational status.")
        if bus.casefold() in ("usb", "sd", "mmc"):
            alerts.append("Removable media: if files disappeared, stop writes and avoid CHKDSK repairs.")
        results.append({
            "disk_number": number, "name": str(disk.get("FriendlyName") or "Unknown disk"),
            "bus_type": bus, "size_bytes": _int_or_none(disk.get("Size")),
            "health": health, "operational": operational,
            "partition_style": _status(disk.get("PartitionStyle")),
            "offline": offline, "read_only": read_only,
            "partitions": sorted(grouped.get(number, []), key=lambda p: p["partition"] or -1),
            "alerts": alerts,
        })
    results.sort(key=lambda item: item["disk_number"])
    known = {item["disk_number"] for item in results}
    return {
        "disks": results,
        "unmapped_partition_disks": sorted(set(grouped)-known),
        "limitations": (
            "Windows provider status is not a complete SMART test. RAID controllers, USB bridges, "
            "BitLocker, unplugged or offline drives may hide details. No scan, repair or change performed."
        ),
        "read_only": True,
    }

def inventory_windows(*, timeout=25):
    """Run fixed, no-input PowerShell Get-* inventory commands only."""
    if os.name != "nt":
        raise RuntimeError("Windows only")
    if not isinstance(timeout, (int,float)) or timeout <= 0 or timeout > 120:
        raise ValueError("Invalid timeout")
    proc = subprocess.run(
        ["powershell.exe","-NoProfile","-NonInteractive","-Command",POWERSHELL_SCRIPT],
        shell=False, capture_output=True, text=True, timeout=timeout, errors="replace",
        creationflags=0x08000000,
    )
    if proc.returncode:
        raise RuntimeError("Storage provider unavailable or insufficient privileges; no changes made.")
    data = json.loads(proc.stdout)
    return normalize_inventory(data)

def recovery_triage(*, drive_visible, abnormal_noise=False, disconnecting=False,
                    overwritten=False):
    """Conservative next steps; no promise of recovery."""
    if abnormal_noise or disconnecting:
        return {
            "risk":"critical",
            "guidance":"Stop using the device and disconnect safely. Avoid repeated scans, CHKDSK, formatting, or repair. Seek professional recovery/imaging.",
            "run_command":False,
        }
    if overwritten:
        return {
            "risk":"high",
            "guidance":"New writes may have overwritten deleted data. Stop writing; recovery may be impossible, especially on SSD/TRIM.",
            "run_command":False,
        }
    if not drive_visible:
        return {
            "risk":"high",
            "guidance":"Do not initialize or format an unrecognized device. Check cable/port once; consider professional imaging if data matters.",
            "run_command":False,
        }
    return {
        "risk":"caution",
        "guidance":"Stop using the source drive. Preserve the device and prepare a recovery plan saving to a different physical disk; no guarantee.",
        "run_command":False,
    }
