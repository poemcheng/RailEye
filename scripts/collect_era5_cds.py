"""Optional authorized CDS four-layer adapter. Never print credentials or service errors.
No token => no network requests. This is a data collector, not the paper's ANN.
"""
from __future__ import annotations
import hashlib,json,os,signal,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collect_soil import REGIONS,DEPTHS,iso,stamp,moisture,save,validate_cds
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'.soil-cache/cds';UTC=timezone.utc
VARIABLES=[f'volumetric_soil_water_layer_{i}' for i in range(1,5)]
def decode(path,region,seen):
 import xarray as xr
 import pandas as pd
 with xr.open_dataset(path) as original:
  ds=original
  for dim in ['number','expver']:
   if dim in ds.dims:
    if ds.sizes[dim]!=1:raise ValueError('MULTI_VERSION_REQUIRES_EXPLICIT_RECONCILIATION')
    ds=ds.isel({dim:0})
  latname='latitude' if 'latitude' in ds.coords else 'lat';lonname='longitude' if 'longitude' in ds.coords else 'lon'
  ds=ds.sel({latname:region['lat'],lonname:region['lon']},method='nearest')
  lat=float(ds[latname]);lon=float(ds[lonname]);timekey='valid_time' if 'valid_time' in ds.coords else 'time'
  cols=[]
  for i in range(1,5):
   key=f'swvl{i}' if f'swvl{i}' in ds else VARIABLES[i-1]
   if key not in ds:raise ValueError('CDS_VARIABLE_MISSING')
   unit=str(ds[key].attrs.get('units','')).replace('**','').replace(' ','')
   if unit not in {'m3m-3','m3/m3'}:raise ValueError('CDS_UNITS')
   cols.append(ds[key].values.reshape(-1))
  times=ds[timekey].values.reshape(-1);rows=[]
  for n,t in enumerate(times):
   valid=pd.Timestamp(t).tz_localize('UTC').isoformat().replace('+00:00','Z')
   vals={f's{i+1}':moisture(float(col[n])) for i,col in enumerate(cols)}
   if all(v is None for v in vals.values()):continue
   rows.append({'valid_at':valid,'available_at':None,'first_seen_at':seen,'availability_basis':'collector_first_seen_not_provider_release','values':vals,'value_hash':hashlib.sha256(json.dumps(vals,sort_keys=True).encode()).hexdigest()})
 return {'grid':{'id':f'cds-era5-land:{lat:.4f}:{lon:.4f}','lat':lat,'lon':lon,'requested_lat':region['lat'],'requested_lon':region['lon'],'scope':'regional_grid_not_verified_slope'},'rows':rows}

def main():
 token=os.getenv('CDSAPI_KEY','').strip()
 if not token:
  print('CDS_SOIL requires_configuration (optional); no requests submitted');return
 if hasattr(signal,'SIGALRM'):
  signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('CDS_TIME_BUDGET')));signal.alarm(240)
 import cdsapi
 client=cdsapi.Client(url='https://cds.climate.copernicus.eu/api',key=token,quiet=True,debug=False,progress=False,timeout=25,retry_max=1)
 now=datetime.now(UTC);end=(now-timedelta(days=6)).date();start=end-timedelta(days=24);groups={}
 for i in range((end-start).days+1):
  d=start+timedelta(days=i);groups.setdefault((d.year,d.month),[]).append(f'{d.day:02d}')
 for r in REGIONS:
  target=DEST/(r['id']+'.json');old=None
  if target.exists():
   try:
    old=validate_cds(json.loads(target.read_text()))
    if 0<=(now-stamp(old['fetched_at'])).total_seconds()<20*3600:continue
   except (ValueError,KeyError):old=None
  try:
   rows=[];grid=None
   with tempfile.TemporaryDirectory() as td:
    for (year,month),days in groups.items():
     req={'variable':VARIABLES,'year':str(year),'month':f'{month:02d}','day':days,'time':[f'{h:02d}:00' for h in range(24)],'area':[r['lat']+.11,r['lon']-.11,r['lat']-.11,r['lon']+.11],'data_format':'netcdf','download_format':'unarchived'}
     path=Path(td)/f'{year}-{month}.nc';client.retrieve('reanalysis-era5-land',req,str(path));part=decode(path,r,iso());grid=part['grid'];rows.extend(part['rows'])
   prior={(x['valid_at'],x['value_hash']):x['first_seen_at'] for x in (old or {}).get('rows',[]) if (old or {}).get('grid',{}).get('id')==grid['id']}
   for row in rows:row['first_seen_at']=prior.get((row['valid_at'],row['value_hash']),row['first_seen_at'])
   out={'status':'ok','provider':'Copernicus CDS ERA5-Land','product':'reanalysis-era5-land','product_version':'CDS_returned_revision_not_resolved','direct_cds':True,'unit':'m3/m3','depths_cm':DEPTHS,'grid':grid,'rows':sorted(rows,key=lambda x:x['valid_at']),'fetched_at':iso(),'checked_at':iso(),'latest_valid_at':max(x['valid_at'] for x in rows),'layer4_status':'CDS_native_100_289cm','source_url':'https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land'}
   save(target,validate_cds(out));print('CDS_SOIL',r['id'],'ok',len(rows))
  except Exception as e:print('CDS_SOIL',r['id'],'unavailable',type(e).__name__)
 if hasattr(signal,'SIGALRM'):signal.alarm(0)
if __name__=='__main__':main()
