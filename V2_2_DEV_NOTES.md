# AI Laptop Manager V2.2 — Storage Recommendations (development)

This isolated branch builds on V2.1. **Not merged or released.**

## What is implemented
- `cleanup_recommendations.py`: deterministic, read-only classifications for folders returned by Storage Insights, ranked by logical size.
- `storage_insights_gui.py`: **Review recommendations** button, which opens a local review panel after a folder-size scan.
- `tests/test_cleanup_recommendations.py`: tests for drive space thresholds, protection of system and development folders, incomplete scans, validation and no automatic deletion.
- A Windows Actions workflow to run all tests, compile all modules, and build the V2.2 preview executable.

## Safety limitations
- No automatic junk deletion, registry edits, service termination, RAM forcing, disk formatting, or recovery commands.
- File-size totals are *logical* lengths, not reclaimable bytes. Suggestions must not be treated as guaranteed savings.
- Scan results are bounded and may be incomplete due to permissions, links or scan limits.
- Installed application moves must use supported Windows/launcher mechanisms; never manually move Program Files.
- Drive capacity is not inferred from the folder scan. The recommendation API accepts separately measured capacity and indicates low space at less than 15% free.

## Test on the Dell G3 3500
1. Download the **AI-Laptop-Manager-V2-2-Windows** artifact after the Windows Actions run succeeds.
2. Back up important files, then close the previous preview.
3. Run the preview; go to **Storage Insights 2.1**.
4. Select a folder on C: and run **Scan folder**.
5. Click **Review recommendations** and confirm suggestions are read-only. Nothing should be deleted.
6. Verify that links/junctions and inaccessible folders remain explicitly reported. Avoid sharing reports with personal file paths.

## Remaining V2.2 work
- Per-app installed-size mapping is unreliable via registry Size estimates; design precise app-specific inventory separately.
- Planned cleanup actions require explicit per-item revalidation, backup and consent; **not implemented**.
- No automated registry cleaning or fake RAM boosting.

