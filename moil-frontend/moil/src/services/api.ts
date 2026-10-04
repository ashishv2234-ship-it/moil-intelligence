import axios from 'axios'
import * as M from '../lib/mock'
import type * as T from '../types'
const base=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api/v1'
const useMock=import.meta.env.VITE_USE_MOCK==='true'
const http=axios.create({baseURL:base,timeout:8000})
http.interceptors.request.use(c=>{const t=localStorage.getItem('token');if(t)c.headers.Authorization=`Bearer ${t}`;return c})
let refreshing:Promise<string>|null=null
http.interceptors.response.use(r=>r,async e=>{
 const cfg:any=e.config
 if(e.response?.status===401&&cfg&&!cfg._retry&&!String(cfg.url).includes('/auth/')){
  cfg._retry=true; const rt=localStorage.getItem('refresh')
  if(rt){try{
   // One shared refresh: tokens rotate, so parallel refreshes would trip reuse detection.
   refreshing??=axios.post(`${base}/auth/refresh`,{refresh_token:rt}).then(r=>{localStorage.setItem('token',r.data.access_token);localStorage.setItem('refresh',r.data.refresh_token);return r.data.access_token as string}).finally(()=>{refreshing=null})
   cfg.headers.Authorization=`Bearer ${await refreshing}`;return http(cfg)}catch{}}
  localStorage.clear();location.href='/login?expired=1'}
 return Promise.reject(e)})
// Real API; mock only if mock mode is on or the server is unreachable (no HTTP response).
async function call<R>(fn:()=>Promise<R>,mock:()=>R):Promise<R>{
 if(useMock)return mock()
 try{return await fn()}catch(e:any){if(e.response)throw e;return mock()}}
const mockOnly=<R,>(mock:()=>R)=>Promise.resolve(mock()) // backend endpoint not built yet
const mineNames=async():Promise<Record<number,string>>=>Object.fromEntries((await http.get('/mines',{params:{size:200}})).data.items.map((m:any)=>[m.id,m.name]))
export const getDashboardSummary=(mineId='all',days=30,range:{from:string;to:string}|null=null)=>call(async()=>(await http.get('/dashboard/summary',{params:{mine_id:mineId==='all'?undefined:Number(mineId),days,date_from:range?.from,date_to:range?.to}})).data,()=>{
 const p=M.mines.map(m=>{const r=M.genProduction(m.id,30);return{mine:m.name,planned:r.reduce((a,x)=>a+x.planned,0),actual:r.reduce((a,x)=>a+x.actual,0)}})
 const today=Math.round(M.mines.reduce((a,m)=>a+m.dailyTarget*0.93,0))
 return{today,todayDeltaPct:-7,mtd:p.reduce((a,x)=>a+x.actual,0),ytd:today*270,mineWise:p,trend:M.genProduction('m1',30),alerts:{Critical:2,High:4,Medium:7,Low:5},availability:84,stockpileT:182000,risks:M.risks}})
export const getShortfallRisks=()=>call(async()=>{
 const [r,names]=await Promise.all([http.get('/risks/shortfall'),mineNames()]); const seen=new Set<number>()
 return (r.data as any[]).filter(x=>!seen.has(x.mine_id)&&seen.add(x.mine_id)).map(x=>({id:String(x.id),mineId:String(x.mine_id),mineName:names[x.mine_id]??'Unknown',level:x.level,expectedShortfall:x.expected_shortfall_t,probability:x.probability,cause:x.main_cause,confidence:x.confidence,action:x.action??'None yet',owner:x.owner??'Unassigned',status:x.status})) as T.ShortfallRisk[]},()=>M.risks)
