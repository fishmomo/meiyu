"""
与frontal1_process_w类似，处理某时刻的锋面1结果的相对湿度多剖面结果，同时对某时刻的锋面进行拆分子区域，输出掩膜数据。
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
from nc_compat import open_dataset_compat, stage_input_path, to_netcdf_compat
from project_paths import cra40_front_extend, cra40_front_mask, cra40_front2_subarea, cra40_glob
  
# #### 读取CRA40垂直速度数据

dir_path = cra40_glob("")
files_path = glob(os.path.join(dir_path, 'CRA40_RHU_2017*.grib2')) #VVP RHU
time_list = [p[-37:-27] for p in files_path]
# time_list
  
from skimage import measure
from scipy.interpolate import RegularGridInterpolator

#### 选取指定时刻并获取区域边界点并对锋面结构进行曲线拟合，进而做沿曲线的等分切线。 
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


#### 绘制降水分布与锋面拟合线、切线位置
import pygrib
import glob

prep_list = glob.glob(cra40_glob("CRA40LAND_PRECIP_201706*.grib"))

  
prep_list[7]

i= 7
DT = datetime.strptime(prep_list[i][-36:-26], "%Y%m%d%H").strftime("%Y-%m-%dT%H")
lonmin, lonmax = 0.125, 359.875
latmin, latmax = -89.875, 89.875
npt=0.25
lon_x = np.linspace(lonmin, lonmax, int((lonmax-lonmin)/npt)+1)
lat_y = np.linspace(latmax, latmin, int((latmax-latmin)/npt)+1)
E_95 = np.where(lon_x == 94.875)[0][0]
E_130 = np.where(lon_x == 130.125)[0][0]
N_20 = np.where(lat_y == 19.875)[0][0]
N_40 = np.where(lat_y == 40.125)[0][0]
lon_cut = lon_x[E_95:E_130+1]
lat_cut = lat_y[N_40:N_20+1]
with pygrib.open(stage_input_path(prep_list[i])) as grbs:
    grb = grbs[1]
    prep = grb.values * 3600 * 6
prep_cut = prep[N_40:N_20+1, E_95:E_130+1]
# 可视化
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels = np.linspace(0, 50, 11)
cf = ax.contourf(lon_cut, lat_cut, prep_cut, levels=levels, cmap='YlGnBu', extend='max')

plt.plot(x, y_fit, color='r', label='polyfit points')
for i in range(len(sampled_vx)):
    plt.plot(sampled_vx[i], sampled_vy[i], color='green', linestyle = '-')
plt.scatter(x_sample, y_sample, s=20, color='blue', marker='s')

cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
cbar = plt.colorbar(cf, label='precipitation (mm)', cax=cax1)
cbar.ax.tick_params(labelsize=12)
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
ax.set_title(f"{DT}", loc='left', fontsize=15)
ax.coastlines(color='gray')
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])

  
def Get_Area_latlon(i_start, i_end):
    xx, yy = np.meshgrid(lons, lats)
    points_mask = np.c_[xx[mask], yy[mask]]
    vx_line = sampled_vx[i_start]
    vy_line = sampled_vy[i_start]

    vx_line2 = sampled_vx[i_end]
    vy_line2 = sampled_vy[i_end]

    x1, y1 = vx_line[0], vy_line[0]
    x2, y2 = vx_line[-1], vy_line[-1]

    x3, y3 = vx_line2[0], vy_line2[0]
    x4, y4 = vx_line2[-1], vy_line2[-1]

    a = y1-y2
    b = x2-x1
    c = x1 * y2 - x2 * y1

    a2 = y3-y4
    b2 = x4-x3
    c2 = x3 * y4 - x4 * y3

    vals1 = a * points_mask[:,0] + b * points_mask[:,1] + c

    vals2 = a2 * points_mask[:,0] + b2 * points_mask[:,1] + c2

    result_area_lonlat = points_mask[(vals1 <= 0) & (vals2 > 0)]
    
    return result_area_lonlat

# area1_lonlat = Get_Area_latlon(0, 2)
# area2_lonlat = Get_Area_latlon(3, 5)
# area22_lonlat = Get_Area_latlon(2, 6)
# area3_lonlat = Get_Area_latlon(6, 8)

#### 选择切线分区段，将一条切线与另一条切线之间区域划分出
area1_lonlat = Get_Area_latlon(1, 4)
area2_lonlat = Get_Area_latlon(6, 8)
  
i= 7
DT = datetime.strptime(prep_list[i][-36:-26], "%Y%m%d%H").strftime("%Y-%m-%dT%H")
lonmin, lonmax = 0.125, 359.875
latmin, latmax = -89.875, 89.875
npt=0.25
lon_x = np.linspace(lonmin, lonmax, int((lonmax-lonmin)/npt)+1)
lat_y = np.linspace(latmax, latmin, int((latmax-latmin)/npt)+1)
E_95 = np.where(lon_x == 94.875)[0][0]
E_130 = np.where(lon_x == 130.125)[0][0]
N_20 = np.where(lat_y == 19.875)[0][0]
N_40 = np.where(lat_y == 40.125)[0][0]
lon_cut = lon_x[E_95:E_130+1]
lat_cut = lat_y[N_40:N_20+1]
with pygrib.open(stage_input_path(prep_list[i])) as grbs:
    grb = grbs[1]
    prep = grb.values * 3600 * 6
prep_cut = prep[N_40:N_20+1, E_95:E_130+1]
# 可视化
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels = np.linspace(0, 50, 11)
cf = ax.contourf(lon_cut, lat_cut, prep_cut, levels=levels, cmap='YlGnBu', extend='max')

plt.plot(x, y_fit, color='r', label='polyfit points')
for i in range(len(sampled_vx)):
    plt.plot(sampled_vx[i], sampled_vy[i], color='green', linestyle = '-')

plt.scatter(area1_lonlat[:,0], area1_lonlat[:,1], s=10, color='red')
plt.scatter(area2_lonlat[:,0], area2_lonlat[:,1], s=10, color='blue')

# cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
# cbar = plt.colorbar(cf, label='precipitation (mm)', cax=cax1)
# cbar.ax.tick_params(labelsize=12)
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
ax.set_title(f"{DT}", loc='left', fontsize=15)
ax.coastlines(color='gray')
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])

  
area1_lonlat[:3]

  
region = area2_lonlat

ds_mask2 = open_dataset_compat(cra40_front_extend(2, DT))
lon_mask = ds_mask2.lon.values
lat_mask = ds_mask2.lat.values
mask = np.zeros(ds_mask2.ind_area_bool.shape).astype(bool)
for j in range(len(region)):
    lon_indice = np.argmin(np.abs(region[j][0] - lon_mask))
    lat_indice = np.argmin(np.abs(region[j][1] - lat_mask))
    mask[lat_indice, lon_indice] = True

#### 输出该时刻所区域的掩膜数据
ds_mask2.ind_area_bool.values = mask
to_netcdf_compat(ds_mask2, cra40_front2_subarea("area2_lonlat_0622T18.nc"))
ds_mask2.close()

  
# #### 叠加等熵面等值线和垂直速度填色图结果
  
files_path2 = glob.glob(os.path.join(dir_path, 'CRA40_TEM_2017*.grib2'))
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

  
files_path3 = glob.glob(os.path.join(dir_path, 'CRA40_VVP_2017*.grib2')) #VVP RHU
ds_w = open_dataset_compat(files_path3[i_time])

  
W = ds_w.w.values
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
lev_color = np.linspace(-0.4, 0.4, 11)
lev_color2 = np.linspace(320, 350, 11)
for i in range(n_profiles):
    ax = axes.flat[i]
    cf = ax.contourf(np.arange(0,20), levels, w_profile[i].T, cmap='coolwarm_r', levels=lev_color, extend='both')#RdYlBu
    cs = ax.contour(np.arange(0,20), levels, theta_profile[i].T, cmap='Greys', levels=lev_color2)
    ax.invert_yaxis()
    ax.set_title(f'Profile {i+1}', fontsize=15)
    if i == 0 or i == 5:
        ax.set_ylabel('w (Pa/s)', fontsize=15)
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
cbar.set_label('w(Pa/s)', fontsize=16)
cbar.ax.tick_params(labelsize=15)

plt.show()


#### 绘制锋面的地理位置及所占区域
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels_color = np.linspace(0, 0.00040, 11)
cf = ax.contourf(lon_mask, lat_mask, mask.astype(int), levels=levels_color, cmap='YlOrRd', extend='max')
# plt.scatter(area1_lonlat[:,0], area1_lonlat[:,1], s=10, color='red')
# plt.scatter(area2_lonlat[:,0], area2_lonlat[:,1], s=10, color='blue')
# plt.scatter(area3_lonlat[:,0], area3_lonlat[:,1], s=10, color='k')
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

  



