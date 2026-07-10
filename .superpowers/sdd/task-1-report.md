# Task 1 Report

## Status
Completed.

## What Changed
- Added explicit CRA40 front1 mask asset resolution in `pipeline/core/mask_ops.py`.
- Updated `pipeline/steps/masks.py` to resolve both `front1` and `front2` explicitly, with no silent fallback from `front1` to `front2`.
- Rewrote `tests/test_mask_step.py` to verify front1 asset resolution, front2 regression protection, and front1 missing-file failure behavior.

## Test Result
- `conda run -n cwr_py312 python -m pytest tests/test_mask_step.py -v`
- Result: 3 passed

## Commit
- `73fada7` - feat: add explicit front1 mask asset resolution

## Fix Addendum
- Locked CRA40 front1 V1 to the single supported target time `2017-06-22T18` in `pipeline/core/mask_ops.py`.
- Front1 now raises `ValueError` for any other `target_time` before file existence is considered.
- Front2 was not time-locked because the reviewer requested preserving the existing front2 regression path, and there was no evidence in this task that front2 needed the same boundary.

## Updated Test Result
- `conda run -n cwr_py312 python -m pytest tests/test_mask_step.py -v`
- Result: 4 passed
