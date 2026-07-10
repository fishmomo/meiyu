"""
处理某时刻的沿锋面2拟合线上多个切线上的的湿度剖面结果。
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
from nc_compat import open_dataset_compat
from project_paths import era5_file, era5_front_mask

ds = open_dataset_compat(era5_file("201706.nc"))

lats = ds.latitude.values
lons = ds.longitude.values
lon2d, lat2d = np.meshgrid(lons, lats)
dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)

E_95 = np.where(lons == 95)[0][0]
E_130 = np.where(lons == 130)[0][0]
N_20 = np.where(lats == 20)[0][0]
N_40 = np.where(lats == 40)[0][0]

theta_e_list = []
for i in range(11, 11+26):  #fengmian1  5:5+14;  fengmian2  11:11+26

    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
    ds_mask = open_dataset_compat(era5_front_mask(2, DT))

    mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
    mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
    lon_scatter = lon2d[mask]
    lat_scatter = lat2d[mask]

    print(ds.valid_time[i].values)
    T = ds['t'].isel(valid_time=i, pressure_level=2)
    RH = ds['r'].isel(valid_time=i, pressure_level=2)
    Td = dewpoint_from_relative_humidity(T, RH)
    theta_e = equivalent_potential_temperature(850 * units.hPa, T, Td)

    # 梯度
    grad_thetae_x, grad_thetae_y = mpcalc.gradient(theta_e, deltas=(dy, dx))
    grad_thetae_mag = np.sqrt(grad_thetae_x**2 + grad_thetae_y**2)
    theta_e_list.append(np.array(grad_thetae_mag)[mask].mean())

    # 可视化
    # fig = plt.figure(figsize=(10, 8))
    # ax = plt.axes(projection=ccrs.PlateCarree())
    # levels = np.linspace(0, 0.00040, 11)
    # cf = ax.contourf(lon2d, lat2d, np.array(grad_thetae_mag), levels=levels, cmap='YlOrRd', extend='max')
    # set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    # ax.scatter(lon_scatter, lat_scatter, s=2, color='blue', alpha=0.8)
    # ax.set_title(f"{DT}", loc='left', fontsize=15)
    # # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    # ax.set_ylim([20, 40])
    # ax.set_xlim([95, 130])
    # cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    # plt.colorbar(cf, label='|θe| (K/m)', cax=cax1)
    # DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    # ax.coastlines(color='gray')
    # plt.savefig(r"H:\我的业务\MeiYu\锋生函数图\201706\fengmian1\{}.png".format(DT), bbox_inches='tight')
    # plt.close()

# 从ERA5资料获取CPAE结果
ds_cape = open_dataset_compat(era5_file("ERA5-CAPE.nc"))
cape = ds_cape.cape
 
ds.valid_time[11].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")

cape_maskmean = []
DT_list = []
for i in range(11, 11+26):  #11:11+26

    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
    print(DT)
    DT_list.append(DT[5:])
    ds_mask = open_dataset_compat(era5_front_mask(2, DT))

    mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
    mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
    cape_temp = cape[i,:,:].values
    cape_maskmean.append(cape_temp[mask].mean())
cape_arr = np.array(cape_maskmean)

 
for row in cape_arr:
    print(np.round(row, 6))

 
for row in cape_arr:
    print('\t'+str(np.round(row, 2))+'\t')

 
fig = plt.figure(figsize=(5,4),dpi=200)
ax = fig.add_subplot(211)
ax.plot(cape_arr, label='cape', marker='^')
ax.set_ylabel('CAPE(J/kg)', fontsize=13)
ax.set_xticks([])

ax2 = fig.add_subplot(212)
ax2.plot(theta_e_list, marker='^')
ax2.set_ylabel('|θe|(K/m)', fontsize=13)
ax2.set_xticks(np.arange(0, len(cape_arr), 3))
ax2.set_xticklabels(DT_list[::3], rotation=45, fontsize=8)

 
from skimage import measure
from scipy.interpolate import RegularGridInterpolator

 
#### 读取垂直速度数据
ds_w = open_dataset_compat(era5_file("ERA5_RH_201706.nc"))
ds_w

# #### i的开始

i_time=15 # 对应2017-06-23T18
DT = ds.valid_time[i_time].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
print(DT)
ds_mask = open_dataset_compat(era5_front_mask(1, DT))
mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values

 
# 提取边界轮廓（返回的是一组坐标点）
contours = measure.find_contours(mask, level=0.5)

# 通常只用最大的轮廓
largest_contour = max(contours, key=lambda x: x.shape[0])

# 可视化边界点
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

#### 绘制边界点和拟合线、切线
plt.scatter(x, y, label='edge points')
plt.plot(x, y_fit, color='r', label='polyfit points')
for i in range(len(sampled_vx)):
    plt.plot(sampled_vx[i], sampled_vy[i], color='green', linestyle = '-')
plt.scatter(x_sample, y_sample, s=20, color='blue', marker='s')
plt.legend()
plt.show()
 
levels = ds_w.pressure_level.values
W = ds_w['r'].isel(valid_time=i_time)
DT2 = ds_w.valid_time[i_time].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
print(DT == DT2)
# 假设你有 lon, lat, level, 以及 w(lon, lat, level)
interp = RegularGridInterpolator((levels, lats, lons), W, bounds_error=False, fill_value=np.nan)

 
# 假设你有 lon, lat, level, 以及 w(lon, lat, level)
interp = RegularGridInterpolator((levels, lats, lons), W, bounds_error=False, fill_value=np.nan)

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

n_profiles = len(w_profile)
ncols = 5
nrows = (n_profiles + ncols - 1) // ncols

#### 绘制切线上的湿度剖面图
fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4*ncols, 3*nrows), constrained_layout=True)
lev_color = np.linspace(0, 100, 11)
for i in range(n_profiles):
    ax = axes.flat[i]
    cf = ax.contourf(np.arange(0,20), levels, w_profile[i].T, cmap='RdYlBu', levels=lev_color, extend='max')
    ax.invert_yaxis()
    ax.set_title(f'Profile {i+1}', fontsize=15)
    if i == 0 or i == 5:
        ax.set_ylabel('Pressure (hPa)', fontsize=15)
        ax.set_yticks(levels[::4])  # 或根据levels密度设定合适刻度
    else:
        ax.set_yticks([])
    ax.set_xticks([])

# 删除多余空子图（如果有）
for j in range(n_profiles, nrows * ncols):
    fig.delaxes(axes.flat[j])

# 添加 colorbar 到右侧整张图
cbar = fig.colorbar(cf, ax=axes.ravel().tolist(), shrink=0.75, pad=0.02)
cbar.set_label('RH(%)', fontsize=16)
cbar.ax.tick_params(labelsize=15)
plt.show()

#### 绘制锋面与拟合线的空间地理位置分布图
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels_color = np.linspace(0, 0.00040, 11)
cf = ax.contourf(lon2d, lat2d, mask.astype(int), levels=levels_color, cmap='YlOrRd', extend='max')
ax.plot(x, y_fit, 'b-')
ax.plot(sampled_vx[8], sampled_vy[8], 'orange', '-')
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
# ax.scatter(lon_scatter, lat_scatter, s=2, color='blue', alpha=0.8)
ax.set_title(f"{DT}", loc='left', fontsize=15)
# ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
# ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])
ax.coastlines(color='gray')
plt.show()

 