export const getCorrectiveActions=()=>call(async()=>{
 const [a,r,names]=await Promise.all([http.get('/actions/recommendations'),http.get('/risks/shortfall'),mineNames()])
 const mineOf:Record<number,number>=Object.fromEntries((r.data as any[]).map(x=>[x.id,x.mine_id]))
 return (a.data as any[]).map(x=>({id:String(x.id),title:`${x.action_type} at ${names[mineOf[x.risk_id]]??'mine'}`,recoveryT:Math.round(x.recovery_t),costInrLakh:x.cost_inr_lakh,feasibility:x.feasibility>=.8?'High':x.feasibility>=.6?'Medium':'Low',confidence:Math.round(x.confidence),owner:x.owner??'Unassigned',deadline:String(x.valid_until).slice(0,10),status:x.status,comments:[]})) as T.CorrectiveAction[]},()=>M.actions)
export const updateCorrectiveActionStatus=(id:string,status:T.CorrectiveAction['status'])=>call(async()=>{
 const u=`/actions/recommendations/${id}`
 return (status==='Approved'?await http.post(`${u}/approve`):status==='Rejected'?await http.post(`${u}/reject`):await http.patch(`${u}/status`,{status})).data},()=>({id,status}))
// Workflow (real backend only, no mock fallback). Risk owners are kept per mine; comments belong to one corrective action.
export const errText=(e:any,fallback:string)=>{const d=e?.response?.data?.detail; return Array.isArray(d)?(d[0]?.msg??fallback):typeof d==='string'?d:fallback}
export const getAssignableUsers=async()=>(await http.get('/workflow/assignable-users')).data as T.OwnerOption[]
export const setRiskOwner=async(mineId:string,userId:number|null)=>(await http.put('/risks/owner',{mine_id:Number(mineId),user_id:userId})).data
export const assignAction=async(id:string,owner:string)=>(await http.post(`/actions/recommendations/${id}/assign`,{owner})).data
export const getActionComments=async(id:string)=>((await http.get(`/actions/recommendations/${id}/comments`)).data as any[]).map(c=>({id:c.id,text:c.text,author:c.author,role:c.role,createdAt:c.created_at})) as T.ActionComment[]
export const addActionComment=async(id:string,text:string)=>(await http.post(`/actions/recommendations/${id}/comments`,{text})).data
export const getEquipmentStatus=()=>call(async()=>((await http.get('/equipment',{params:{size:200}})).data.items as any[]).map(e=>({id:e.code,type:e.type,mineId:String(e.mine_id),status:e.status,availability:e.availability_pct,health:e.health_score,downtimeHrs:e.downtime_hrs,mtbfHrs:0})) as T.Equipment[],()=>M.equipment)
export const getDataSourceStatus=()=>call(async()=>((await http.get('/data-sources')).data as any[]).map(d=>({id:String(d.id),name:d.name,lastSync:d.last_sync??'',status:d.status,records:d.records,issues:0})) as T.DataSourceStatus[],()=>M.dataSources)
export const getMines=()=>call(async()=>((await http.get('/mines',{params:{size:200}})).data.items as any[]).map(m=>({id:String(m.id),name:m.name as string,dailyTarget:m.daily_target_t as number})),()=>M.mines.map(m=>({id:m.id,name:m.name,dailyTarget:m.dailyTarget})))
export interface ForecastInfo{points:T.ProductionForecast[];seasonalAdjusted:boolean;outliersReplaced:number}
export const getProductionForecastInfo=(mineId:string,horizon=30)=>call(async()=>{
 const [f,mines]=await Promise.all([http.get('/production/forecast',{params:{mine_id:Number(mineId),horizon}}),getMines()])
 const target=mines.find(m=>m.id===mineId)?.dailyTarget??0
 const points=(f.data.points as any[]).map(p=>({date:new Date(Date.now()+p.day_offset*864e5).toISOString().slice(0,10),planned:target,forecast:p.forecast_t,lower:p.lower_t,upper:p.upper_t})) as T.ProductionForecast[]
 return{points,seasonalAdjusted:!!f.data.seasonal_adjusted,outliersReplaced:Number(f.data.outliers_replaced??0)} as ForecastInfo},
 ()=>({points:M.genForecast(mineId,horizon),seasonalAdjusted:false,outliersReplaced:0} as ForecastInfo))
