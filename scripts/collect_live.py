"""Public environmental collector. Never a railway control or validated hazard model.
Only approved public endpoints; optional CWA key stays in CI, never in outputs.
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib,json,math,os,time,traceback
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'live';CACHE=ROOT/'.live-cache';UTC=timezone.utc;TW=timezone(timedelta(hours=8))
REGIONS=[
 {'id':'northlink','name':'北迴・花蓮北部','lat':24.20,'lon':121.68,'counties':['花蓮縣'],'location_status':'regional_reference_not_asset'},
 {'id':'yilan','name':'宜蘭・蘇澳周邊','lat':24.60,'lon':121.80,'counties':['宜蘭縣'],'location_status':'regional_reference_not_asset'},
 {'id':'southlink','name':'南迴・太麻里周邊','lat':22.60,'lon':121.00,'counties':['臺東縣','屏東縣'],'location_status':'regional_reference_not_asset'},
 {'id':'neiwan','name':'內灣・新竹山區','lat':24.70,'lon':121.18,'counties':['新竹縣'],'location_status':'regional_reference_not_asset'}]
WATER='https://opendata.wra.gov.tw/api/v2/73c4c3de-4045-4765-abeb-89f9f9cd5ff0?format=JSON'
STATIONS='https://opendata.wra.gov.tw/api/v2/c4acc691-7416-40ca-9464-292c0c00da92?format=JSON'
ALERTS='https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=ofvJwoWC5wum'
UA='RailEye-Public-Research/0.4 (+https://github.com/poemcheng/RailEye)'
ALLOWED={'api.open-meteo.com','power.larc.nasa.gov','opendata.wra.gov.tw','data.moa.gov.tw','api.daac.asf.alaska.edu','opendata.cwa.gov.tw'}
def iso(d=None):return (d or datetime.now(UTC)).astimezone(UTC).isoformat(timespec='seconds').replace('+00:00','Z')
def parse_time(value,assume_taiwan=False):
 if not isinstance(value,str) or not value.strip():return None
 try:
  d=datetime.fromisoformat(value.strip().replace('/','-').replace('Z','+00:00'))
  if d.tzinfo is None:
   if not assume_taiwan:return None
   d=d.replace(tzinfo=TW)
  return d.astimezone(UTC)
 except ValueError:return None

def number(value):
 if value is None or isinstance(value,bool) or (isinstance(value,str) and not value.strip()):return None
 try:n=float(value)
 except (ValueError,TypeError):return None
 return n if math.isfinite(n) and n>-900 else None

def nonnegative(value):
 n=number(value)
 return n if n is not None and n>=0 else None

def distance(a,b,c,d):
 p,q=math.radians(a),math.radians(c)
 z=math.sin((q-p)/2)**2+math.cos(p)*math.cos(q)*math.sin(math.radians(d-b)/2)**2
 return 6371*2*math.asin(min(1,math.sqrt(z)))

def atomic_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
 tmp.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8');tmp.replace(path)

def fetch_json(url,cache_hours=0):
 if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in ALLOWED:raise ValueError('URL_NOT_ALLOWED')
 p=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
 if cache_hours and p.exists():
  try:
   old=json.loads(p.read_text());age=(datetime.now(UTC)-parse_time(old['fetched_at'])).total_seconds()/3600
   if 0<=age<cache_hours:return old['data'],old['fetched_at'],True
  except (ValueError,KeyError,TypeError):pass
 for attempt in range(2):
  try:
   with urlopen(Request(url,headers={'User-Agent':UA,'Accept':'application/json','Cache-Control':'no-cache'}),timeout=35) as r:raw=r.read(12_000_001)
   if len(raw)>12_000_000:raise ValueError('RESPONSE_TOO_LARGE')
   obj=json.loads(raw.decode('utf-8-sig'));stamp=iso()
   if cache_hours:atomic_json(p,{'fetched_at':stamp,'data':obj})
   return obj,stamp,False
  except Exception:
   if attempt:raise
   time.sleep(1)
 raise RuntimeError('UNREACHABLE')

def envelope(name,url,kind,ttl,fn):
 started=iso()
 try:
  data,stamp,cached=fn()
  return {'status':'ok','source':name,'source_url':url,'kind':kind,'fetched_at':stamp,'attempted_at':started,'ttl_seconds':ttl,'cached':cached,'data':data}
 except Exception as e:
  # Only exception class/status/function location; never messages, locals or token URLs.
  tb=traceback.extract_tb(e.__traceback__)
  return {'status':'unavailable','source':name,'source_url':url.split('?Authorization')[0],'kind':kind,'fetched_at':None,'attempted_at':started,'ttl_seconds':ttl,'error':type(e).__name__,'error_http_status':getattr(e,'code',None),'error_location':f'{tb[-1].name}:{tb[-1].lineno}' if tb else None,'data':None}

def weather(region):
 params={'latitude':region['lat'],'longitude':region['lon'],'current':'temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m','hourly':'temperature_2m,precipitation,precipitation_probability,soil_moisture_0_to_1cm','past_days':3,'forecast_days':4,'timezone':'UTC','timeformat':'unixtime','wind_speed_unit':'ms'}
 url='https://api.open-meteo.com/v1/forecast?'+urlencode(params)
 def run():
  d,t,c=fetch_json(url)
  if not isinstance(d,dict) or not isinstance(d.get('hourly',{}).get('time'),list):raise ValueError('WEATHER_SCHEMA')
  return {**d,'measurement_type':'numerical_weather_model_not_station_observation','model_issue_time':None},t,c
 return envelope('Open-Meteo 天氣模式',url,'model_forecast',10800,run)

def climate(region):
 url='https://power.larc.nasa.gov/api/temporal/climatology/point?'+urlencode({'parameters':'T2M,PRECTOTCORR','community':'AG','latitude':region['lat'],'longitude':region['lon'],'format':'JSON'})
 def run():
  d,t,c=fetch_json(url,24*30)
  if not isinstance(d,dict) or not isinstance(d.get('properties',{}).get('parameter'),dict):raise ValueError('CLIMATE_SCHEMA')
  keep={k:d.get(k) for k in ['geometry','header','parameters','messages']};keep['monthly']=d['properties']['parameter']
  # Normalized period fields preserve the original authoritative range text.
  keep['header']=dict(keep.get('header') or {})
  if keep['header'].get('range') and not keep['header'].get('start'):keep['header']['start']=keep['header']['range'];keep['header']['end']='原來源統計期間'
  return keep,t,c
 return envelope('NASA POWER 氣候背景',url,'climatology_not_live_weather',86400*35,run)

def satellite(region):
 now=datetime.now(UTC)
 url='https://api.daac.asf.alaska.edu/services/search/param?'+urlencode({'dataset':'SENTINEL-1','processingLevel':'SLC','beamMode':'IW','intersectsWith':f"POINT({region['lon']} {region['lat']})",'start':iso(now-timedelta(days=45)),'end':iso(now),'maxResults':60,'output':'geojson'})
 def run():
  d,t,c=fetch_json(url)
  if not isinstance(d,dict) or d.get('type')!='FeatureCollection' or not isinstance(d.get('features'),list):raise ValueError('ASF_SCHEMA')
  rows=[]
  for f in d['features']:
   p=f.get('properties') or {};dt=parse_time(p.get('startTime'))
   if not dt or dt>now+timedelta(minutes=5):continue
   browse=p.get('browse') or []
   if isinstance(browse,str):browse=[browse]
   if not isinstance(browse,list):browse=[]
   preview=next((x for x in browse if isinstance(x,str) and x.startswith('https://')),None)
   rows.append({'scene_id':p.get('sceneName') or p.get('fileID'),'acquired_at':iso(dt),'relative_orbit':p.get('pathNumber') or p.get('relativeOrbit'),'frame':p.get('frameNumber'),'flight_direction':p.get('flightDirection'),'polarization':p.get('polarization'),'platform':p.get('platform'),'browse_url':preview,'geometry':f.get('geometry'),'product':'IW SLC catalog','insar_displacement':None})
  rows.sort(key=lambda x:x['acquired_at'],reverse=True)
  return {'scenes':rows[:20],'returned_count':len(rows),'query_limit':60,'possibly_truncated':len(d['features'])>=60,'coverage':'reference_point_intersection_not_verified_slope_coverage','latest_acquired_at':rows[0]['acquired_at'] if rows else None},t,c
 return envelope('NASA ASF Sentinel-1 SLC',url,'satellite_catalog_not_insar',86400,run)

def extract_list(d):
 if isinstance(d,list):return d
 if isinstance(d,dict):
  for k in ['data','Data','records','result']:
   if isinstance(d.get(k),list):return d[k]
 raise ValueError('EXPECTED_ARRAY')

def water_observations():
 def run():
  raw,t,c=fetch_json(WATER);rows=extract_list(raw);out=[]
  for x in rows:
   tm=parse_time(x.get('datetime'),True);value=number(x.get('waterlevel'))
   if not x.get('stationid'):continue
   qc=str(x.get('checkresult','')).lower()
   out.append({'station_id':x['stationid'],'observed_at':iso(tm) if tm else None,'level_m':value,'source_check':qc,'quality':'source_check_passed_unreviewed' if qc=='true' and value is not None and tm else 'needs_review','source_description':x.get('checkdesc'),'datum':'source_station_datum_not_cross_station_comparable'})
  if rows and not out:raise ValueError('WATER_SCHEMA')
  return out,t,c
 return envelope('經濟部水利署即時水位',WATER,'station_observation_unreviewed',5400,run)

def station_metadata():
 def run():
  from pyproj import Transformer
  transform=Transformer.from_crs('EPSG:3826','EPSG:4326',always_xy=True);raw,t,c=fetch_json(STATIONS,24);out=[]
  for r in extract_list(raw):
   if r.get('observationstatus')!='現存':continue
   xy=str(r.get('locationbytwd97_xy','')).replace(',',' ').split();lon=lat=None
   if len(xy)==2:
    try:
     lon,lat=transform.transform(float(xy[0]),float(xy[1]))
     if not (118<=lon<=123 and 20<=lat<=27):lon=lat=None
    except ValueError:pass
   out.append({'station_id':r.get('basinidentifier'),'name':r.get('observatoryname'),'river':r.get('rivername'),'basin':r.get('affiliatedbasin'),'address':r.get('locationaddress'),'lat':lat,'lon':lon,'coordinates_source':'WRA locationbytwd97_xy; EPSG:3826 to 4326','geometry_role':'public_gauge_not_railway_asset'})
  if not out:raise ValueError('STATION_SCHEMA')
  return out,t,c
 return envelope('水利署現存水位站資料',STATIONS,'station_metadata',172800,run)

def slope_alerts():
 def run():
  raw,t,c=fetch_json(ALERTS);rows=extract_list(raw);out=[]
  for x in rows:
   if not isinstance(x,dict) or x.get('AlertType') not in {'D','L'} or str(x.get('AlertLevel','')).lower() not in {'y','r'}:continue
   out.append({k:x.get(k) for k in ['AlertType','DebrisNo','LandslideID','LandslideName','County','Town','Vill','AlertLevel','LastUpdateDate']})
  if rows and not out and not all(isinstance(x,dict) and x.get('LandslideName')=='目前無警戒' and x.get('AlertLevel')=='-' for x in rows):raise ValueError('ALERT_SCHEMA')
  return {'alerts':out,'count':len(out),'empty_meaning':'source_returned_no_records_not_proof_of_no_hazard','official_issue_time':max((x.get('LastUpdateDate') or '' for x in out),default=None)},t,c
 return envelope('農村水保署土石流／崩塌警戒',ALERTS,'official_alert',5400,run)

def cwa_rainfall():
 base='https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001';token=os.getenv('CWA_API_KEY','').strip()
 if not token:return {'status':'requires_configuration','source':'中央氣象署雨量測站','source_url':base,'kind':'station_observation','fetched_at':None,'attempted_at':iso(),'ttl_seconds':3600,'data':None,'error':'CWA_API_KEY_NOT_CONFIGURED'}
 def run():
  d,t,c=fetch_json(base+'?'+urlencode({'Authorization':token,'format':'JSON'}));raw=d.get('records',{}).get('Station')
  if not isinstance(raw,list):raise ValueError('CWA_SCHEMA')
  out=[]
  for x in raw:
   geo=x.get('GeoInfo',{});co=next((g for g in geo.get('Coordinates',[]) if g.get('CoordinateName')=='WGS84'),{})
   rain=x.get('RainfallElement',{});tm=parse_time(x.get('ObsTime',{}).get('DateTime'))
   out.append({'station_id':x.get('StationId'),'name':x.get('StationName'),'county':geo.get('CountyName'),'lat':number(co.get('StationLatitude')),'lon':number(co.get('StationLongitude')),'observed_at':iso(tm) if tm else None,'rain_1h':nonnegative(rain.get('Past1hr',{}).get('Precipitation')),'rain_24h':nonnegative(rain.get('Past24hr',{}).get('Precipitation'))})
  return out,t,c
 return envelope('中央氣象署雨量測站',base,'station_observation_unreviewed',3600,run)

def main():
 jobs={'water':water_observations,'stations':station_metadata,'alerts':slope_alerts,'cwa_rainfall':cwa_rainfall}
 for r in REGIONS:
  for k,fn in [('weather',weather),('satellite',satellite),('climate',climate)]:jobs[f"{k}:{r['id']}"]=lambda r=r,fn=fn:fn(r)
 results={}
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  future={pool.submit(fn):key for key,fn in jobs.items()}
  for f in cf.as_completed(future):
   key=future[f]
   try:results[key]=f.result()
   except Exception as e:results[key]={'status':'unavailable','error':type(e).__name__,'fetched_at':None,'data':None,'attempted_at':iso()}
   print(key,results[key]['status'],results[key].get('error_location',''),flush=True)
 global_data={k:results[k] for k in ['water','stations','alerts','cwa_rainfall']};regions=[]
 stations={s['station_id']:s for s in (results['stations'].get('data') or [])};observations=[]
 for w in results['water'].get('data') or []:observations.append({**stations.get(w['station_id'],{}),**w})
 for r in REGIONS:
  nearest=[{**w,'distance_km':round(distance(r['lat'],r['lon'],w['lat'],w['lon']),1),'association':'geographic_proximity_only_not_hydrological_connection'} for w in observations if w.get('lat') is not None and w.get('lon') is not None]
  nearest=sorted((w for w in nearest if w['distance_km']<=60),key=lambda w:w['distance_km'])[:8]
  regions.append({**r,**{k:results[f"{k}:{r['id']}"] for k in ['weather','satellite','climate']},'nearby_water':nearest})
 summary={'schema_version':'1.0','app_version':'0.4.0','generated_at':iso(),'regions':regions,'sources':global_data,
  'source_status':{k:{'status':v['status'],'fetched_at':v.get('fetched_at'),'error':v.get('error'),'error_location':v.get('error_location'),'error_http_status':v.get('error_http_status')} for k,v in results.items()},
  'slope_prediction':{'status':'not_validated','probability':None,'reason':'No verified asset geometry, independent hazard labels or calibrated slope model'},
  'schedule_note':'GitHub Actions every 30 min, best effort; browser checks published snapshot every 5 min; not a guaranteed real-time safety channel'}
 for k in ['water','stations']:
  src=summary['sources'][k];src['record_count']=len(src.get('data') or []);src.pop('data',None)
 atomic_json(OUT/'latest.json',summary)
 health={'generated_at':summary['generated_at'],'sources':summary['source_status'],'regions':{r['id']:{'water_stations':len(r['nearby_water']),'satellite_scenes':len((r['satellite'].get('data') or {}).get('scenes',[]))} for r in regions}}
 atomic_json(OUT/'health.json',health)
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## RailEye public data refresh\n\n'+json.dumps(health,ensure_ascii=False,indent=2)+'\n\nNo slope probability computed.\n')
 print(json.dumps(health,ensure_ascii=False),flush=True)
 for r in regions:
  w=(r['weather'].get('data') or {}).get('current',{});sc=(r['satellite'].get('data') or {}).get('scenes',[])
  print('PUBLIC_SAMPLE',json.dumps({'region':r['id'],'weather':w,'water':r['nearby_water'][:1],'satellite':[{k:s.get(k) for k in ['scene_id','acquired_at','platform','relative_orbit','browse_url']} for s in sc[:1]],'climate_header':(r['climate'].get('data') or {}).get('header')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
