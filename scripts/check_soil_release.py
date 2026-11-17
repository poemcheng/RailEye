"""Read-only public HTTPS acceptance; verify content and record actual source availability."""
import json,os,time
from urllib.request import Request,urlopen
BASE='https://poemcheng.github.io/RailEye/'
for attempt in range(8):
 try:
  def read(path):
   with urlopen(Request(BASE+path+'?soil_release_check='+str(int(time.time())),headers={'Cache-Control':'no-cache','User-Agent':'RailEye-Acceptance/0.5'}),timeout=20) as r:
    if r.status!=200:raise ValueError('HTTP_STATUS')
    return r.read(6_000_000).decode('utf-8')
  build=json.loads(read('build-info.json'))
  if build.get('commit')!=os.environ.get('GITHUB_SHA') or build.get('version')!='0.5.0':raise ValueError('OLD_DEPLOYMENT')
  if 'hydro-ui.js?v=0.5.0' not in read('index.html'):raise ValueError('HYDRO_MODULE_MISSING')
  read('hydro-core.js');read('hydro-ui.js');data=json.loads(read('data/soil/latest.json'))
  if data.get('schema_version')!='soil-1.0' or len(data.get('regions',[]))!=4:raise ValueError('SOIL_SCHEMA')
  summary=[]
  for r in data['regions']:
   s=r['soil'];rows=s.get('rows',[]);last=rows[-1] if rows else None
   if any(x.get('values',{}).get('s4') is not None for x in rows) and not s.get('direct_cds'):raise ValueError('LAYER4_MISREPRESENTED')
   if r.get('local_model',{}).get('slope_probability') is not None:raise ValueError('UNVALIDATED_PREDICTION')
   summary.append({'region':r['id'],'status':s['status'],'provider':s.get('provider'),'rows':len(rows),'latest_valid_at':s.get('latest_valid_at'),'last_values':last.get('values') if last else None,'layer4_status':s.get('layer4_status')})
  print('SOIL_HTTPS_ACCEPTANCE',json.dumps({'commit':build['commit'],'snapshot_at':data['generated_at'],'regions':summary,'scope':'HTTP/source/data; not browser or hazard validation'},ensure_ascii=False));break
 except Exception as e:
  if attempt==7:raise
  print('Retry soil release:',type(e).__name__);time.sleep(6)
