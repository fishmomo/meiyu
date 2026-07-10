---
name: windows-chinese-science-path-compat
description: Use when a Windows project contains Chinese or other non-ASCII paths and Python scientific tools behave inconsistently, especially when PowerShell can see files but libraries such as xarray, netCDF4, pygrib, matplotlib, or related IO code report file-not-found, permission, cache, or encoding errors.
---

# Windows Chinese Science Path Compat

## Overview

Treat two problems separately:

1. PowerShell output looks garbled or inconsistent.
2. Python libraries cannot reliably read or write files under non-ASCII project paths.

The first is usually a shell display issue. The second is a real runtime compatibility issue and is the one that breaks workflows.

## Core Rule

Do not assume "PowerShell can `Test-Path` the file" means the Python library can open it.

On Windows, some scientific IO stacks still fail when the absolute path contains Chinese characters. Typical symptoms:

- `FileNotFoundError` on an existing file
- `PermissionError` when writing a new file in a valid folder
- `UnicodeEncodeError: 'ascii' codec can't encode characters`
- Matplotlib cache/lock failures under user profile or project path

## Quick Triage

1. Verify the file exists from PowerShell.
2. Verify the same file exists from Python `Path.exists()`.
3. Test the target library directly on the original path.
4. Copy the same file to a pure ASCII temp path and test again.
5. If ASCII temp succeeds, classify it as a path-compat issue, not a missing-data issue.

Read [references/diagnosis-checklist.md](references/diagnosis-checklist.md) before changing code.

## Fix Strategy

Prefer the smallest change that preserves the original research logic.

### A. For `xarray` / `netCDF4` / `pygrib`

Wrap file access at the IO boundary instead of rewriting the algorithm:

- Read: stage the source file into a pure ASCII temp directory, then open that staged file.
- Write: write to a pure ASCII temp file first, then copy the result back to the intended project path.

Use [scripts/path_staging_compat.py](scripts/path_staging_compat.py) as the reusable template.

### B. For `matplotlib`

When running non-interactively on Windows:

- set `MPLBACKEND=Agg`
- set `MPLCONFIGDIR` to a writable project-local or temp ASCII directory

This avoids font-cache and lock-file issues that are easy to confuse with data-path failures.

### C. For PowerShell display noise

Do not treat garbled Chinese comments or docstrings in `Get-Content` output as proof the source file is broken.

Check instead:

- whether Python can import/compile the file
- whether the script actually runs
- whether generated outputs are correct

## Decision Flow

- If only terminal text is garbled, keep moving and validate by execution.
- If Python stdlib can see the file but the domain library cannot, add staged-path compatibility.
- If both PowerShell and Python stdlib cannot see the file, fix data placement first.
- If writes fail only for `.nc`, `.grib`, or cache files, suspect backend path compatibility before suspecting permissions.

## Minimal Implementation Pattern

1. Add one shared compatibility module near the project root.
2. Replace direct `xr.open_dataset(...)` with a compat wrapper.
3. Replace `ds.to_netcdf(...)` with a compat writer when writing under non-ASCII paths.
4. Replace `pygrib.open(path)` with `pygrib.open(stage_input_path(path))`.
5. Keep all scientific calculations unchanged unless a real algorithm bug is proven.

## Common Mistakes

- Chasing "missing data" when the file already exists and only the backend cannot open it.
- Editing every hardcoded path one by one instead of fixing the IO boundary once.
- Mixing path diagnosis with encoding diagnosis.
- Treating `plt.show()` warnings under `Agg` as a blocking failure.
- Refactoring core logic before the legacy script can run end to end.

## Output Standard

When documenting this issue in a project:

- record the failing library
- record the exact failing path type
- record the ASCII-temp verification result
- record the final shared compatibility hook

Do not just note "Windows path problem"; make the reproduction chain explicit.