export const getProductionForecast=(mineId:string,horizon=30)=>getProductionForecastInfo(mineId,horizon).then(r=>r.points)
export const getProductionHistory=(mineId:string,days=30)=>call(async()=>((await http.get('/production/records',{params:{mine_id:Number(mineId),days}})).data as any[]).map(r=>({date:r.day as string,planned:r.planned_t as number,actual:r.actual_t as number})),()=>M.genProduction(mineId,days).map(r=>({date:r.date,planned:r.planned,actual:r.actual})))
export const acknowledgeRisk=(id:string)=>call(async()=>(await http.post(`/risks/shortfall/${id}/acknowledge`)).data,()=>({id}))
export const resolveRisk=(id:string)=>call(async()=>(await http.post(`/risks/shortfall/${id}/resolve`)).data,()=>({id}))
// Not built in the backend yet: these keep using mock data.
// Reserve prospectivity (real backend; mock only if the server is unreachable).
export const getReserveProspectivity=()=>call(async()=>((await http.get('/geology/zones')).data as any[]).map(z=>({id:`z${z.id}`,lat:z.lat,lng:z.lng,probability:Math.round(z.probability),tonnage:z.tonnage_t,gradeMnPct:z.grade_mn_pct,confidence:z.confidence_pct>=75?'High':z.confidence_pct>=55?'Medium':'Low',confidencePct:Math.round(z.confidence_pct),holesNearby:z.holes_nearby,drillSuggested:z.drill_suggested,drillRecommended:z.drill_recommended,modelVersion:z.model_version,runAt:z.run_at})) as T.ReserveZone[],()=>M.zones)
export const getDrillHoles=()=>call(async()=>((await http.get('/geology/drill-holes')).data as any[]).map(h=>({id:h.id,lat:h.lat,lng:h.lng,depthM:h.depth_m,mnPct:h.mn_pct})) as T.DrillHole[],()=>M.drillHoles)
export const runProspectivityModel=async()=>(await http.post('/geology/prospectivity/run')).data
export const recommendDrilling=async(id:string)=>(await http.post(`/geology/zones/${id.replace(/\D/g,'')}/drilling`)).data
export const getMaintenanceAlerts=()=>mockOnly(()=>[] as T.MaintenanceRecord[])
export const uploadGeologicalData=(_kind:string,_file:File)=>mockOnly(()=>({ok:true,rows:0}))
// Data ingestion (real backend only: no mock fallback, so a failed upload is never faked).
const toReport=(u:any):T.UploadReport=>({id:u.id,kind:u.kind,filename:u.filename,status:u.status,dryRun:u.dry_run,rowsTotal:u.rows_total,rowsOk:u.rows_ok,rowsRejected:u.rows_rejected,rowsWarning:u.rows_warning,issuesTotal:u.issues_total,qualityPct:u.quality_pct,createdAt:u.created_at})
export type IngestKind='production'|'telematics'|'sap'|'stockpile'
export const uploadCsv=async(kind:IngestKind,file:File,dryRun:boolean)=>{
 const r=await http.post(`/ingestion/${kind}`,file,{params:{filename:file.name,dry_run:dryRun},headers:{'Content-Type':'text/csv'},timeout:60000})
 return{upload:toReport(r.data.upload),issues:r.data.issues as T.QualityIssue[]}}
