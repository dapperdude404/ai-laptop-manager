"""Supported Windows power-plan and battery diagnostics.

NO universal registry/BCD tweaks. Wattage/current is explicitly unknown unless
a future sensor provider reports actual electrical measurements.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import uuid
import psutil

GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")

def _run(args, *, timeout=20):
    if os.name != "nt":
        raise RuntimeError("Windows only")
    if timeout <= 0 or timeout > 90:
        raise ValueError("Unsupported command timeout")
    p = subprocess.run(["powercfg.exe", *args], capture_output=True, text=True,
                       errors="replace", timeout=timeout, shell=False,
                       creationflags=0x08000000)
    if p.returncode != 0:
        detail = (p.stderr or p.stdout).strip()[:500]
        raise RuntimeError("Windows powercfg returned an error: " + detail)
    return p.stdout

def _norm_guid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid power-plan GUID.") from None

def parse_power_plans(list_output, active_output):
    current_match = GUID_RE.search(active_output)
    active = _norm_guid(current_match.group()) if current_match else None
    choices = []
    seen = set()
    for line in list_output.splitlines():
        match = GUID_RE.search(line)
        if not match:
            continue
        guid = _norm_guid(match.group())
        if guid in seen:
            continue
        seen.add(guid)
        tail = line[match.end():].strip()
        # Plan names may be localized. Keep human description, never use it as a command.
        label = tail.strip(" *-:\t") or "Unnamed power plan"
        choices.append({"guid": guid, "name": label, "active": guid == active})
    return {"active": active, "plans": choices}

def list_power_plans():
    return parse_power_plans(_run(["/list"]), _run(["/getactivescheme"]))

def diagnostic_snapshot():
    """On-demand cheap measurements, no power-report or drive writes."""
    b = psutil.sensors_battery()
    f = psutil.cpu_freq()
    return {
        "charge_percent": round(float(b.percent), 1) if b else None,
        "plugged_in": bool(b.power_plugged) if b else None,
        "seconds_left": int(b.secsleft) if b and b.secsleft >= 0 else None,
        "cpu_frequency_mhz": round(float(f.current), 1) if f else None,
        "watts": None,
        "amperes": None,
        "explanation": ("Battery charge is not battery wear. CPU frequency is not CPU power draw. "
                        "Accurate voltage/current/wattage and charge cycles require supported hardware sensors "
                        "or an OEM/Windows report, and are not inferred here."),
    }

def read_power_blockers():
    """List processes preventing sleep (may require elevated permissions)."""
    return _run(["/requests"], timeout=18)

def read_sleep_capabilities():
    return _run(["/a"], timeout=18)

def change_power_plan(target_guid, *, confirmed):
    """Explicit opt-in, reversible using returned previous GUID.

    Re-list plans just before a change; refuse stale or unrecognized IDs.
    """
    if not confirmed:
        raise PermissionError("Explicit confirmation is required.")
    target = _norm_guid(target_guid)
    before = list_power_plans()
    if target not in {x["guid"] for x in before["plans"]}:
        raise ValueError("Selected power plan is no longer available.")
    if before["active"] is None:
        raise RuntimeError("Active plan cannot be verified; refusing to change it.")
    if before["active"] == target:
        return {"changed": False, "previous": before["active"], "current": target}
    _run(["/setactive", target])
    after = list_power_plans()
    if after["active"] != target:
        raise RuntimeError("Power plan change could not be verified.")
    return {"changed": True, "previous": before["active"], "current": target}

def battery_report(path, *, confirmed):
    """Opt-in report generation; never overwrite an existing report."""
    if not confirmed:
        raise PermissionError("Confirm report creation first.")
    dest = Path(path).expanduser().absolute()
    if dest.suffix.lower() != ".html" or not dest.parent.is_dir() or dest.exists():
        raise ValueError("Choose a new .html file in an existing local directory.")
    _run(["/batteryreport", "/output", str(dest)], timeout=35)
    if not dest.is_file():
        raise RuntimeError("powercfg did not create the requested battery report.")
    return str(dest)
