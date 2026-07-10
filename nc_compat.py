"""xarray/GRIB Windows 中文路径兼容层。

当前项目路径包含中文字符，部分科学计算后端在 Windows 下会出现：

1. `netCDF4` 读取现有 nc 文件却报 FileNotFoundError
2. 写出 nc 文件时报 PermissionError
3. `cfgrib` / `pygrib` 在中文路径下索引或编码异常

这里统一把输入文件暂存到系统英文临时目录，再交给后端读取；
写出时先写到英文临时目录，再复制回项目路径。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import xarray as xr


TMP_ROOT = Path(tempfile.gettempdir()) / "meiyu_new_xarray_cache"
TMP_ROOT.mkdir(parents=True, exist_ok=True)

GRIB_SUFFIXES = {".grib", ".grib2", ".grb", ".grb2"}


def _needs_ascii_staging(path: Path) -> bool:
    """只要绝对路径里含非 ASCII 字符，就启用暂存。"""
    return not str(path.resolve()).isascii()


def _staged_name(path: Path) -> Path:
    """为源文件生成临时文件名。"""
    resolved = str(path.resolve())
    digest = hashlib.md5(resolved.encode("utf-8")).hexdigest()
    suffix = "".join(path.suffixes) or ".dat"
    if path.suffix.lower() in GRIB_SUFFIXES:
        return TMP_ROOT / f"{digest}_{os.getpid()}{suffix}"
    return TMP_ROOT / f"{digest}{suffix}"


def stage_input_path(path_like: os.PathLike[str] | str) -> str:
    """把输入文件映射到 ASCII 临时路径。"""
    path = Path(path_like)
    if not _needs_ascii_staging(path):
        return str(path)

    staged = _staged_name(path)
    staged.parent.mkdir(parents=True, exist_ok=True)

    src_stat = path.stat()
    if not staged.exists():
        shutil.copy2(path, staged)
    else:
        dst_stat = staged.stat()
        if dst_stat.st_size != src_stat.st_size or dst_stat.st_mtime < src_stat.st_mtime:
            shutil.copy2(path, staged)
    return str(staged)


def open_dataset_compat(path_like: os.PathLike[str] | str, **kwargs: Any) -> xr.Dataset:
    """兼容中文工程路径的 `xr.open_dataset`。"""
    path = Path(path_like)
    staged_path = stage_input_path(path)

    if path.suffix.lower() in GRIB_SUFFIXES and "engine" not in kwargs:
        kwargs["engine"] = "cfgrib"
        backend_kwargs = dict(kwargs.get("backend_kwargs") or {})
        backend_kwargs.setdefault("indexpath", "")
        kwargs["backend_kwargs"] = backend_kwargs

    return xr.open_dataset(staged_path, **kwargs)


def to_netcdf_compat(ds: xr.Dataset, path_like: os.PathLike[str] | str, **kwargs: Any) -> Any:
    """兼容中文工程路径的 `Dataset.to_netcdf`。"""
    path = Path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not _needs_ascii_staging(path):
        return ds.to_netcdf(path, **kwargs)

    staged = _staged_name(path)
    staged.parent.mkdir(parents=True, exist_ok=True)
    result = ds.to_netcdf(staged, **kwargs)
    shutil.copy2(staged, path)
    return result
