"""Explainable health recommendations and privacy-limited laptop comparisons.

No machine identifiers, serial numbers, username, location or file paths are exported.
No unsupported whole-PC 'accuracy score' is manufactured.
"""
from __future__ import annotations

import json
import math
import statistics

SCHEMA = "ai-laptop-manager/peer-profile/v1"
FIELDS = ("cpu_logical_cores", "ram_gib", "system_drive_free_pct",
          "cpu_utilization_pct", "ram_utilization_pct")
LIMITS = {
    "cpu_logical_cores": (1, 256),
    "ram_gib": (0.5, 4096),
    "system_drive_free_pct": (0, 100),
    "cpu_utilization_pct": (0, 100),
    "ram_utilization_pct": (0, 100),
}

def _number(key, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid numeric metric: {key}")
    lower, upper = LIMITS[key]
    if not lower <= value <= upper:
        raise ValueError(f"Out-of-range metric: {key}")
    return round(float(value), 2)

def validate_profile(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Unsupported anonymized laptop profile schema.")
    # Explicitly discard any non-allowlisted keys rather than propagating secrets.
    safe = {"schema": SCHEMA}
    for key in FIELDS:
        safe[key] = _number(key, data[key])
    return safe

def profile_from_snapshot(snapshot, *, logical_cores, ram_total_bytes):
    """Create a minimal opt-in report from one actual snapshot.

    Capacity reported for C: is derived from the Windows drive snapshot, not
    inferred from a total-storage estimate.
    """
    if logical_cores is None or ram_total_bytes is None:
        raise ValueError("CPU and installed RAM are required.")
    disks = snapshot.get("drives", [])
    system = next((d for d in disks if str(d.get("name", "")).upper().startswith("C:")), None)
    if system is None or not system.get("total"):
        raise ValueError("C: system-drive capacity is unavailable.")
    candidate = {
        "schema": SCHEMA,
        "cpu_logical_cores": logical_cores,
        "ram_gib": ram_total_bytes / 1024**3,
        "system_drive_free_pct": 100.0 * system["free"] / system["total"],
        "cpu_utilization_pct": snapshot["cpu_percent"],
        "ram_utilization_pct": snapshot["ram_percent"],
    }
    return validate_profile(candidate)

def advice(profile):
    """Rules are review prompts, not diagnostic proof or automatic actions."""
    p = validate_profile(profile)
    results = []
    def add(severity, title, evidence, recommendation, certainty="Snapshot observation"):
        results.append({"severity": severity, "title": title, "evidence": evidence,
                        "recommendation": recommendation, "certainty": certainty,
                        "automatic_change": False})
    free = p["system_drive_free_pct"]
    if free < 10:
        add("High", "Very low Windows drive space", f"C: free: {free:.1f}%",
            "Review Windows storage categories and large apps. Back up personal files; use official uninstall/move actions. Do not wipe caches or system directories.")
    elif free < 15:
        add("Medium", "Limited Windows drive headroom", f"C: free: {free:.1f}%",
            "Investigate installed applications and large user files; prefer moving suitable personal media to another drive.")
    if p["ram_utilization_pct"] >= 85:
        add("Review", "Memory usage is elevated", f"RAM used: {p['ram_utilization_pct']:.0f}%",
            "Inspect top processes and repeat the measurement after restart. Do not force-clear Windows memory cache.",
            "Single sample is not evidence of a memory leak.")
    if p["cpu_utilization_pct"] >= 85:
        add("Review", "CPU was busy in this snapshot", f"CPU used: {p['cpu_utilization_pct']:.0f}%",
            "Observe sustained usage and inspect process ownership before changing power plans.",
            "Single sample is not a CPU benchmark.")
    if not results:
        add("Info", "No simple threshold alert", "No included snapshot metric crossed the selected review thresholds.",
            "Continue normal monitoring; this does not certify hardware or software health.",
            "Limited indicators only.")
    return results

def compare_profiles(current, peers):
    """Compare 2–4 voluntarily exported profiles. NOT a performance ranking."""
    own = validate_profile(current)
    if not isinstance(peers, (list, tuple)) or not 2 <= len(peers) <= 4:
        raise ValueError("Provide profiles from 2 to 4 consenting laptops.")
    clean = [validate_profile(p) for p in peers]
    rows = []
    for key in FIELDS:
        values = [p[key] for p in clean]
        rows.append({"metric": key, "this_laptop": own[key],
                     "peer_median": round(statistics.median(values), 2),
                     "peer_min": min(values), "peer_max": max(values)})
    return {
        "count": len(clean), "rows": rows, "privacy": "Only five allowlisted numeric metrics were processed.",
        "limitations": ("Small, self-selected sample. Hardware and workload are not standardized. "
                        "RAM/CPU usage values are snapshots, not benchmark scores or a diagnosis."),
    }

def profile_json(profile):
    return json.dumps(validate_profile(profile), indent=2)
