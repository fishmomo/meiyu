"""Reusable staged-path compatibility helpers for Windows scientific workflows.

Use this when domain libraries fail on non-ASCII project paths even though
the files exist. The helper stages files into a stable ASCII temp directory.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


TMP_ROOT = Path(tempfile.gettempdir()) / "codex_path_stage"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def needs_staging(path_like: os.PathLike[str] | str) -> bool:
    path = Path(path_like)
    return not str(path.resolve()).isascii()


def staged_path(path_like: os.PathLike[str] | str) -> Path:
    path = Path(path_like)
    digest = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()
    suffix = "".join(path.suffixes) or ".dat"
    return TMP_ROOT / f"{digest}{suffix}"


def stage_input_path(path_like: os.PathLike[str] | str) -> str:
    """Return an ASCII-safe readable path for a source file."""
    path = Path(path_like)
    if not needs_staging(path):
        return str(path)

    dst = staged_path(path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    src_stat = path.stat()
    if not dst.exists():
        shutil.copy2(path, dst)
    else:
        dst_stat = dst.stat()
        if dst_stat.st_size != src_stat.st_size or dst_stat.st_mtime < src_stat.st_mtime:
            shutil.copy2(path, dst)
    return str(dst)


def stage_output_path(path_like: os.PathLike[str] | str) -> tuple[str, Path]:
    """Return an ASCII-safe output path and the final intended path."""
    path = Path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not needs_staging(path):
        return str(path), path

    dst = staged_path(path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    return str(dst), path


def finalize_staged_output(staged_output: os.PathLike[str] | str, final_path: os.PathLike[str] | str) -> None:
    shutil.copy2(staged_output, final_path)


def open_xarray_dataset_compat(path_like: os.PathLike[str] | str, xr_module: Any, **kwargs: Any) -> Any:
    """Open an xarray dataset through a staged ASCII path."""
    return xr_module.open_dataset(stage_input_path(path_like), **kwargs)


def write_xarray_netcdf_compat(ds: Any, path_like: os.PathLike[str] | str, **kwargs: Any) -> Any:
    """Write a Dataset/DataArray to netCDF through a staged ASCII path."""
    output_path, final_path = stage_output_path(path_like)
    result = ds.to_netcdf(output_path, **kwargs)
    if Path(output_path) != final_path:
        finalize_staged_output(output_path, final_path)
    return result
