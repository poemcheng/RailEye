/* RailEye: delayed soil + causal rainfall-event features. NOT CTRL-T or a hazard model. */
(function(root){'use strict';
const H=3600000,DAY=24*H,DOI='10.5194/nhess-25-4907-2025';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
function instant(v){if(typeof v==='number')return finite(v)?v:null;if(typeof v!=='string'||!/(Z|[+-]\d\d:\d\d)$/i.test(v))return null;const t=Date.parse(v);return finite(t)?t:null;}
const iso=t=>new Date(t).toISOString();
/* Each rain row is a preceding-hour sum ending at t. A missing hour breaks the event. */
function segmentRain(input,{asOf=Date.now(),dryHours=24,wetThreshold=0.2}={}){
 if(!Number.isInteger(dryHours)||dryHours<1||dryHours>168||!finite(wetThreshold)||wetThreshold<=0)throw Error('INVALID_EVENT_PARAMETERS');
 const rows=input.map(r=>({...r,t:instant(r.t),available:instant(r.available_at)})).filter(r=>r.t!==null&&r.t<=asOf).sort((a,b)=>a.t-b.t);
 const seen=new Set();for(const r of rows){if(seen.has(r.t))throw Error('DUPLICATE_RAIN_TIME');seen.add(r.t);}
 const out=[];let active=null,dryBefore=0,last=null,pending=0,trailing=0;
 const close=state=>{if(!active)return;active.status=state;active.right_censored=state!=='closed';active.trailing_dry_hours=trailing;active.duration_hours=(active.last_wet_end-active.start)/H;active.start_at=iso(active.start);active.last_wet_at=iso(active.last_wet_end);active.label=null;out.push(active);active=null;pending=0;trailing=0;};
 for(const r of rows){
  if(last!==null&&r.t-last!==H){close('interrupted');dryBefore=0;}
  last=r.t;
  if(r.available===null||r.available>asOf||!finite(r.rain)||r.rain<0){close('interrupted');dryBefore=0;continue;}
  if(r.rain>=wetThreshold){
   if(!active){active={start:r.t-H,last_wet_end:r.t,rain_mm:0,wet_hours:0,left_censored:dryBefore<dryHours,method:'dry-gap-v1-not-CTRL-T',dry_hours:dryHours,wet_threshold_mm:wetThreshold};pending=0;}
   active.rain_mm+=pending+r.rain;active.last_wet_end=r.t;active.wet_hours++;pending=0;trailing=0;dryBefore=0;
  }else{dryBefore++;if(active){pending+=r.rain;trailing++;if(trailing>=dryHours)close('closed');}}
 }
 close('ongoing');return out.map((e,i)=>({...e,id:'EVENT-'+(i+1),rain_mm:Math.round(e.rain_mm*10000)/10000}));
}
function sourceUsable(src,asOf=Date.now()){const t=instant(src?.fetched_at);return src?.status==='ok'&&t!==null&&asOf-t>=-300000&&asOf-t<=36*H;}
function latestSoil(src,asOf=Date.now()){
 if(!sourceUsable(src,asOf))return null;
 return (src.rows||[]).filter(r=>instant(r.valid_at)!==null&&instant(r.valid_at)<=asOf&&instant(r.first_seen_at)!==null&&instant(r.first_seen_at)<=asOf).sort((a,b)=>instant(a.valid_at)-instant(b.valid_at)).at(-1)||null;
}
function laggedSoil(src,start,lagDays,asOf=Date.now()){
 const onset=instant(start);if(onset===null||!Number.isInteger(lagDays)||lagDays<0||lagDays>15)return {status:'invalid_request',row:null};
 if(!sourceUsable(src,asOf))return {status:'source_unavailable',row:null};
 const target=onset-lagDays*DAY;
 const rows=(src.rows||[]).filter(r=>instant(r.valid_at)===target&&instant(r.first_seen_at)!==null&&instant(r.first_seen_at)<=asOf);
 const row=rows.sort((a,b)=>instant(a.first_seen_at)-instant(b.first_seen_at)).at(-1)||null;
 return {status:row?'available_now_not_historical_replay':'not_available_at_target',target_at:iso(target),row,lag_days:lagDays,as_of:iso(asOf)};
}
function featurePacket(event,sample,src,{asOf=Date.now(),rainKind='model_estimate'}={}){
 const reasons=[];if(!event)reasons.push('NO_RAIN_EVENT');
 else{if(event.left_censored)reasons.push('EVENT_ONSET_UNCERTAIN');if(event.status==='interrupted')reasons.push('RAIN_GAP');if(event.status!=='closed')reasons.push('INCOMPLETE_EVENT_NOT_PAPER_ENDPOINT');}
 const s2=sample?.row?.values?.s2;
 if(!sample?.row)reasons.push('LAGGED_SOIL_UNAVAILABLE');
 if(!finite(s2)||s2<=0||s2>1)reasons.push('S2_INVALID_FOR_LOG');
 const D=event?.duration_hours,E=event?.rain_mm;
 if(!finite(D)||D<=0||!finite(E)||E<=0)reasons.push('DE_INVALID_FOR_LOG');
 const logFeatures=!reasons.length?[Math.log(D),Math.log(E),Math.log(s2)]:null;
 return {as_of:iso(asOf),doi:DOI,task:'feature_preparation_only',rain_kind:rainKind,soil_source:src?.provider||null,grid:src?.grid||null,event:event||null,lagged_sample:sample||null,log_features_DES2:logFeatures,feature_status:logFeatures?'research_features_ready':'blocked',feature_blockers:reasons,model_status:'not_trained_or_calibrated_for_Taiwan',slope_probability:null,safety_action:null};
}
const PAPER={doi:DOI,study_area:'Sicily, Italy',label:'原文結果，非 RailEye 效能；TSS ≠ 機率',lags:[0,5,15],s2_all:[.76,.70,.68],s2_test:[.73,.67,.65],all_all:[.78,.72,.67],all_test:[.75,.70,.65],pages:[9,10]};
const api={H,DAY,DOI,finite,instant,segmentRain,sourceUsable,latestSoil,laggedSoil,featurePacket,PAPER};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RailEyeHydroCore=api;
})(typeof window==='undefined'?globalThis:window);
