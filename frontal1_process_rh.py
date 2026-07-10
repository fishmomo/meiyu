"""
与frontal1_process_w类似，处理某时刻的锋面1结果的相对湿度多剖面结果。
"""  
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import metpy.calc as mpcalc
from metpy.units import units
from metpy.interpolate import log_interpolate_1d
import os
from datetime import datetime, timedelta
from plot_picture_function import set_map_ticks,add_Chinese_provinces
from metpy.calc import equivalent_potential_temperature, dewpoint_from_relative_humidity
from metpy.units import units
from glob import glob
from nc_compat import open_dataset_compat
from project_paths import cra40_front_mask, cra40_glob
  
# #### 读取CRA40垂直速度数据

  
dir_path = cra40_glob("")
files_path = glob(os.path.join(dir_path, 'CRA40_RHU_2017*.grib2')) #VVP RHU
time_list = [p[-37:-27] for p in files_path]
# time_list

  
from skimage import measure
from scipy.interpolate import RegularGridInterpolator
  
# #### i的开始

i_time=7
DT = datetime.strptime(time_list[i_time], "%Y%m%d%H").strftime("%Y-%m-%dT%H")
print(DT)

  
ds = open_dataset_compat(files_path[i_time])
lons = ds.longitude.values
lats = ds.latitude.values
N_40 = np.where(lats == 40.0)[0][0]
N_20 = np.where(lats == 20.0)[0][0]
E_95 = np.where(lons == 95.0)[0][0]
E_130 = np.where(lons == 130.0)[0][0]
ds_mask = open_dataset_compat(cra40_front_mask(2, DT))
mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values

# 提取边界轮廓（返回的是一组坐标点）
contours = measure.find_contours(mask, level=0.5)

# 通常只用最大的轮廓
largest_contour = max(contours, key=lambda x: x.shape[0])

# 可视化
plt.imshow(mask, cmap='gray')
plt.plot(largest_contour[:, 1], largest_contour[:, 0], 'r')
plt.show()

x = np.array([lons[int(i)] for i in largest_contour[:, 1]])
y = np.array([lats[int(i)] for i in largest_contour[:, 0]])

z = np.polyfit(x, y, deg=4)  # 拟合三次多项式
p = np.poly1d(z)
y_fit = p(x)

# 原始密集点
x_dense = np.linspace(np.min(x), np.max(x), 1000)
y_dense = p(x_dense)

# 计算累计弧长
dx = np.diff(x_dense)
dy = np.diff(y_dense)
dD = np.sqrt(dx**2 + dy**2)
s = np.concatenate(([0], np.cumsum(dD)))  # 弧长累计

# 在弧长上均匀采样
s_uniform = np.linspace(0, s[-1], 10)
x_sample = np.interp(s_uniform, s, x_dense)
y_sample = p(x_sample)

  
slopes_new = []
delta_x = 0.1
for i in range(len(x_sample)):
    temp1 = p(x_sample[i] + delta_x)
    temp2 = p(x_sample[i] - delta_x)
    slope_temp = (temp1-temp2) / (delta_x * 2)
    slopes_new.append(slope_temp)
    print(slope_temp)
slopes_new = np.array(slopes_new)

# dp_dx = np.polyder(p)
# slopes = dp_dx(x)  # 每个 x 上的导数 = 切线斜率

dx = 1 / np.sqrt(1 + slopes_new**2)
dy = slopes_new / np.sqrt(1 + slopes_new**2)

# 法向量（垂直切线方向）：
nx = -dy
ny = dx

dist = 1  # 每步距离（单位根据你经纬网格距离来定，例如km）
n_points = 20
offsets = np.linspace(-dist, dist, n_points)  # 距离数组

sampled_vx = []
sampled_vy = []

for i in range(len(x_sample)):
    sample_vx = x_sample[i] + offsets * nx[i]
    sample_vy = y_sample[i] + offsets * ny[i]
    sampled_vx.append(sample_vx)
    sampled_vy.append(sample_vy)

plt.scatter(x, y, label='edge points')
plt.plot(x, y_fit, color='r', label='polyfit points')
for i in range(len(sampled_vx)):
    plt.plot(sampled_vx[i], sampled_vy[i], color='green', linestyle = '-')
plt.scatter(x_sample, y_sample, s=20, color='blue', marker='s')
plt.legend()
  
# #### 叠加等熵面结果

files_path2 = glob(os.path.join(dir_path, 'CRA40_TEM_2017*.grib2'))
files_path2[i_time]

