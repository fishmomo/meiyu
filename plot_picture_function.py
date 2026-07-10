import math

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
import numpy as np
import shapely.geometry as sgeom
from cartopy.io.shapereader import Reader
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from shapely.prepared import prep

from project_paths import CHINA_SHP_PATH


def polygon_to_mask(polygon, x, y):
    """生成落入多边形内部的掩膜数组。"""
    x = np.atleast_1d(x)
    y = np.atleast_1d(y)
    if x.shape != y.shape:
        raise ValueError("x和y的形状不匹配")
    prepared = prep(polygon)

    def recursion(x, y):
        xmin, xmax = x.min(), x.max()
        ymin, ymax = y.min(), y.max()
        xflag = math.isclose(xmin, xmax)
        yflag = math.isclose(ymin, ymax)
        mask = np.zeros(x.shape, dtype=bool)

        if xflag and yflag:
            point = sgeom.Point(xmin, ymin)
            mask[:] = prepared.contains(point)
            return mask

        xmid = (xmin + xmax) / 2
        ymid = (ymin + ymax) / 2

        if xflag or yflag:
            line = sgeom.LineString([(xmin, ymin), (xmax, ymax)])
            if prepared.contains(line):
                mask[:] = True
            elif prepared.intersects(line):
                if xflag:
                    m1 = (y >= ymin) & (y <= ymid)
                    m2 = (y >= ymid) & (y <= ymax)
                else:
                    m1 = (x >= xmin) & (x <= xmid)
                    m2 = (x >= xmid) & (x <= xmax)
                if m1.any():
                    mask[m1] = recursion(x[m1], y[m1])
                if m2.any():
                    mask[m2] = recursion(x[m2], y[m2])
            return mask

        box = sgeom.box(xmin, ymin, xmax, ymax)
        if prepared.contains(box):
            mask[:] = True
        elif prepared.intersects(box):
            m1 = (x >= xmid) & (x <= xmax) & (y >= ymid) & (y <= ymax)
            m2 = (x >= xmin) & (x <= xmid) & (y >= ymid) & (y <= ymax)
            m3 = (x >= xmin) & (x <= xmid) & (y >= ymin) & (y <= ymid)
            m4 = (x >= xmid) & (x <= xmax) & (y >= ymin) & (y <= ymid)
            if m1.any():
                mask[m1] = recursion(x[m1], y[m1])
            if m2.any():
                mask[m2] = recursion(x[m2], y[m2])
            if m3.any():
                mask[m3] = recursion(x[m3], y[m3])
            if m4.any():
                mask[m4] = recursion(x[m4], y[m4])
        return mask

    return recursion(x, y)


def add_Chinese_provinces(ax, **kwargs):
    """给 GeoAxes 添加中国省界。"""
    proj = ccrs.PlateCarree()
    reader = Reader(str(CHINA_SHP_PATH))
    provinces = cfeature.ShapelyFeature(reader.geometries(), proj)
    ax.add_feature(provinces, **kwargs)


def set_map_ticks(ax, dx=60, dy=30, nx=0, ny=0, labelsize="medium"):
    """为 PlateCarree 投影设置刻度与刻度标签。"""
    if not isinstance(ax.projection, ccrs.PlateCarree):
        raise ValueError("Projection of ax should be PlateCarree!")
    proj = ccrs.PlateCarree()

    major_xticks = np.arange(-180, 180 + 0.9 * dx, dx)
    ax.set_xticks(major_xticks, crs=proj)
    if nx > 0:
        ddx = dx / (nx + 1)
        minor_xticks = np.arange(-180, 180 + 0.9 * ddx, ddx)
        ax.set_xticks(minor_xticks, minor=True, crs=proj)

    major_yticks = np.arange(-90, 90 + 0.9 * dy, dy)
    ax.set_yticks(major_yticks, crs=proj)
    if ny > 0:
        ddy = dy / (ny + 1)
        minor_yticks = np.arange(-90, 90 + 0.9 * ddy, ddy)
        ax.set_yticks(minor_yticks, minor=True, crs=proj)

    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.tick_params(labelsize=labelsize)


def set_map_ticks2(ax, dx=60, dy=30, nx=0, ny=0, labelsize="medium"):
    """简化版地图刻度设置。"""

    def custom_formatter(value, pos, latlon):
        if pos == 0:
            return f"{value}deg{latlon}"
        return f"{value}deg{latlon}"

    if not isinstance(ax.projection, ccrs.PlateCarree):
        raise ValueError("Projection of ax should be PlateCarree!")
    proj = ccrs.PlateCarree()

    major_xticks = np.arange(-180, 180 + 0.9 * dx, dx)
    ax.set_xticks(major_xticks, crs=proj)
    if nx > 0:
        ddx = dx / (nx + 1)
        minor_xticks = np.arange(-180, 180 + 0.9 * ddx, ddx)
        ax.set_xticks(minor_xticks, minor=True, crs=proj)

    major_yticks = np.arange(-90, 90 + 0.9 * dy, dy)
    ax.set_yticks(major_yticks, crs=proj)
    if ny > 0:
        ddy = dy / (ny + 1)
        minor_yticks = np.arange(-90, 90 + 0.9 * ddy, ddy)
        ax.set_yticks(minor_yticks, minor=True, crs=proj)

    _ = custom_formatter
    ax.tick_params(labelsize=labelsize)