export const uploadProductionCsv=(file:File,dryRun:boolean)=>uploadCsv('production',file,dryRun)
export const getUploads=async()=>((await http.get('/ingestion/uploads')).data as any[]).map(toReport)
export const getUploadIssues=async(id:number)=>(await http.get(`/ingestion/uploads/${id}/issues`)).data as T.QualityIssue[]
// Blasting (real backend).
const toBlast=(b:any):T.BlastRecord=>({id:String(b.id),mineId:String(b.mine_id),bench:b.bench,date:b.blast_date,plannedT:b.planned_t,actualT:b.actual_t??undefined,status:b.status,reason:b.delay_reason??undefined,weather:b.weather?{status:b.weather.status,observedAt:b.weather.observed_at,kind:b.weather.kind,rainMm:b.weather.rain_mm??undefined,windKmh:b.weather.wind_kmh??undefined,nextSuitable:b.weather.next_suitable??undefined}:undefined})
export const getBlastingOperations=()=>call(async()=>((await http.get('/blasting')).data as any[]).map(toBlast),()=>[] as T.BlastRecord[])
export const scheduleBlast=async(b:{mineId:string;bench:string;date:string;plannedT:number})=>toBlast((await http.post('/blasting',{mine_id:Number(b.mineId),bench:b.bench,blast_date:b.date,planned_t:b.plannedT})).data)
export const completeBlast=async(id:string,actualT:number)=>toBlast((await http.post(`/blasting/${id}/complete`,{actual_t:actualT})).data)
export const delayBlast=async(id:string,reason:string)=>toBlast((await http.post(`/blasting/${id}/delay`,{reason})).data)
// Reports (real backend). JSON preview feeds the table and the PDF print; csv/xlsx are file downloads.
export const getReport=async(kind:string,days=30,range:{from:string;to:string}|null=null):Promise<T.ReportData>=>{const d=(await http.get(`/reports/${kind}`,{params:{days,date_from:range?.from,date_to:range?.to}})).data;return{title:d.title,columns:d.columns,rows:d.rows,note:d.note,generatedAt:d.generated_at}}
export const downloadReport=async(kind:string,format:'csv'|'xlsx',days=30,range:{from:string;to:string}|null=null)=>{
 const r=await http.get(`/reports/${kind}`,{params:{format,days,date_from:range?.from,date_to:range?.to},responseType:'blob'})
 const a=document.createElement('a');a.href=URL.createObjectURL(r.data);a.download=`moil-${kind}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
// Administration (admin only, real backend, no mock fallback).
const toUser=(u:any):T.AdminUser=>({id:u.id,email:u.email,name:u.name,role:String(u.role).toLowerCase() as T.Role,isActive:u.is_active,locked:u.locked})
export const getAdminUsers=async()=>((await http.get('/admin/users')).data as any[]).map(toUser)
export const createAdminUser=async(b:{email:string;name:string;password:string;role:T.Role})=>toUser((await http.post('/admin/users',{...b,role:b.role.toUpperCase()})).data)
export const updateAdminUser=async(id:number,b:{role?:T.Role;isActive?:boolean;unlock?:boolean})=>toUser((await http.patch(`/admin/users/${id}`,{role:b.role?.toUpperCase(),is_active:b.isActive,unlock:b.unlock})).data)
export const resetUserPassword=async(id:number,password:string)=>{await http.post(`/admin/users/${id}/reset-password`,{password})}
export const getAuditLogs=async(p:{page:number;action?:string;days?:number}):Promise<T.AuditPage>=>{const d=(await http.get('/admin/audit-logs',{params:{page:p.page,size:25,action:p.action||undefined,days:p.days||undefined}})).data
 return{items:d.items.map((a:any)=>({id:a.id,at:a.at,action:a.action,detail:a.detail??{},userEmail:a.user_email,userName:a.user_name})),total:d.total,page:d.page,size:d.size}}
export const getAuditActions=async()=>(await http.get('/admin/audit-actions')).data as string[]
export const changePassword=async(current:string,next:string)=>{
 const {data}=await http.post('/auth/change-password',{current_password:current,new_password:next})
 localStorage.setItem('token',data.access_token);localStorage.setItem('refresh',data.refresh_token)} // other devices are signed out; this one stays in
export interface WeatherRow{mineId:string;mine:string;observedAt:string;tempC:number;humidityPct:number;windKmh:number;rainNowMm:number;rainTodayMm:number;blasting:'Suitable'|'Caution'|'Unsuitable'}
export const getWeather=()=>call(async()=>((await http.get('/weather/current')).data as any[]).map(w=>({mineId:String(w.mine_id),mine:w.mine_name,observedAt:w.observed_at,tempC:w.temp_c,humidityPct:w.humidity_pct,windKmh:w.wind_kmh,rainNowMm:w.rain_now_mm,rainTodayMm:w.rain_today_mm,blasting:w.blasting})) as WeatherRow[],()=>[] as WeatherRow[])
export const syncWeather=async()=>(await http.post('/weather/sync',null,{timeout:60000})).data as {updated:number;failed:string[];forecast_updated:number}  // 10 sequential weather requests can take longer than the default 8 s
// Satellite layers (real backend, no mock fallback so nothing is faked).
export interface SatLayer{indicator:string;observedOn:string|null;source:string|null;cellDeg:number;min:number;max:number;cells:{lat:number;lng:number;value:number}[]}
export const getSatelliteLayer=async(k:string):Promise<SatLayer>=>{const d=(await http.get(`/satellite/layers/${k}`)).data;return{indicator:d.indicator,observedOn:d.observed_on,source:d.source,cellDeg:d.cell_deg,min:d.min,max:d.max,cells:d.cells}}
export interface SatSummary{indicator:string;label:string;unit:string;count:number;observedOn:string|null;source:string|null}
export const getSatelliteSummary=async()=>((await http.get('/satellite/layers')).data as any[]).map(x=>({indicator:x.indicator,label:x.label,unit:x.unit,count:x.count,observedOn:x.observed_on,source:x.source})) as SatSummary[]
export const syncSatellite=async()=>(await http.post('/satellite/sync',null,{timeout:60000})).data as {updated:number;cells:number}
export const uploadSatelliteCsv=async(file:File)=>(await http.post('/satellite/upload',file,{params:{filename:file.name},headers:{'Content-Type':'text/csv'},timeout:60000})).data as {imported:number;rejected:number;indicators:string[];issues:{row:number;message:string}[]}
export interface ForecastDay{day:string;rainMm:number;windKmh:number;blasting:'Suitable'|'Caution'|'Unsuitable'}
export interface MineForecast{mineId:string;mine:string;fetchedAt:string;days:ForecastDay[]}
export const getWeatherForecast=()=>call(async()=>((await http.get('/weather/forecast')).data as any[]).map(m=>({mineId:String(m.mine_id),mine:m.mine_name,fetchedAt:m.fetched_at,days:(m.days as any[]).map(d=>({day:d.day,rainMm:d.rain_mm,windKmh:d.wind_kmh,blasting:d.blasting}))})) as MineForecast[],()=>[] as MineForecast[])
// Shortfall history (real backend only, no mock fallback). Each point is one saved risk run; factors explain one run's probability.
export const getRiskHistory=async(mineId:string,limit=30)=>((await http.get('/risks/history',{params:{mine_id:Number(mineId),limit}})).data as any[]).map(x=>({id:x.id,at:String(x.created_at).slice(0,16).replace('T',' '),level:x.level,probability:x.probability,expectedShortfall:Math.round(x.expected_shortfall_t),cause:x.main_cause})) as T.RiskRun[]
export const getRiskFactors=async(riskId:string)=>(await http.get(`/risks/shortfall/${riskId}/factors`)).data as T.RiskFactor[]
// Equipment history (real backend only, no mock fallback): one point per real telematics import inside the period.
export const getEquipmentHistory=async(mineId='all',days=30,range:{from:string;to:string}|null=null)=>((await http.get('/equipment/history',{params:{mine_id:mineId==='all'?undefined:Number(mineId),days,date_from:range?.from,date_to:range?.to}})).data.points as any[]).map(x=>({uploadId:x.upload_id,at:String(x.taken_at).slice(0,16).replace('T',' '),machines:x.machines,availability:x.avg_availability,health:x.avg_health,breakdowns:x.breakdowns,downtimeHrs:x.downtime_hrs})) as T.EquipmentPoint[]