ds_temp = open_dataset_compat(files_path2[i_time])
ds_temp.valid_time.values

rh = ds.r[:-4,:,:]
tmp = ds_temp.t[:-10,:,:]
levels = ds.isobaricInhPa.values[:-4]
level_3d = np.broadcast_to(
    levels[:, None, None],
    rh.shape
)
Td = dewpoint_from_relative_humidity(tmp, rh)
theta_e = equivalent_potential_temperature(level_3d * units.hPa, tmp, Td)
 
lats = ds.latitude.values
lons = ds.longitude.values

W = rh.values
print(ds.valid_time.values)
# 假设你有 lon, lat, level, 以及 w(lon, lat, level)
interp = RegularGridInterpolator((levels, lats, lons), W, bounds_error=False, fill_value=np.nan)
interp_theta = RegularGridInterpolator((levels, lats, lons), theta_e.values, bounds_error=False, fill_value=np.nan)

# 假设你有 lon, lat, level, 以及 w(lon, lat, level)
sample_points = []
w_profile = []
for i_sample in range(len(sampled_vx)):
    sample_x_temp = sampled_vx[i_sample]
    sample_y_temp = sampled_vy[i_sample]
    w_profile_temp = []
    for sx, sy in zip(sample_x_temp, sample_y_temp):
        for lev in levels:
            sample_points.append([lev, sy, sx])  # 注意顺序 (z, y, x)
            w_profile_temp.append(interp([lev, sy, sx])[0])
    w_profile.append(np.array(w_profile_temp).reshape(n_points, levels.shape[0]))
sample_points = np.array(sample_points)

# 假设你有 lon, lat, level, 以及 w(lon, lat, level)
sample_points = []
theta_profile = []
for i_sample in range(len(sampled_vx)):
    sample_x_temp = sampled_vx[i_sample]
    sample_y_temp = sampled_vy[i_sample]
    theta_profile_temp = []
    for sx, sy in zip(sample_x_temp, sample_y_temp):
        for lev in levels:
            sample_points.append([lev, sy, sx])  # 注意顺序 (z, y, x)
            theta_profile_temp.append(interp_theta([lev, sy, sx])[0])
    theta_profile.append(np.array(theta_profile_temp).reshape(n_points, levels.shape[0]))
sample_points = np.array(sample_points)

  
n_profiles = len(w_profile)
ncols = 5
nrows = (n_profiles + ncols - 1) // ncols

fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4*ncols, 3*nrows), constrained_layout=True)

# lev_color = np.linspace(-0.5, 0.5, 11)
lev_color = np.linspace(60, 100, 11)
lev_color2 = np.linspace(300, 400, 21)
for i in range(n_profiles):
    ax = axes.flat[i]
    cf = ax.contourf(np.arange(0,20), levels, w_profile[i].T, cmap='Blues', levels=lev_color, extend='max')#RdYlBu
    cs = ax.contour(np.arange(0,20), levels, theta_profile[i].T, cmap='hot', levels=lev_color2)
    ax.invert_yaxis()
    ax.set_title(f'Profile {i+1}', fontsize=15)
    if i == 0 or i == 5:
        ax.set_ylabel('Pressure (hPa)', fontsize=15)
        ax.set_yticks(levels[::4])  # 或根据levels密度设定合适刻度
    else:
        ax.set_yticks([])
    ax.set_xticks([])
    ax.clabel(cs, inline=True, fontsize=12, fmt='%d')

# 删除多余空子图（如果有）
for j in range(n_profiles, nrows * ncols):
    fig.delaxes(axes.flat[j])

# 添加 colorbar 到右侧整张图
cbar = fig.colorbar(cf, ax=axes.ravel().tolist(), shrink=0.75, pad=0.02)
cbar.set_label('RH(%)', fontsize=16)
cbar.ax.tick_params(labelsize=15)

plt.show()

fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels_color = np.linspace(0, 0.00040, 11)
cf = ax.contourf(lons, lats, mask.astype(int), levels=levels_color, cmap='YlOrRd', extend='max')
ax.plot(x, y_fit, 'b-')
for i in range(0, 10):
    ax.plot(sampled_vx[i], sampled_vy[i], 'orange', '-')
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
# ax.scatter(lon_scatter, lat_scatter, s=2, color='blue', alpha=0.8)
ax.set_title(f"{DT}", loc='left', fontsize=15)
# ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
# ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])
ax.coastlines(color='gray')

  



