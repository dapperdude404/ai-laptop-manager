# AI Laptop Manager v1.0 — Windows PC Care

A **local desktop application (initial release; not yet validated on your Dell laptop)** for Windows 10/11, designed around the Dell G3 3500 screenshots. This is a rules-based diagnostic utility, **not an AI agent** and not an antivirus. It makes no network requests and does not access ChatGPT.

## Features

- **Dashboard:** CPU, RAM, battery, process count, uptime, and per-volume storage.
- **Processes:** read-only view of the 75 most memory-intensive running programs.
- **Storage Explorer:** read-only scan of a folder you choose, ranking the 100 largest ordinary files; excludes junction traversal and stops after 180,000 files.
- **Installed Apps:** Windows uninstall registry inventory, including reported sizes where available (estimated, not exact).
- **Startup:** read-only listing of startup registry entries and Startup folder items.
- **Safe Cleanup:** preview user Temp files older than 14 days; move only selected eligible files to **Recycle Bin** after two confirmations. Never touches Downloads, personal projects, Windows system files, and never empties Recycle Bin.
- **Health:** read-only Windows storage health request, launcher for Reliability Monitor, and local JSON report export.

## Run on Windows

1. Extract the ZIP into a folder you own, such as `Documents\AI_Laptop_Manager`.
2. Install **Python 3.10+** from https://www.python.org/downloads/windows/ if not already installed. Check **Add Python to PATH** during setup.
3. Double-click **`Start_Laptop_Manager.bat`**. If Windows SmartScreen warns about the unsigned script, inspect the included source and run only if you trust it. On first run it creates `.venv` and installs the packages listed in `requirements.txt`. Internet is needed for this initial dependency installation; all diagnostic features run locally thereafter.
4. Use **Dashboard → Refresh diagnostics**, **Processes → Refresh top processes**, then **Installed Apps → Load installed apps**. To find space used by your files, choose specific folders in **Storage Explorer**.
5. For old Temp files, **Safe Cleanup → Preview old temp files**, select individual rows, and choose **Move SELECTED to Recycle Bin**. Review the list and type `RECYCLE` to confirm.

**Important:** Moving files to Recycle Bin does *not* free up space until you inspect and empty Recycle Bin manually in Windows. Some files may be in use and cannot be recycled. Do not delete anything you need.

If the launcher closes unexpectedly, run `Run_Debug.bat` to see the error. Actual system measurements will appear only when the application runs locally on your PC.

## Build a Windows EXE

After a successful run, double-click **`Build_Windows_EXE.bat`**. The script installs PyInstaller into the private virtual environment and creates `dist\AI_Laptop_Manager.exe`. That executable runs without a separate Python installation on a compatible Windows machine. Alternatively, push the project to a repository and run the included **Build Windows App** GitHub Actions workflow (`workflow_dispatch`), then download the Windows artifact.

> The ZIP does not contain a pre-built executable. Windows EXE packaging must be done on Windows or a Windows CI runner. Code is provided for inspection before running it.

## Tests

From a Python environment with dependencies installed:

```bat
python -m unittest discover -s tests -v
```

The unit tests check read-only file ranking, Temp age filtering, path restrictions and selected-file recycling authorization. A Windows GitHub Actions workflow runs these tests and attempts to build the executable; neither substitutes for testing the full GUI on your Dell G3 3500.

## Safety and privacy

- The app itself makes no network connections, telemetry, cloud uploads, autonomous deletion, uninstalling software, changing startup settings, modifying the registry, or Windows repairs.
- Temp cleanup is manual, file-by-file, and **Recycle Bin only**. The tool does not automatically remove directories or files newer than 14 days.
- Do not use cleanup while a software installer or updater is running.
- Installed-app size estimates may be inaccurate. SSD RAID setups can obscure physical drive SMART data; reported healthy status is not a guarantee.
- Exported JSON reports can contain names, local paths, and startup commands. Review and redact before sending them to anyone.
- For full thermal testing, battery wear data, and SSD SMART health, use trusted Dell or Windows diagnostics.

## Your Dell G3 3500 screenshot findings (not live measurements)

| Item | Screenshot finding |
| --- | --- |
| CPU | Intel Core i5-10300H, 4 cores/8 threads |
| RAM | 16 GiB-class installed; ~10.7 GB in use at capture |
| Discrete GPU | GeForce GTX 1650 4 GB |
| Windows disk | C: approximately 235 GB, about 218 GB used, ~16.9 GB free |
| Windows Installed Apps category | Approximately 177 GB |
| Temporary files | About 508 MB |
| Other disk | D:/E: SSD volume reported at about 932 GB formatted |

The system drive's installed applications, not temporary files, are the main starting point for reclaiming space. The software does **not** automatically move installed programs; many require proper reinstall/migration procedures.