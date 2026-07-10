# Diagnosis Checklist

## Goal

Separate these cases cleanly:

1. Data truly missing
2. Shell display/encoding issue only
3. Library-specific non-ASCII path incompatibility
4. Real permission problem

## Recommended Sequence

### 1. Check from PowerShell

Use commands such as:

```powershell
Test-Path -LiteralPath '...'
Get-Item -LiteralPath '...'
```

If this fails, do not debug Python yet.

### 2. Check from Python stdlib

```python
from pathlib import Path
p = Path(r"...")
print(p.exists(), p.stat().st_size if p.exists() else None)
```

If PowerShell succeeds and Python stdlib fails, the issue is broader than one scientific library.

### 3. Check the target backend directly

Examples:

```python
import xarray as xr
ds = xr.open_dataset(path)
```

```python
import pygrib
grbs = pygrib.open(path)
```

Capture the exact exception class and message.

### 4. Repeat on an ASCII temp path

Copy the same file to a path like:

```text
C:\Users\<name>\AppData\Local\Temp\project_test\file.nc
```

If the backend succeeds there, the diagnosis is complete: path compatibility issue.

### 5. Check write path separately

Read success does not imply write success.

Test a minimal write:

```python
import numpy as np
import xarray as xr
ds = xr.Dataset({"a": (("x",), np.arange(3))})
ds.to_netcdf(path)
```

If write fails only under the original project path and succeeds under ASCII temp, wrap writes too.

## Fast Interpretation Table

- `FileNotFoundError` on existing file: suspect backend path incompatibility.
- `PermissionError` on valid new output path: suspect backend path incompatibility first, not ACL first.
- `UnicodeEncodeError` from GRIB tools: almost always path encoding incompatibility.
- Matplotlib lock/cache failures: isolate with `MPLCONFIGDIR`.

## Remediation Order

1. Confirm the incompatibility with ASCII temp reproduction.
2. Introduce one shared staging helper.
3. Patch all affected IO calls.
4. Re-run the light scripts first.
5. Re-run the heavy scripts after IO is stable.
