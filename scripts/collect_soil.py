"""Public ERA5-Land context. Preserve missing layers, version hashes and first-seen times.
Open-Meteo explicitly selects era5_land. Layer 4 is NOT silently remapped from 100-255 cm.
Optional normalized CDS input is produced by collect_era5_cds.py. No hazard inference.
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib,json,math,os,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/soil';CACHE=ROOT/'.soil-cache';UTC=timezone.utc
VARS=['soil_moisture_0_to_7cm','soil_moisture_7_to_28cm','soil_moisture_28_to_100cm']
DEPTHS=[[0,7],[7,28],[28,100],[100,289]]
REGIONS=[{'id':'northlink','name':'北迴・花蓮北部','lat':24.20,'lon':121.68},{'id':'yilan','name':'宜蘭・蘇澳','lat':24.60,'lon':121.80},{'id':'southlink','name':'南迴・太麻里','lat':22.60,'lon':121.00},{'id':'neiwan','name':'內灣・新竹山區','lat':24.70,'lon':121.18}]
def iso(d=None):return (d or datetime.now(UTC)).isoformat(timespec='seconds').replace('+00:00','Z')
def stamp(v):
 if not isinstance(v,str):raise ValueError('TIME_TYPE')
 d=datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return d.astimezone(UTC)
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def moisture(v):return float(v) if finite(v) and 0<=v<=1 else None
def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8');tmp.replace(path)
def request(url):
 for n in range(2):
  try:
   with urlopen(Request(url,headers={'User-Agent':'RailEye-Research/0.5','Accept':'application/json'}),timeout=35) as r:raw=r.read(6_000_001)
   if len(raw)>6_000_000:raise ValueError('RESPONSE_TOO_LARGE')
   return json.loads(raw)
  except Exception:
   if n:raise
   time.sleep(1)

def grid_distance_km(lat,lon,ref):
 a,b=math.radians(lat),math.radians(ref['lat'])
 x=math.sin((a-b)/2)**2+math.cos(a)*math.cos(b)*math.sin(math.radians(lon-ref['lon'])/2)**2
 return 6371*2*math.asin(min(1,math.sqrt(x)))

def normalize_openmeteo(d,region,seen,old=None):
 h=d.get('hourly',{});times=h.get('time');units=d.get('hourly_units',{})
 if not isinstance(times,list) or not times:raise ValueError('SOIL_SCHEMA')
 if not all(isinstance(h.get(v),list) and len(h[v])==len(times) for v in VARS):raise ValueError('SOIL_LENGTH')
 if not all(str(units.get(v)).replace('³','3') in {'m3/m3','m³/m³'} for v in VARS):raise ValueError('SOIL_UNITS')
 lat,lon=d.get('latitude'),d.get('longitude')
 if not finite(lat) or not finite(lon) or not 20<lat<27 or not 118<lon<124:raise ValueError('GRID_INVALID')
 grid={'id':f'era5_land:{lat:.4f}:{lon:.4f}','lat':lat,'lon':lon,'requested_lat':region['lat'],'requested_lon':region['lon'],'scope':'regional_grid_not_verified_slope','selection':'land_preference_not_exact_asset','offset_km':round(grid_distance_km(lat,lon,region),3)}
 prior={(r['valid_at'],r['value_hash']):r['first_seen_at'] for r in (old or {}).get('rows',[]) if (old or {}).get('grid',{}).get('id')==grid['id']}
 rows=[];unique=set();observed=stamp(seen)
 for i,t in enumerate(times):
  if not finite(t):raise ValueError('BAD_TIME')
  dt=datetime.fromtimestamp(t,UTC)
  if t in unique:raise ValueError('DUPLICATE_SOIL_TIME')
  unique.add(t)
  if dt>observed:raise ValueError('FUTURE_SOIL')
  vals={f's{j+1}':moisture(h[v][i]) for j,v in enumerate(VARS)};vals['s4']=None
  if all(vals[k] is None for k in ('s1','s2','s3')):continue
  digest=hashlib.sha256(json.dumps(vals,sort_keys=True).encode()).hexdigest();valid=iso(dt)
  rows.append({'valid_at':valid,'available_at':None,'first_seen_at':prior.get((valid,digest),seen),'availability_basis':'collector_first_seen_not_provider_release','values':vals,'value_hash':digest})
 if not rows:raise ValueError('NO_VALID_SOIL_ROWS')
 return {'status':'ok','provider':'ERA5-Land via Open-Meteo','product':'era5_land','product_version':'provider_revision_unspecified','unit':'m3/m3','grid':grid,'depths_cm':DEPTHS,'rows':sorted(rows,key=lambda r:r['valid_at']),'fetched_at':seen,'latest_valid_at':max(r['valid_at'] for r in rows),'layer4_status':'withheld_provider_depth_label_100_255_vs_CDS_100_289','source_docs':'https://open-meteo.com/en/docs/historical-weather-api','cds_docs':'https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land','direct_cds':False}

def collect(region):
 p=CACHE/(region['id']+'.json');old=None
 if p.exists():
  try:old=json.loads(p.read_text(encoding='utf-8'))
  except (ValueError,OSError):pass
 if old:
  try:
   age=(datetime.now(UTC)-stamp(old['fetched_at'])).total_seconds()
   if 0<=age<20*3600 and old.get('grid',{}).get('selection')=='land_preference_not_exact_asset':return {**old,'cache_reused':True,'checked_at':iso()}
  except (ValueError,KeyError):pass
 now=datetime.now(UTC);end=(now-timedelta(days=5)).date();start=end-timedelta(days=30)
 url='https://archive-api.open-meteo.com/v1/archive?'+urlencode({'latitude':region['lat'],'longitude':region['lon'],'start_date':str(start),'end_date':str(end),'hourly':','.join(VARS),'models':'era5_land','timezone':'UTC','timeformat':'unixtime','cell_selection':'land','elevation':'nan'})
 try:
  d=request(url);seen=iso();data=normalize_openmeteo(d,region,seen,old);data.update(source_url=url,cache_reused=False,checked_at=seen)
  save(p,data);return data
 except Exception as e:
  known={'SOIL_SCHEMA','SOIL_LENGTH','SOIL_UNITS','GRID_INVALID','BAD_TIME','DUPLICATE_SOIL_TIME','FUTURE_SOIL','NO_VALID_SOIL_ROWS','RESPONSE_TOO_LARGE'}
  reason=str(e) if isinstance(e,ValueError) and str(e) in known else type(e).__name__
  if old:return {**old,'status':'stale','checked_at':iso(),'error':reason,'cache_reused':True}
  return {'status':'unavailable','provider':'ERA5-Land via Open-Meteo','source_url':url,'checked_at':iso(),'fetched_at':None,'error':reason,'rows':[],'depths_cm':DEPTHS,'layer4_status':'withheld_depth_mismatch','unit':'m3/m3'}

def validate_cds(d):
 if d.get('product')!='reanalysis-era5-land' or d.get('unit')!='m3/m3' or d.get('depths_cm')!=DEPTHS:raise ValueError('CDS_CONTRACT')
 if not d.get('direct_cds') or not d.get('grid',{}).get('id'):raise ValueError('CDS_PROVENANCE')
 if not d.get('rows'):raise ValueError('CDS_EMPTY')
 for r in d['rows']:
  v=stamp(r['valid_at']);s=stamp(r['first_seen_at'])
  if s<v:raise ValueError('AVAILABILITY_BEFORE_VALID')
  for k in ('s1','s2','s3','s4'):
   x=r['values'].get(k)
   if x is not None and moisture(x) is None:raise ValueError('CDS_RANGE')
 return d

def main():
 latest=json.loads((ROOT/'data/live/latest.json').read_text(encoding='utf-8')); live={r['id']:r for r in latest['regions']}
 with cf.ThreadPoolExecutor(max_workers=2) as pool:soil=list(pool.map(collect,REGIONS))
 direct_dir=os.getenv('RAILEYE_CDS_NORMALIZED_DIR','');regions=[]
 for r,s in zip(REGIONS,soil):
  if direct_dir:
   p=Path(direct_dir)/(r['id']+'.json')
   if p.exists():
    try:
     candidate=validate_cds(json.loads(p.read_text()))
     age=(datetime.now(UTC)-stamp(candidate['fetched_at'])).total_seconds()
     if 0<=age<=36*3600:s=candidate
    except (ValueError,KeyError,TypeError):s={**s,'direct_cds_import_status':'rejected_invalid_contract'}
  w=live.get(r['id'],{}).get('weather',{});h=(w.get('data') or {}).get('hourly') or {};rain=[]
  for i,t in enumerate(h.get('time',[])):
   values=h.get('precipitation',[]);x=values[i] if i<len(values) else None
   rain.append({'t':t*1000,'rain':float(x) if finite(x) and x>=0 else None,'available_at':w.get('fetched_at')})
  regions.append({**r,'soil':s,'rain':{'status':w.get('status','missing'),'kind':'weather_model_estimate_not_station_observation','source':w.get('source'),'fetched_at':w.get('fetched_at'),'ttl_seconds':10800,'rows':rain},'local_model':{'status':'not_trained','slope_probability':None}})
  print('SOIL_RESULT',r['id'],s['status'],len(s.get('rows',[])),s.get('latest_valid_at'),s.get('error'),flush=True)
 obj={'schema_version':'soil-1.0','generated_at':iso(),'regions':regions,'doi':'10.5194/nhess-25-4907-2025','method':'lagged_features_not_paper_model_replication','direct_cds_status':'requires_authorized_CDS_download_or_normalized_import','retrospective_availability':'not_reconstructed; first-seen preserved only for cached identical grid/value versions','source_attribution':'Copernicus Climate Change Service ERA5-Land distributed via Open-Meteo (CC BY 4.0); confirm service terms for commercial use'}
 save(OUT/'latest.json',obj)
 archive=ROOT/'evidence-archive';archive.mkdir(exist_ok=True)
 save(archive/'soil-snapshot.json',obj);save(archive/'environment-snapshot.json',latest)
 save(archive/'manifest.json',{'created_at':iso(),'commit':os.getenv('GITHUB_SHA'),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.glob('*snapshot.json')},'retention':'GitHub artifact 30 days; not an immutable long-term database'})
if __name__=='__main__':main()
