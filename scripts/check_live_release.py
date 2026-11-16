"""Read-only post-deploy check against the public HTTPS site. No credentials."""
import json,os,time
from urllib.request import Request,urlopen
BASE='https://poemcheng.github.io/RailEye/'
expected=os.environ.get('GITHUB_SHA')
for attempt in range(10):
 try:
  suffix='?release_check='+str(int(time.time()))
  def read(path):
   with urlopen(Request(BASE+path+suffix,headers={'User-Agent':'RailEye-Release-Verification/0.4','Cache-Control':'no-cache'}),timeout=15) as r:
    if r.status!=200:raise ValueError('HTTP_STATUS')
    return r.read(2_000_000).decode('utf-8')
  build=json.loads(read('build-info.json'))
  if expected and build.get('commit')!=expected:raise ValueError('CDN_OLD_BUILD')
  html=read('index.html')
  if 'live.js?v=0.4.0' not in html:raise ValueError('LIVE_MODULE_NOT_FOUND')
  data=json.loads(read('data/live/latest.json'))
  if data.get('schema_version')!='1.0' or len(data.get('regions',[]))!=4:raise ValueError('SNAPSHOT_SCHEMA')
  print('PUBLIC_HTTPS_ACCEPTANCE',json.dumps({'url':BASE,'http_status':200,'commit':build['commit'],'snapshot_at':data['generated_at'],'source_status':data['source_status'],'scope':'HTTP, deployed source and real snapshot; not interactive browser'},ensure_ascii=False))
  break
 except Exception as e:
  if attempt==9:raise
  print('Retry CDN acceptance:',type(e).__name__);time.sleep(6)
