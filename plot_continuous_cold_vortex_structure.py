"""Render separate continuous MFC and 700-hPa omega structure sequences."""
from __future__ import annotations
import argparse,csv
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np
from cold_vortex_common_data import read_level
from cold_vortex_diagnostics import moisture_flux_convergence

def fields(time):
 z,lat,lon=read_level('GPH',time,500);u,_,_=read_level('WIU',time,850);v,_,_=read_level('WIV',time,850);q,_,_=read_level('SHU',time,850);w,_,_=read_level('VVP',time,700)
 return z,moisture_flux_convergence(specific_humidity=q,u=u,v=v,latitude=lat,longitude=lon),w,lat,lon
def draw(package,kind):
 reg=package/'regions';rows=list(csv.DictReader((reg/'continuous_body_records.csv').open(encoding='utf-8',newline='')));arc=np.load(reg/'continuous_body_masks.npz');groups={}
 for row,mask in zip(rows,arc['core_body']):groups.setdefault(row['event_id'],[]).append((row,mask))
 out=package/'diagnostics'/'figures';out.mkdir(parents=True,exist_ok=True)
 for event,pairs in groups.items():
  for page,start in enumerate(range(0,len(pairs),6),1):
   subset=pairs[start:start+6];fig,axes=plt.subplots(3,2,figsize=(12,13),constrained_layout=True)
   for ax,(row,mask) in zip(axes.ravel(),subset):
    z,mfc,w,lat,lon=fields(row['time_utc']);data=mfc*1e7 if kind=='mfc' else w;lim=np.nanpercentile(np.abs(data),98);cmap='BrBG' if kind=='mfc' else 'PuOr_r';label='850 hPa MFC (10$^{-7}$ kg kg$^{-1}$ m$^{-1}$ s$^{-1}$)' if kind=='mfc' else '700 hPa omega (Pa s$^{-1}$)'
    im=ax.contourf(lon,lat,data,levels=np.linspace(-lim,lim,17),cmap=cmap,extend='both');ax.contour(lon,lat,z,colors='black',linewidths=.45,levels=np.arange(np.floor(np.nanmin(z)/40)*40,np.ceil(np.nanmax(z)/40)*40+40,40));ax.contour(lon,lat,mask,levels=[.5],colors='#d7301f',linewidths=1.8);ax.plot(float(row['refined_center_longitude_deg_e']),float(row['refined_center_latitude_deg_n']),'+',color='black',ms=9,mew=1.5);ax.set(xlim=(70,165),ylim=(15,80),xlabel='Longitude (E)',ylabel='Latitude (N)');ax.set_title(f"{row['time_utc']} | {row['region_method']}",fontsize=8);fig.colorbar(im,ax=ax,shrink=.78,label=label)
   for ax in axes.ravel()[len(subset):]:ax.axis('off')
   title='850 hPa moisture-flux convergence' if kind=='mfc' else '700 hPa omega (negative = ascent)';fig.suptitle(f'{event}: continuous 6-hour {title}; red: core; black: Z500',fontsize=11);fig.savefig(out/f'{event}_continuous_{kind}_page_{page:02d}.png',dpi=180);plt.close(fig)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--kind',choices=('mfc','omega'),required=True);draw(p.parse_args().package,p.parse_args().kind)
