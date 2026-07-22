# 
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import metpy.calc as mpcalc
from metpy.units import units
from metpy.interpolate import log_interpolate_1d
import os
from glob import glob

from datetime import datetime, timedelta
from plot_picture_function import set_map_ticks,add_Chinese_provinces
from nc_compat import open_dataset_compat, stage_input_path, to_netcdf_compat
from project_paths import (
    cra40_file,
    cra40_glob,
    cra40_front_extend,
    cra40_front_mask,
    cra40_front2_offset,
    era5_file,
    legacy_figure_path,
)

# 
import gc
gc.collect()

# 
file_list = sorted(glob(cra40_glob("CRA40*.nc"), recursive=True))
file_list

# 
ds = open_dataset_compat(file_list[0])


def Get_F(i, u_arr, v_arr, tmp_arr):
    u = u_arr.isel(time=i, level=6)  # 选择第一个时间点, 5对应2017/06/21 00UTC
    v = v_arr.isel(time=i, level=6)  # level=6, 850hPa层
    t = tmp_arr.isel(time=i, level=6)

    # 提取坐标
    lon2d, lat2d = np.meshgrid(lon, lat)

    # 2. 转单位（MetPy 需要）
    u = u.metpy.quantify().metpy.convert_units("m/s")
    v = v.metpy.quantify().metpy.convert_units("m/s")
    t = t.metpy.quantify().metpy.convert_units("K")

    # 3. 计算网格间距（米）
    dx, dy = mpcalc.lat_lon_grid_deltas(lon, lat)

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

from metpy.calc import equivalent_potential_temperature, dewpoint_from_relative_humidity
from metpy.units import units


#### 目标时段06-21T06 06-28T06
#### 叠加锋面1和锋面2的人工打点和熵位温分布
thethae_list = []
for i in range(7, 30):  #fengmian1索引范围 1:15, fengmian2索引范围 7:30
    filepath = file_list[i]
    ds = open_dataset_compat(filepath)
    lon = ds.longitude.values
    lat = ds.latitude.values
    level = ds.level.values
    lon2d, lat2d = np.meshgrid(lon, lat)
    time_ = np.datetime64(
            datetime.strptime(os.path.basename(file_list[i])[6:-3],'%Y%m%d%H')
            )
    ### 物理量
    # u = ds.u
    # v = ds.v
    rh = ds.rh
    tmp = ds.tmp

    T = tmp.isel(level=6) #850hPa
    RH = rh.isel(level=6)
    Td = dewpoint_from_relative_humidity(T, RH)
    theta_e = equivalent_potential_temperature(850 * units.hPa, T, Td)
    DT = time_.astype('datetime64[s]').item().strftime("%Y-%m-%dT%H")
    print(DT)
    mask_f1 = np.zeros([lat.shape[0], lon.shape[0]]).astype(bool)
    mask_f2 = np.zeros([lat.shape[0], lon.shape[0]]).astype(bool)
    E_95 = np.where(lon == 95)[0][0]
    E_130 = np.where(lon == 130)[0][0]
    N_20 = np.where(lat == 20)[0][0]
    N_40 = np.where(lat == 40)[0][0]
    f1_path = cra40_front_mask(1, DT)
    if os.path.exists(f1_path):
        ds_mask_f1 = open_dataset_compat(f1_path)
        mask_f1[N_40:N_20+1, E_95:E_130+1] = ds_mask_f1.ind_area_bool.values
        lon_scatter_f1 = lon2d[mask_f1]
        lat_scatter_f1 = lat2d[mask_f1]
    f2_path = cra40_front_mask(2, DT)
    if os.path.exists(f2_path):
        ds_mask_f2 = open_dataset_compat(f2_path)
        mask_f2[N_40:N_20+1, E_95:E_130+1] = ds_mask_f2.ind_area_bool.values
        lon_scatter_f2 = lon2d[mask_f2]
        lat_scatter_f2 = lat2d[mask_f2]
        thethae_list.append(theta_e.values[mask_f2].mean())
    # 梯度
    dx, dy = mpcalc.lat_lon_grid_deltas(lon, lat)
    grad_thetae_x, grad_thetae_y = mpcalc.gradient(theta_e, deltas=(dy, dx))
    grad_thetae_mag = np.sqrt(grad_thetae_x**2 + grad_thetae_y**2)
    # 可视化
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    levels = np.linspace(0, 0.00020, 11)
    cf = ax.contourf(lon2d, lat2d, np.array(grad_thetae_mag), levels=levels, cmap='YlOrRd', extend='max')
    if os.path.exists(f1_path):
        ax.scatter(lon_scatter_f1, lat_scatter_f1, s=2, color='blue', alpha=0.8)
    if os.path.exists(f2_path):
        ax.scatter(lon_scatter_f2, lat_scatter_f2, s=2, color='green', alpha=0.8)
    # ax.contour(lon2d, lat2d, F, levels=[0], colors='blue', linewidths=2)  # F=0 等值线
    # ax.contour(lon2d, lat2d, front_mask, levels=[0.5], colors='black', linewidths=1.2)
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    cbar = plt.colorbar(cf, label='|θe| (K/m)', cax=cax1)
    cbar.ax.tick_params(labelsize=12)
    set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    ax.set_title(f"{DT}  850hPa", loc='left', fontsize=15)
    ax.coastlines(color='gray')
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    # savepath = r"H:\我的业务\MeiYu\锋生函数图\PPT_pic\850_thetae_CRA40"
    # if os.path.exists(savepath):
    #     pass
    # else:
    #     os.mkdir(savepath)
    #     print("已创建：", savepath)
    # plt.savefig(savepath+r"\{}.png".format(DT), bbox_inches='tight')
    # np.save(savepath+r"\{}.npy".format(DT), np.array(grad_thetae_mag)[N_40:N_20+1, E_95:E_130+1])
    plt.close()
    ds.close()

