"""
meiyu_new.frontal_info_graphic_identification 的 Docstring
evirenment: geo
内容：绘制锋面逐6小时的气象信息内容，进而识别锋面
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
from nc_compat import open_dataset_compat
from project_paths import era5_file, era5_front_mask, find_era5_mask, legacy_figure_path

#### 读取ERA5数据
ds = open_dataset_compat(era5_file("201706.nc"))

def Get_F(i, ds):
    u = ds['u'].isel(valid_time=i, pressure_level=2)  # 选择第一个时间点, 5对应2017/06/21 00UTC
    v = ds['v'].isel(valid_time=i, pressure_level=2)  # level=2, 850hPa层
    t = ds['t'].isel(valid_time=i, pressure_level=2)

    # 提取坐标
    lats = ds.latitude.values
    lons = ds.longitude.values
    lon2d, lat2d = np.meshgrid(lons, lats)

    # 2. 转单位（MetPy 需要）
    u = u.metpy.quantify().metpy.convert_units("m/s")
    v = v.metpy.quantify().metpy.convert_units("m/s")
    t = t.metpy.quantify().metpy.convert_units("K")

    # 3. 计算网格间距（米）
    dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)

    # 4. 计算温度梯度（K/m）
    grad_t_x, grad_t_y = mpcalc.gradient(t.values, deltas=(dy, dx))

    
    # 5. 温度梯度模 和 方向角θ（用于F函数）
    grad_t_mag = np.sqrt(grad_t_x**2 + grad_t_y**2)
    # 构建锋区掩膜
    # Tgrad_thresh = 5 / 100e3
    # front_mask = Tgrad_mag > Tgrad_thresh
    
    theta = np.arctan2(grad_t_y, grad_t_x)  # 注意：y 在前

    # 6. 风场偏导（m/s per m）
    dudx, dudy = mpcalc.gradient(u.values, deltas=(dy, dx))
    dvdx, dvdy = mpcalc.gradient(v.values, deltas=(dy, dx))

    # 7. 代入地转近似锋生函数公式
    F = 0.5 * grad_t_mag * ((dudx - dvdy) * np.cos(2 * theta) + (dvdx + dudy) * np.sin(2 * theta))
    return F, lat2d, lon2d

def Tdelta(i, ds):
    u = ds['u'].isel(valid_time=i, pressure_level=2)  # 选择第一个时间点, 5对应2017/06/21 00UTC
    v = ds['v'].isel(valid_time=i, pressure_level=2)  # level=2, 850hPa层
    t = ds['t'].isel(valid_time=i, pressure_level=2)

    # 提取坐标
    lats = ds.latitude.values
    lons = ds.longitude.values
    lon2d, lat2d = np.meshgrid(lons, lats)

    # 2. 转单位（MetPy 需要）
    u = u.metpy.quantify().metpy.convert_units("m/s")
    v = v.metpy.quantify().metpy.convert_units("m/s")
    t = t.metpy.quantify().metpy.convert_units("K")

    # 3. 计算网格间距（米）
    dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)

    # 4. 计算温度梯度（K/m）
    grad_t_x, grad_t_y = mpcalc.gradient(t.values, deltas=(dy, dx))


# 8. 绘图
def save_fig(i, ds, F):
    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    cf = ax.contourf(lon2d, lat2d, F * 1e9,  # 放大数值显示效果
                    levels=np.linspace(-5, 5, 21), cmap='bwr', extend='both')
    
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    cbar = plt.colorbar(cf, label='Frontogenesis (1e$^{-9}$ K/m/s)', cax=cax1)
    cbar.ax.tick_params(labelsize=12)
    set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    ax.set_title(f"{DT}", loc='left', fontsize=15)
    ax.coastlines()
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    # ax.set_title("Geostrophic Frontogenesis Function (850 hPa)")
    plt.savefig(legacy_figure_path("201706", "850", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()

for i in range(5, 5+32):  
    F_temp, lat2d, lon2d = Get_F(i, ds)
    print(np.nanmax(F_temp), np.nanmin(F_temp))
    save_fig(i, ds, F_temp)

i=28
u = ds['u'].isel(valid_time=i, pressure_level=0)  # 选择第一个时间点, 5对应2017/06/21 00UTC
v = ds['v'].isel(valid_time=i, pressure_level=0)  # level=2, 850hPa层
t = ds['t'].isel(valid_time=i, pressure_level=0)
# 提取坐标
lats = ds.latitude.values
lons = ds.longitude.values
lon2d, lat2d = np.meshgrid(lons, lats)

# 2. 转单位（MetPy 需要）
u = u.metpy.quantify().metpy.convert_units("m/s")
v = v.metpy.quantify().metpy.convert_units("m/s")
t = t.metpy.quantify().metpy.convert_units("K")

# 3. 计算网格间距（米）
dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)

# 4. 计算温度梯度（K/m）
grad_t_x, grad_t_y = mpcalc.gradient(t.values, deltas=(dy, dx))


#  5. 温度梯度模 和 方向角θ（用于F函数）
grad_t_mag = np.sqrt(grad_t_x**2 + grad_t_y**2)
# 构建锋区掩膜
Tgrad_thresh = 5 / 100e3
front_mask = np.array(grad_t_mag) > Tgrad_thresh
"""绘制熵位温"""
# 可视化
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
cf = ax.contourf(lon2d, lat2d, np.array(grad_t_mag), levels=20, cmap='YlOrRd')
# ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
# ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])
cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
plt.colorbar(cf, label='|∇T| (K/m)', cax=cax1)
# ax.set_title('锋面识别图：温度梯度 + 锋生函数F')
ax.coastlines(color='gray')

from metpy.calc import equivalent_potential_temperature, dewpoint_from_relative_humidity
from metpy.units import units

lats = ds.latitude.values
lons = ds.longitude.values
lon2d, lat2d = np.meshgrid(lons, lats)
dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)

E_95 = np.where(lons == 95)[0][0]
E_130 = np.where(lons == 130)[0][0]
N_20 = np.where(lats == 20)[0][0]
N_40 = np.where(lats == 40)[0][0]

i = 25
DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
ds_mask = open_dataset_compat(find_era5_mask(DT))

mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
lon_scatter = lon2d[mask]
lat_scatter = lat2d[mask]


theta_e_arr = np.zeros([32, 161, 281])
for i in range(5, 5+32): # 5对应2017/06/21 00UTC
    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
    ds_mask = open_dataset_compat(find_era5_mask(DT))

    mask = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
    mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
    lon_scatter = lon2d[mask]
    lat_scatter = lat2d[mask]

    # print(ds.valid_time[i].values)
    T = ds['t'].isel(valid_time=i, pressure_level=2)
    RH = ds['r'].isel(valid_time=i, pressure_level=2)
    Td = dewpoint_from_relative_humidity(T, RH)
    theta_e = equivalent_potential_temperature(850 * units.hPa, T, Td)

    #储存theta_e
    theta_e_arr[i-5,:,:] = theta_e.values

def compute_frontogenesis_thetae(thetae1, thetae2, lats, lons, delta_t_seconds):
    """
    使用两时次的熵位温θₑ计算锋生函数（梯度型）
    
    参数：
        thetae1, thetae2: 两时次的 θₑ 数据（单位 K），形状 (lat, lon)
        lats, lons: 纬度、经度数组（一维）
        delta_t_seconds: 两时次之间的间隔（单位秒）

    返回：
        F_fronto: 梯度型锋生函数，负值表示锋生（单位 K² / (m·s)）
    """
    # 1. 计算两时次的水平梯度
    dx, dy = mpcalc.lat_lon_grid_deltas(lons, lats)  # dx/dy 形状 (lat, lon-1)
    
    grad_x1, grad_y1 = mpcalc.gradient(thetae1 * units.kelvin, deltas=(dy, dx))
    grad_x2, grad_y2 = mpcalc.gradient(thetae2 * units.kelvin, deltas=(dy, dx))

    grad_mag1 = np.sqrt(grad_x1**2 + grad_y1**2)
    grad_mag2 = np.sqrt(grad_x2**2 + grad_y2**2)

    # 2. 时间导数项
    d_grad_dt = (grad_mag2 - grad_mag1) / delta_t_seconds * units('1/s')

    # 3. 代入锋生函数公式（带负号）
    F_fronto = -0.5 * grad_mag1 * d_grad_dt  # 结果单位 K²/(m·s)

    return F_fronto

thetae1 = theta_e_arr[16]
thetae2 = theta_e_arr[17]
res = compute_frontogenesis_thetae(thetae1, thetae2, lats, lons, delta_t_seconds=6*3600)
levels = np.linspace(-15e-14, 15e-14, 11)
plt.contourf(res[::-1], levels=levels, cmap='coolwarm', extend='both')

"""人工标记格点与锋生函数分布对应"""
# i = 33
# DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
for i in range(5, 34): #5对应2017/06/21 00UTC

    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
    f1_path = era5_front_mask(1, DT)
    if os.path.exists(f1_path):
        ds_mask_f1 = open_dataset_compat(f1_path)
        mask_f1 = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
        mask_f1[N_40:N_20+1, E_95:E_130+1] = ds_mask_f1.ind_area_bool.values
        lon_scatter_f1 = lon2d[mask_f1]
        lat_scatter_f1 = lat2d[mask_f1]
    f2_path = era5_front_mask(2, DT)
    if os.path.exists(f2_path):
        ds_mask_f2 = open_dataset_compat(f2_path)
        mask_f2 = np.zeros([lats.shape[0], lons.shape[0]]).astype(bool)
        mask_f2[N_40:N_20+1, E_95:E_130+1] = ds_mask_f2.ind_area_bool.values
        lon_scatter_f2 = lon2d[mask_f2]
        lat_scatter_f2 = lat2d[mask_f2]

    print(ds.valid_time[i].values)
    T = ds['t'].isel(valid_time=i, pressure_level=2)
    RH = ds['r'].isel(valid_time=i, pressure_level=2)
    Td = dewpoint_from_relative_humidity(T, RH)
    theta_e = equivalent_potential_temperature(850 * units.hPa, T, Td)

    # 梯度
    grad_thetae_x, grad_thetae_y = mpcalc.gradient(theta_e, deltas=(dy, dx))
    grad_thetae_mag = np.sqrt(grad_thetae_x**2 + grad_thetae_y**2)

    # 可视化
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    levels = np.linspace(0, 0.00040, 11)
    cf = ax.contourf(lon2d, lat2d, np.array(grad_thetae_mag), levels=levels, cmap='YlOrRd', extend='max')
    set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    if os.path.exists(f1_path):
        ax.scatter(lon_scatter_f1, lat_scatter_f1, s=2, color='purple', alpha=0.8)
    if os.path.exists(f2_path):
        ax.scatter(lon_scatter_f2, lat_scatter_f2, s=2, color='green', alpha=0.8)
    ax.set_title(f"{DT}", loc='left', fontsize=15)
    # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    plt.colorbar(cf, label='|θe| (K/m)', cax=cax1)
    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    ax.coastlines(color='gray')
    plt.savefig(legacy_figure_path("PPT_pic", "850_theta_ERA5", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()

"""某时刻熵位温"""
i=5+31 #5对应2017/06/21 00UTC 6h间隔， 36对应2017/06/29 00UTC
DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H")
ds_mask = open_dataset_compat(find_era5_mask(DT))

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

# 可视化
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels = np.linspace(0, 0.00040, 11)
cf = ax.contourf(lon2d, lat2d, np.array(grad_thetae_mag), levels=levels, cmap='YlOrRd', extend='max')
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
ax.set_title(f"{DT}", loc='left', fontsize=15)
ax.scatter(lon_scatter, lat_scatter, s=2, color='blue', alpha=0.8)
# ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
# ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])
cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
plt.colorbar(cf, label='|θe| (K/m)', cax=cax1)
ax.coastlines(color='gray')

"""700hPa湿度分布"""
for i in range(5, 5+32):  #5对应2017/06/21 00UTC， 36对应2017/06/29 00UTC
    print(ds.valid_time[i].values)
    RH = ds['r'].isel(valid_time=i, pressure_level=3) #850hPa
    grad_rh_x, grad_rh_y = mpcalc.gradient(RH.values, deltas=(dy, dx))
    rh_grad_mag = np.sqrt(grad_rh_x**2 + grad_rh_y**2)

    # 可视化
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    cf = ax.contourf(lon2d, lat2d, np.array(rh_grad_mag), levels=20, cmap='YlOrRd')
    # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    plt.colorbar(cf, label='RH(%)', cax=cax1)
    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    ax.coastlines(color='gray')
    savepath = legacy_figure_path("201706", "700_RH", filename="")
    if os.path.exists(savepath):
        pass
    else:
        os.mkdir(savepath)
        print("已创建：", savepath)
    plt.savefig(legacy_figure_path("201706", "700_RH", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()

"""散度分布"""
for i in range(5, 5+32):  # 5对应2017/06/21 00UTC, 36对应2017/06/29 00UTC
    print(ds.valid_time[i].values)
    u = ds['u'].isel(valid_time=i, pressure_level=2)  # 选择第一个时间点, 5对应2017/06/21 00UTC
    v = ds['v'].isel(valid_time=i, pressure_level=2)  # level=2, 850hPa层
    div850 = np.array(mpcalc.divergence(u, v, dx=dx, dy=dy))

    # 可视化
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    levels = np.linspace(-0.00018, 0.00018, 11)
    cf = ax.contourf(lon2d, lat2d, div850, levels=levels, cmap='coolwarm', extend='both')
    # front_mask = (np.abs(div850) > 0.00007).astype(int)
    # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    plt.colorbar(cf, label='div(s$^{-1}$)' , cax=cax1)
    # ax.set_title('锋面识别图：温度梯度 + 锋生函数F')
    ax.coastlines(color='gray')
    DT = ds.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    ax.coastlines(color='gray')
    savepath = legacy_figure_path("201706", "850_Div", filename="")
    if os.path.exists(savepath):
        pass
    else:
        os.mkdir(savepath)
        print("已创建：", savepath)
    plt.savefig(legacy_figure_path("201706", "850_Div", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()


"""绘制降水分布"""
ds_sp = open_dataset_compat(era5_file("ERA5_SP_201706.nc"))
sp = ds_sp.tp.values * 1000
for i in range(5, 34):  # 5 = '2017-06-21T06', 33 = '2017-06-28T06'
    print(ds.valid_time[i].values)

    # 可视化
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    levels = np.linspace(0, 20, 11)
    cf = ax.contourf(lon2d, lat2d, sp[i,:,:], levels=levels, cmap='YlGnBu', extend='max')
    set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    ax.set_title(f"{DT}", loc='left', fontsize=15)
    # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    cbar = plt.colorbar(cf, label='Ps(mm)', cax=cax1)
    cbar.ax.tick_params(labelsize=12)
    cbar.set_label('Ps(mm)', fontsize=13)
    DT = ds_sp.valid_time[i].values.astype('datetime64[s]').astype(timedelta).strftime("%Y-%m-%dT%H") 
    ax.coastlines(color='gray')
    savepath = legacy_figure_path("PPT_pic", "SP_ERA5", filename="")
    if os.path.exists(savepath):
        pass
    else:
        os.mkdir(savepath)
        print("已创建：", savepath)
    plt.savefig(legacy_figure_path("PPT_pic", "SP_ERA5", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()
