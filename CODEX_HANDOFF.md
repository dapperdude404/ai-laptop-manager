# Codex handoff — AI Laptop Manager

This app was authored as a local-first Windows maintenance utility. Codex is **optional** for expanding the project. Do not merge this into unrelated repositories.

## Current architecture

- `maintenance.py`: psutil read-only system audit, Windows registry app/startup inventory, selected user-temp recycling using send2trash; local JSON report.
- `app.py`: Tkinter desktop UI. Background scan results marshalled onto Tkinter's main thread via Queue.
- `tests/test_maintenance.py`: non-destructive backend security regression tests.
- `Start_Laptop_Manager.bat`: source launcher. `Build_Windows_EXE.bat`: local PyInstaller packaging.
- `.github/workflows/build-windows.yml`: Windows executable CI artifact.

## Suggested next Codex tasks

1. Run the tests and GUI smoke test on Windows 11. Fix Windows-only failures without reducing file safety restrictions.
2. Add CPU/GPU temperature readings via a documented, opt-in sensor source; do not claim a temperature if unavailable.
3. Implement **read-only** duplicate-file discovery, hashing contents only when the user selects directories; never auto-delete originals.
4. Add a sortable per-volume space treemap, respecting Windows junctions and inaccessible directories.
5. Add an app-size inventory with explicit reliability qualifiers and a migration guide for large games/apps; never move programs by raw folder copying.
6. Build and sign a Windows installer if a suitable code-signing certificate and publisher process become available.
7. Expand automated tests for Windows junctions, access denied errors, locked temp files and snapshot privacy.

## Security invariants

- No changes to system settings/registry, no remote telemetry, no silent deletion.
- Only recycle selected, revalidated, non-symlink, at-least-14-day-old ordinary files **inside the current user's LocalAppData\\Temp**.
- Require an explicit review + typed confirmation for any file mutation.
- Never touch Downloads, user projects, Windows temp/System32, backups, or Recycle Bin automatically.
- Report paths may disclose sensitive information; store locally only and warn on sharing.