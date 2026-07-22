"""Lifecycle diagnostics for the independent 0.25-degree cold-vortex events."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from build_literature_cold_vortex_regions import _cell_area_km2
from cold_vortex_common_data import read_level, read_precipitation
from cold_vortex_diagnostics import core_summary, moisture_flux_convergence
from cold_vortex_regions import relative_vorticity

ROOT=Path(__file__).resolve().parent; CASES=ROOT/'data'/'processed'/'cold_vortex'/'cases'

def phase_rows(rows):
    normal=[i for i,r in enumerate(rows) if r['is_terminal_diagnostic']!='True']
    valid=[i for i in normal if r_float(rows[i].get('refined_center_z500_gpm')) is not None]
    mature=min(valid,key=lambda i:r_float(rows[i]['refined_center_z500_gpm']))
    for i,row in enumerate(rows):
        row['phase']='dissipation' if row['is_terminal_diagnostic']=='True' else ('maturity' if i==mature else ('formation' if i==normal[0] else ('development' if i<mature else 'decay')))
    return rows
def r_float(v):
    try:return float(v)
    except (TypeError,ValueError):return None
def interp_precip(values,lat,lon,target_lat,target_lon):
    grid=RegularGridInterpolator((lat[::-1],lon),values[::-1],bounds_error=False,fill_value=np.nan)
    yy,xx=np.meshgrid(target_lat,target_lon,indexing='ij'); return grid(np.c_[yy.ravel(),xx.ravel()]).reshape(yy.shape)
def fieldset(time):
    z,lat,lon=read_level('GPH',time,500); u5,_,_=read_level('WIU',time,500);v5,_,_=read_level('WIV',time,500)
    u,_,_=read_level('WIU',time,850);v,_,_=read_level('WIV',time,850);q,_,_=read_level('SHU',time,850)
    rh8,_,_=read_level('RHU',time,850);rh5,_,_=read_level('RHU',time,500);t8,_,_=read_level('TEM',time,850);t5,_,_=read_level('TEM',time,500);w,_,_=read_level('VVP',time,700)
    p,plat,plon=read_precipitation(time)
    return {'z500_gpm':z,'zeta500_s_inv':relative_vorticity(u5,v5,lat,lon),'wind850_m_s':np.hypot(u,v),'q850_kg_kg':q,'mfc850_kg_kg_m_s_inv':moisture_flux_convergence(specific_humidity=q,u=u,v=v,latitude=lat,longitude=lon),'omega700_pa_s':w,'rh850_percent':rh8,'rh500_percent':rh5,'t850_minus_t500_k':t8-t5,'precipitation_6h_raw':interp_precip(p,plat,plon,lat,lon)},lat,lon
def write_figure(event,records,out):
    specs=[('center_z500_gpm','Center Z500 (gpm)',1),('core_area_km2','Core area (10^6 km2)',1e-6),('zeta500_s_inv','Core zeta500 (10^-5 s^-1)',1e5),('mfc850_kg_kg_m_s_inv','850 hPa MFC (10^-7)',1e7),('omega700_pa_s','700 hPa omega (Pa s^-1)',1),('precipitation_6h_raw','6 h precipitation (raw unit)',1)]
    fig,axes=plt.subplots(3,2,figsize=(12,9),sharex=True,constrained_layout=True); x=np.arange(len(records))
    for ax,(key,label,scale) in zip(axes.ravel(),specs):
        y=np.array([float(r[key]) for r in records])*scale;ax.plot(x,y,'o-',ms=3,color='#2166ac');ax.axvline(next(i for i,r in enumerate(records) if r['phase']=='maturity'),color='#b2182b',ls='--');ax.set_ylabel(label,fontsize=8);ax.grid(alpha=.25)
    axes[-1,0].set_xticks(x[::max(1,len(x)//8)]);axes[-1,0].set_xticklabels([r['time_utc'][4:] for r in records][::max(1,len(x)//8)],rotation=40,ha='right',fontsize=8);axes[-1,1].set_xticks(axes[-1,0].get_xticks());axes[-1,1].set_xticklabels(axes[-1,0].get_xticklabels())
    fig.suptitle(f'{event}: core lifecycle (red dashed = Z500 minimum)',fontsize=11);fig.savefig(out/f'{event}_lifecycle_timeseries.png',dpi=180);plt.close(fig)
def write_md(event,records,out):
    maturity=next(r for r in records if r['phase']=='maturity'); first,last=records[0],records[-1]
    text=f'''# {event}：冷涡生命周期初步诊断\n\n- 时段：{first['time_utc']} 至 {last['time_utc']}（含末次识别后 6 h 消散诊断）。\n- 成熟期：{maturity['time_utc']}，以冷涡中心 500 hPa 位势高度最低定义（{float(maturity['center_z500_gpm']):.1f} gpm）。\n- 主体区：500 hPa 最外层 40 gpm 闭合等高线；短缺口按三级规则平移继承，连续长缺口使用固定小核心窗口。\n- 诊断量：主体区面积、Z500、500 hPa 相对涡度、850 hPa 水汽通量辐合、700 hPa 垂直速度、湿度与层结，以及同区 6 h 降水变量。降水原始单位尚未核验，表中保留为 raw unit。\n\n本文件为后续逐事件科学解释的量化材料，不将单一变量变化直接视作因果结论。\n'''
    (out/f'{event}_lifecycle_diagnosis.md').write_text(text,encoding='utf-8')
def run_package(package):
    reg=package/'regions'; rows=list(csv.DictReader((reg/'continuous_body_records.csv').open(encoding='utf-8',newline=''))); archive=np.load(reg/'continuous_body_masks.npz'); area=np.broadcast_to(_cell_area_km2(archive['latitude'],archive['longitude']),archive['core_body'][0].shape)
    byevent={};
    for row,mask in zip(rows,archive['core_body']):byevent.setdefault(row['event_id'],[]).append((row,mask))
    for event,pairs in byevent.items():
        records=phase_rows([dict(row) for row,_ in pairs]); out=package/'diagnostics'; tables=out/'tables'; figs=out/'figures'; analysis=package/'analysis';tables.mkdir(parents=True,exist_ok=True);figs.mkdir(parents=True,exist_ok=True);analysis.mkdir(parents=True,exist_ok=True)
        result=[]
        for row,(_,mask) in zip(records,pairs):
            fields,lat,lon=fieldset(row['time_utc']); summary=core_summary(core_mask=mask,cell_area_km2=area,fields=fields); center_z=fields['z500_gpm'][np.abs(lat-float(row['refined_center_latitude_deg_n'])).argmin(),np.abs(lon-float(row['refined_center_longitude_deg_e'])).argmin()]
            result.append({'event_id':event,**row,'center_z500_gpm':center_z,**summary})
        with (tables/f'{event}_lifecycle_diagnostics.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
        write_figure(event,result,figs);write_md(event,result,analysis);print(event,len(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);run_package(p.parse_args().package)
