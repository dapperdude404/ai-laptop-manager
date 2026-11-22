# AI Laptop Manager V2.5 — Smart Control Center

Development preview. The protected `main` branch is **not** modified by this branch.

## Implemented
- **Smart Intelligence:** deterministic evidence-based storage, CPU and RAM review suggestions; each suggestion includes its uncertainty and is never executed automatically.
- **Power Cycle Lab:** battery charge and AC/charging state, CPU frequency, `powercfg /list`, `/getactivescheme`, `/a` and `/requests`. User-confirmed, verified power-plan switching with session undo.
- **Battery Report:** explicit local `powercfg /batteryreport /output` on a user-selected new HTML path, with no overwrite and no upload.
- **Guided app management:** Windows registry app inventory, keyword filtering and a link to Windows Installed Apps where users can uninstall normally. Registry-reported sizes are estimates.
- **Optional 2–4 laptop comparison:** each owner exports a local JSON file containing exactly five numerical fields; importing and comparing happens offline. No account ID, serial, hostname, file paths, machine name or identifying hardware ID. Small samples are *not benchmarks*.
- **Windows EXE self-test:** reconstructs the actual Tkinter app, checks the Smart Control Center, and writes a result marker for CI.

## Why no automatic VBS/Defender/BCDEDIT tweaks?
An inspected reference ZIP called WindowsOptimizer 1.7 contains tools such as `Disable-VBS.ps1`, registry tweaks, `BCDEDIT.bat`, scripted Windows Update disabling, GPU IRQ priority changes, power-plan imports and undo scripts. Some can disable security, break boot, affect thermal/power draw or harm virtualization features. We have **not** executed or redistributed the third-party ZIP or any of its binaries/scripts. This release does not copy them into the project.

## Missing (future milestones)
- Hardware-validated sensor readings for amperes, watts, CPU package power, GPU power, charge-cycle counts and temperature. Drivers/RAID/USB bridges can hide sensors; do not estimate these as facts.
- True app uninstall orchestration through verified WinGet package IDs and explicit rollback/documented reinstall steps.
- Transactional per-tweak backup, OS compatibility constraints, hardware-specific baselines and post-change benchmark verification.
- Optional signed low-privilege telemetry collector and a narrowly scoped Windows service for protected operations, if ever needed.
- UI migration to a modern WinUI 3/WPF shell while preserving the Python diagnostic core or replacing it with tested .NET services.
- Verified disk recovery on spare USB media; never silently attempt recovery or format a failing drive.

## Data handling
The application does not proactively upload system measurements. Privacy-limited profile export needs the user's explicit action. Never ask for third-party laptop metrics without the owner's approval. No claims of machine-learning model accuracy are made.

## Verification
Run `python -m unittest discover -s tests -v`, perform Windows Tk initialization, and run the frozen-EXE `--self-test` check. A passing CI build does **not** certify performance or safety on every laptop.

## Public documentation
- PowerCfg: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
- WinGet uninstall: https://learn.microsoft.com/en-us/windows/package-manager/winget/uninstall
- VBS/Memory Integrity: https://learn.microsoft.com/en-us/windows/security/hardware-security/enable-virtualization-based-protection-of-code-integrity
- Hardware sensor reference (not included): https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
