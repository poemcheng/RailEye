/* Pure, testable environmental calculations. Never a slope hazard probability. */
(function(root){'use strict';
const H=3600000;
function finite(x){return typeof x==='number'&&Number.isFinite(x);}
function ageSeconds(t,now=Date.now()){const v=Date.parse(t||'');return Number.isFinite(v)?(now-v)/1000:null;}
function sourceState(s,now=Date.now()){
 if(!s)return 'missing';if(s.status!=='ok')return s.status||'unavailable';
 const a=ageSeconds(s.fetched_at,now);if(a===null||a< -300)return 'invalid_time';
 return a>(s.ttl_seconds||3600)?'stale':'ok';
}
function series(data){
 const h=data?.hourly;if(!h||!Array.isArray(h.time))return [];
 return h.time.map((t,i)=>({t:Number(t)*1000,rain:finite(h.precipitation?.[i])&&h.precipitation[i]>=0?h.precipitation[i]:null,
  temp:finite(h.temperature_2m?.[i])?h.temperature_2m[i]:null,
  prob:finite(h.precipitation_probability?.[i])&&h.precipitation_probability[i]>=0&&h.precipitation_probability[i]<=100?h.precipitation_probability[i]:null,
  moisture:finite(h.soil_moisture_0_to_1cm?.[i])?h.soil_moisture_0_to_1cm[i]:null})).filter(r=>Number.isFinite(r.t)).sort((a,b)=>a.t-b.t);
}
function windowRain(rows,start,end){
 const n=Math.round((end-start)/H);const found=rows.filter(r=>r.t>start&&r.t<=end);
 const unique=new Map();let duplicate=false;for(const r of found){if(unique.has(r.t))duplicate=true;unique.set(r.t,r);}
 const expected=Array.from({length:n},(_,i)=>start+(i+1)*H);
 const valid=expected.filter(t=>unique.has(t)&&finite(unique.get(t).rain));
 return {start,end,expected:n,valid:valid.length,total:valid.length===n&&!duplicate&&n>0?valid.reduce((a,t)=>a+unique.get(t).rain,0):null};
}
function weatherSummary(src,now=Date.now()){
 const rows=series(src?.data),pastEnd=Math.floor(now/H)*H,futureStart=Math.ceil(now/H)*H;
 const current=src?.data?.current||{}, validCurrent=finite(current.time)?Math.abs(now-current.time*1000)<3*H:false;
 const fresh=sourceState(src,now)==='ok'&&validCurrent;
 const past24=windowRain(rows,pastEnd-24*H,pastEnd),future24=windowRain(rows,futureStart,futureStart+24*H),future72=windowRain(rows,futureStart,futureStart+72*H);
 const future=rows.filter(r=>r.t>futureStart&&r.t<=futureStart+72*H);
 const peak=future.filter(r=>finite(r.rain)).reduce((a,r)=>!a||r.rain>a.rain?r:a,null);
 const probs=rows.filter(r=>r.t>futureStart&&r.t<=futureStart+24*H&&finite(r.prob)).map(r=>r.prob);
 return {fresh,rows,current,pastEnd,futureStart,past24,future24,future72,future,peak,maxHourlyProbability:probs.length===24?Math.max(...probs):null,slope_probability:null};
}
function gaugeState(row,now=Date.now()){
 const age=ageSeconds(row.observed_at,now);
 if(!finite(row.level_m)||row.quality!=='source_check_passed_unreviewed')return 'needs_review';
 if(age===null||age< -300)return 'invalid_time';
 return age>5400?'stale':'ok';
}
function normalizedCounty(s){return String(s||'').replaceAll('台','臺');}
function regionAlerts(src,region){return (src?.data?.alerts||[]).filter(x=>(region.counties||[]).map(normalizedCounty).includes(normalizedCounty(x.County)));}
function advisory(weather,alerts,alertSource,now=Date.now()){
 if(sourceState(alertSource,now)==='ok'&&alerts.length)return {title:'區域內有官方警戒紀錄',text:'請查閱原發布單位及核定程序。縣市相符不代表該坡體位於警戒影響範圍。'};
 if(!weather.fresh||weather.future24.total===null)return {title:'資料不足或已過期，暫不推估',text:'不以缺測、零筆警戒或舊快照推論安全；請核對來源時間與必要證據。'};
 return {title:'已載入環境預報；坡體危害仍待驗證',text:'降雨預報可支援工程師安排資料覆核。尚缺核定坡體幾何、獨立危害真值及校準模型，不提供崩塌機率或 A–D 自動調整。'};
}
const api={H,finite,ageSeconds,sourceState,series,windowRain,weatherSummary,gaugeState,normalizedCounty,regionAlerts,advisory};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RailEyeLiveCore=api;
})(typeof window==='undefined'?globalThis:window);
