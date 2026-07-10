"""
统一锋面掩膜经纬度网格。

当前旧脚本用途是把小范围锋面掩膜插值并扩展到 CRA40 目标网格。
这里仅把读写路径切到项目内新目录，算法保持原样。
"""

import os
from glob import glob

import matplotlib.pyplot as plt
import netCDF4  # noqa: F401
import numpy as np
import xarray as xr

from nc_compat import open_dataset_compat, to_netcdf_compat
from project_paths import cra40_front_extend, cra40_front_mask

lat = np.arange(55.875, 15.0, -0.25)
lon = np.arange(70.125, 141.0, 0.25)
lon2d, lat2d = np.meshgrid(lon, lat)

filepath_list = sorted(glob(cra40_front_mask(2, "*")))
for filepath in filepath_list:
    ds_nc = open_dataset_compat(filepath)
    mask_small = ds_nc.ind_area_bool.values
    lon_interp = (ds_nc.lon.values[:-1] + ds_nc.lon.values[1:]) / 2
    lat_interp = (ds_nc.lat.values[:-1] + ds_nc.lat.values[1:]) / 2
    mask_temp = (mask_small[:-1, :] + mask_small[1:, :]) / 2
    mask_small_interp = (mask_temp[:, :-1] + mask_temp[:, 1:]) / 2
    mask_small_interp[mask_small_interp >= 0.5] = 1
    mask_small_interp[mask_small_interp < 0.5] = 0

    mask_large = np.zeros_like(lon2d).astype(bool)
    index_W = np.where(lon == lon_interp[0])[0][0]
    index_E = np.where(lon == lon_interp[-1])[0][0]
    index_N = np.where(lat == lat_interp[0])[0][0]
    index_S = np.where(lat == lat_interp[-1])[0][0]
    mask_large[index_N:index_S + 1, index_W:index_E + 1] = mask_small_interp.astype(bool)

    ds_new = xr.Dataset(
        {
            "ind_area_bool": (["lat", "lon"], mask_large),
            "longitude": (["lat", "lon"], lon2d),
            "latitude": (["lat", "lon"], lat2d),
        },
        coords={
            "lon": lon,
            "lat": lat,
        },
    )
    filename = os.path.basename(filepath)
    dt = os.path.splitext(filename)[0]
    to_netcdf_compat(ds_new, cra40_front_extend(2, dt))