#### 绘制研究时段间打点区锋面CAPE和θe格点平均值序列
ds_cape = open_dataset_compat(era5_file("ERA5-CAPE.nc"))
lat_era5 = ds_cape.latitude.values
lon_era5 = ds_cape.longitude.values
cape_era5 = ds_cape.cape.values
E_95 = np.where(lon_era5 == 95)[0][0]
E_130 = np.where(lon_era5 == 130)[0][0]
N_20 = np.where(lat_era5 == 20)[0][0]
N_40 = np.where(lat_era5 == 40)[0][0]
cape_list = []
DT_list = []
for i in range(7, 30):
    time_ = np.datetime64(
            datetime.strptime(os.path.basename(file_list[i])[6:-3],'%Y%m%d%H')
            )
    DT = time_.astype('datetime64[s]').item().strftime("%Y-%m-%dT%H")
    DT_list.append(DT[5:])
    print(DT, ds_cape.valid_time[11+i-7].values)
    mask_era5 = np.zeros([lat_era5.shape[0], lon_era5.shape[0]]).astype(bool)
    ds_mask = open_dataset_compat(cra40_front_mask(2, DT))
    mask_era5[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
    cape_list.append(cape_era5[11+i-7][mask_era5].mean())


fig = plt.figure(figsize=(5,4),dpi=200)
ax = fig.add_subplot(211)
ax.plot(cape_list, label='cape', marker='^')
ax.set_ylabel('CAPE(J/kg)', fontsize=13)
ax.set_xticks([])

ax2 = fig.add_subplot(212)
ax2.plot(thethae_list, marker='^')
ax2.set_ylabel('θe(K)', fontsize=13)
ax2.set_xticks(np.arange(0, len(thethae_list), 3))
ax2.set_xticklabels(DT_list[::3], rotation=45, fontsize=8)

#### 自写计算cape,目前弃用
# cape_mean_list = []
# for i in range(7, 29):  #fengmian1 1:15, fengmian2 7:29
#     filepath = file_list[i]
#     ds = xr.open_dataset(filepath)
#     lon = ds.longitude.values
#     lat = ds.latitude.values
#     level = ds.level.values * units.hPa
#     lon2d, lat2d = np.meshgrid(lon, lat)
#     time_ = np.datetime64(
#             datetime.strptime(os.path.basename(file_list[i])[6:-3],'%Y%m%d%H')
#             )
#     mask = np.zeros([lat.shape[0], lon.shape[0]]).astype(bool)
#     E_95 = np.where(lon == 95)[0][0]
#     E_130 = np.where(lon == 130)[0][0]
#     N_20 = np.where(lat == 20)[0][0]
#     N_40 = np.where(lat == 40)[0][0]
#     DT = time_.astype('datetime64[s]').item().strftime("%Y-%m-%dT%H")
#     print(DT)
#     ds_mask = xr.open_dataset(r"D:\Yu_jie\pysider6\meiyu\CRA40_fengmian2\{}.nc".format(DT))
#     mask[N_40:N_20+1, E_95:E_130+1] = ds_mask.ind_area_bool.values
#     lon_indices = np.where(mask == True)[1]  # 获取经度索引
#     lat_indices = np.where(mask == True)[0]  # 获取纬度索引
#     ### 物理量
#     # u = ds.u
#     # v = ds.v
#     rh = ds.rh.values * units.percent 
#     tmp = ds.tmp.values * units.K
#     Td = dewpoint_from_relative_humidity(tmp, rh)
#     cape_temp = []
#     for i_lat, i_lon in zip(lat_indices, lon_indices):
#             T_prof = tmp[:, i_lat, i_lon]
#             Td_prof = Td[:, i_lat, i_lon]
#             # print(T_prof.shape, level.shape, Td_prof.shape)
#             parp = parcel_profile(level, T_prof[0], Td_prof[0])
#             cape = mpcalc.cape_cin(level, T_prof, Td_prof, parp)
#             cape_temp.append(cape[0].magnitude)
#     cape_mean_list.append(np.mean(cape_temp))
    


#### 绘制降水分布
import pygrib
import glob

prep_list = glob.glob(cra40_glob("CRA40LAND_PRECIP_201706*.grib"))

for i in range(1, 30):
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
    cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
    cbar = plt.colorbar(cf, label='precipitation (mm)', cax=cax1)
    cbar.ax.tick_params(labelsize=12)
    set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
    ax.set_title(f"{DT}", loc='left', fontsize=15)
    ax.coastlines(color='gray')
    ax.set_ylim([20, 40])
    ax.set_xlim([95, 130])
    savepath = legacy_figure_path("PPT_pic", "SP_CRA40", filename="")
    if os.path.exists(savepath):
        pass
    else:
        os.mkdir(savepath)
        print("已创建：", savepath)
    plt.savefig(legacy_figure_path("PPT_pic", "SP_CRA40", filename=f"{DT}.png"), bbox_inches='tight')
    plt.close()


#### 锋面偏移以北地区或以南地区的掩膜区域。

prep_list = glob.glob(cra40_glob("CRA40LAND_PRECIP_201706*.grib"))

i = 21
DT = datetime.strptime(prep_list[i][-36:-26], "%Y%m%d%H").strftime("%Y-%m-%dT%H")
lonmin, lonmax = 0.125, 359.875
latmin, latmax = -89.875, 89.875
npt=0.25
lon_x = np.linspace(lonmin, lonmax, int((lonmax-lonmin)/npt)+1)
lat_y = np.linspace(latmax, latmin, int((latmax-latmin)/npt)+1)
lon2d, lat2d = np.meshgrid(lon_x, lat_y)
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

mask_f2 = np.zeros([lat_y.shape[0], lon_x.shape[0]]).astype(bool)
f2_path = cra40_front_mask(2, DT)
if os.path.exists(f2_path):
    ds_mask_f2 = open_dataset_compat(f2_path)
    mask_f2[N_40:N_20, E_95:E_130] = ds_mask_f2.ind_area_bool.values
    lon_scatter_f2 = lon2d[mask_f2]
    lat_scatter_f2 = lat2d[mask_f2]

from scipy.ndimage import label
from sklearn.decomposition import PCA

x_coords, y_coords = lon_scatter_f2, lat_scatter_f2

points = np.column_stack((x_coords, y_coords))
# 主成分分析（PCA）
pca = PCA(n_components=2)
pca.fit(points)

center = pca.mean_              # 中心点
direction = pca.components_[0]  # 第一主成分方向（单位向量）
length = 20                     # 可调整主轴线的显示长度

#所有散点投影到direction上，为标量
relative = points - center
projections = relative @ direction #矩阵乘法，点积，在主轴上的投影

idx_min = np.argmin(projections)
idx_max = np.argmax(projections)

end_point1 = center + projections[idx_min]*direction
end_point2 = center + projections[idx_max]*direction
# 构造中心线两个端点
line_start = center - direction * length
line_end = center + direction * length

# 垂直方向的单位向量(右侧)
vx, vy = direction
v_perp = np.array([-vy, vx])
#偏移距离
offset_distance = 1

#计算左右平移后的两条线
offset = v_perp * offset_distance

line1_start = line_start + offset
line1_end = line_end + offset

line2_start = line_start - offset
line2_end = line_end - offset

f2_extend_path = cra40_front_extend(2, DT)
ds_extendmask_f2 = open_dataset_compat(f2_extend_path)

lon_scatter_offset1 = lon_scatter_f2+offset[0]
lat_scatter_offset1 = lat_scatter_f2+offset[1]
mask_offset = np.zeros(ds_extendmask_f2.ind_area_bool.values.shape).astype(bool)
lon = ds_extendmask_f2.lon.values
lat = ds_extendmask_f2.lat.values
for n in range(len(lon_scatter_offset1)):
    lon_min_indice = np.argmin(np.abs(lon-lon_scatter_offset1[n]))
    lat_min_indice = np.argmin(np.abs(lat-lat_scatter_offset1[n]))
    mask_offset[lat_min_indice, lon_min_indice] = True

### 绘图
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
levels = np.linspace(0, 50, 11)
cf = ax.contourf(lon_cut, lat_cut, prep_cut, levels=levels, cmap='YlGnBu', extend='max')
if os.path.exists(f2_path):
    ax.scatter(lon_scatter_f2, lat_scatter_f2, s=2, color='green', alpha=0.8)
    ax.scatter(lon_scatter_f2+offset[0], lat_scatter_f2+offset[1], s=2, color='red', alpha=0.8)
    ax.scatter(lon_scatter_f2-offset[0], lat_scatter_f2-offset[1], s=2, color='blue', alpha=0.8)
cax1 = fig.add_axes([ax.get_position().x1 + 0.01, ax.get_position().y0, 0.01, ax.get_position().height])
cbar = plt.colorbar(cf, label='precipitation (mm)', cax=cax1)
cbar.ax.tick_params(labelsize=12)
set_map_ticks(ax, dx=4, dy=3, nx=1, ny=1, labelsize='large')
ax.set_title(f"{DT}", loc='left', fontsize=15)
ax.coastlines(color='gray')
ax.set_ylim([20, 40])
ax.set_xlim([95, 130])
savepath = legacy_figure_path("PPT_pic", "fengmian_pianyi", "time1", filename="")
if os.path.exists(savepath):
    pass
else:
    os.mkdir(savepath)
    print("已创建：", savepath)
plt.savefig(legacy_figure_path("PPT_pic", "fengmian_pianyi", "time1", filename=f"{DT}-2.png"), bbox_inches='tight')
plt.close()

ds_extendmask_f2.ind_area_bool.values = mask_offset
to_netcdf_compat(ds_extendmask_f2, cra40_front2_offset("offset1.nc"))
ds_extendmask_f2.close()




