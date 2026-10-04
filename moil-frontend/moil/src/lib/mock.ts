import type * as T from '../types'
let s=42; const rnd=()=>(s=(s*16807)%2147483647)/2147483647
const pick=<A,>(a:readonly A[]):A=>a[Math.floor(rnd()*a.length)]
export const mines:T.Mine[]=([['Balaghat','MP',21.8,80.2,2200],['Dongri Buzurg','MH',21.2,79.6,1800],['Gumgaon','MH',21.3,79.1,1500],['Kandri','MH',21.3,79.3,1300],['Mansar','MH',21.4,79.3,1100],['Ukwa','MP',22.0,80.3,900],['Beldongri','MH',21.1,79.2,700]] as const)
.map(([name,state,lat,lng,t],i)=>({id:`m${i+1}`,name,state,lat,lng,dailyTarget:t,
 pits:[1,2].map(p=>({id:`m${i+1}p${p}`,name:`Pit ${p}`,benches:[1,2,3].map(b=>({id:`m${i+1}p${p}b${b}`,name:`Bench ${b}`,rl:480-b*12}))}))}))
const day=(o:number)=>new Date(Date.now()+o*864e5).toISOString().slice(0,10)
export const genProduction=(mineId:string,days=365):T.ProductionRecord[]=>{const m=mines.find(x=>x.id===mineId)!
 return Array.from({length:days},(_,i)=>{const d=day(i-days),mo=new Date(d).getMonth();const monsoon=mo>=5&&mo<=8
 return{date:d,mineId,planned:m.dailyTarget,actual:Math.round(m.dailyTarget*(0.82+rnd()*0.26)*(monsoon?0.88:1))}})}
export const genForecast=(mineId:string,days=90):T.ProductionForecast[]=>{const m=mines.find(x=>x.id===mineId)!
 return Array.from({length:days},(_,i)=>{const f=Math.round(m.dailyTarget*(0.9+rnd()*0.12));return{date:day(i+1),planned:m.dailyTarget,forecast:f,lower:Math.round(f*0.92),upper:Math.round(f*1.07)}})}
export const equipment:T.Equipment[]=mines.flatMap(m=>(['Excavator','Dumper','Drill','Loader','Crusher'] as const).map((type,i)=>({id:`${type.slice(0,3).toUpperCase()}-${m.id.toUpperCase()}-${i+1}`,type,mineId:m.id,status:pick(['Running','Running','Running','Idle','Breakdown','Maintenance'] as const),availability:Math.round(70+rnd()*28),health:Math.round(55+rnd()*43),downtimeHrs:Math.round(rnd()*60),mtbfHrs:Math.round(120+rnd()*300)})))
const lvl=(g:number):T.Severity=>g>8?'Critical':g>5?'High':g>2?'Medium':'Low'
export const risks:T.ShortfallRisk[]=mines.map((m,i)=>{const g=rnd()*12;return{id:`r${i}`,mineId:m.id,mineName:m.name,level:lvl(g),expectedShortfall:Math.round(m.dailyTarget*g/100*30),probability:Math.round(40+rnd()*55),cause:pick(['Dumper downtime','Monsoon rainfall','Blasting delay','Low-grade benches','Haulage constraint','Maintenance backlog']),confidence:Math.round(70+rnd()*25),action:pick(['Redeploy loaders','Re-sequence faces','Pre-build stockpile','Adjust blasting schedule']),owner:pick(['Mine Manager','Planning Cell','Maintenance Head']),status:pick(['Open','In Progress','Resolved'] as const)}})
export const actions:T.CorrectiveAction[]=risks.slice(0,5).map((r,i)=>({id:`a${i}`,title:`${r.action} at ${r.mineName}`,recoveryT:Math.round(r.expectedShortfall*0.6),costInrLakh:Math.round(5+rnd()*40),feasibility:pick(['High','Medium','Low'] as const),confidence:r.confidence,owner:r.owner,deadline:day(3+i*2),status:'Proposed' as const,comments:[]}))
export const dataSources:T.DataSourceStatus[]=([['Production MIS','Success'],['Fleet telematics','Warning'],['Drill-hole DB','Success'],['IMD weather feed','Failed'],['Sentinel-2 layers','Success']] as const).map(([name,status],i)=>({id:`d${i}`,name,status,lastSync:new Date(Date.now()-rnd()*864e5).toISOString(),records:Math.round(rnd()*50000),issues:status==='Success'?0:Math.round(rnd()*40)}))
export const zones:T.ReserveZone[]=Array.from({length:60},(_,i)=>({id:`z${i}`,lat:21.0+rnd()*1.0,lng:79.0+rnd()*1.3,probability:Math.round(rnd()*100),tonnage:Math.round(50e3+rnd()*900e3),gradeMnPct:Math.round(28+rnd()*22),confidence:pick(['High','Medium','Low'] as const),drillRecommended:false}))
// Demo geology layers for the reserve map (no geology backend yet). Appended last so earlier mock values are unchanged.
export const drillHoles:T.DrillHole[]=Array.from({length:40},(_,i)=>({id:`DH-${String(i+1).padStart(3,'0')}`,lat:+(21.0+rnd()*1.0).toFixed(4),lng:+(79.0+rnd()*1.3).toFixed(4),depthM:Math.round(40+rnd()*260),mnPct:+(8+rnd()*40).toFixed(1)}))
const OFF:[number,number][]=[[.04,-.05],[.05,.04],[-.03,.06],[-.05,-.02]]
export const mineBoundaries:{id:string;name:string;pts:[number,number][]}[]=mines.map(m=>{const k=0.8+rnd()*0.5;return{id:m.id,name:m.name,pts:OFF.map(([a,b])=>[+(m.lat+a*k).toFixed(4),+(m.lng+b*k).toFixed(4)] as [number,number])}})
export const lineaments:[number,number][][]=Array.from({length:8},()=>{const la=21.0+rnd()*0.9,ln=79.0+rnd()*1.1,dl=0.2+rnd()*0.3,dn=0.25+rnd()*0.35,j=(rnd()-.5)*0.08
 return [[la,ln],[la+dl*.5+j,ln+dn*.5-j],[la+dl,ln+dn]].map(([a,b])=>[+a.toFixed(4),+b.toFixed(4)] as [number,number])})
export type Indicator='ndvi'|'soil'|'lst'|'rain'
export const INDICATORS:Record<Indicator,{label:string;unit:string;min:number;max:number;from:string;to:string;k:number}>={
 ndvi:{label:'NDVI (vegetation)',unit:'',min:0,max:0.9,from:'#7a5a2e',to:'#2ea84f',k:1},
 soil:{label:'Soil moisture',unit:'%',min:5,max:45,from:'#e9d9a6',to:'#2563b8',k:2},
 lst:{label:'Land-surface temperature',unit:'°C',min:24,max:46,from:'#3b82f6',to:'#e5534b',k:3},
 rain:{label:'Rainfall (monthly)',unit:'mm',min:0,max:120,from:'#dbeafe',to:'#4c1d95',k:4}}
// Smooth fake field in 0..1, stable for a given place. Replace with Sentinel-2 / IMD rasters later.
export const indicatorT=(l:Indicator,lat:number,lng:number)=>0.5+0.5*Math.sin(lat*(7+INDICATORS[l].k)+lng*(5+INDICATORS[l].k*1.7)+INDICATORS[l].k)
