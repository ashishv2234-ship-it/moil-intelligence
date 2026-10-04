import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, BarChart, Bar, Legend } from 'recharts'
import { getDashboardSummary, getWeather, syncWeather } from '../services/api'
import { useAuth } from '../store/auth'
import { useToast } from '../components/Toast'
import { useFilters, periodText } from '../store/filters'
import { Card, KpiCard, DataTable, RiskBadge, EmptyState, ErrorState, Skeleton } from '../components/ui'
const f=(n:number)=>n.toLocaleString('en-IN')
const when=(s:string)=>new Date(/Z|[+-]\d\d:\d\d$/.test(s)?s:s+'Z').toLocaleString('en-IN')
const wc:Record<string,string>={Suitable:'bg-ok/15 text-ok',Caution:'bg-warn/15 text-warn',Unsuitable:'bg-high/15 text-high'}
export default function Dashboard(){
 const {mineId,days,range}=useFilters(); const {data,isLoading,isError,refetch}=useQuery({queryKey:['summary',mineId,days,range?.from,range?.to],queryFn:()=>getDashboardSummary(mineId,days,range)})
 const qc=useQueryClient(); const toast=useToast(); const canSync=['admin','mine_manager','data_engineer'].includes(useAuth(s=>s.user!.role))
 const wxq=useQuery({queryKey:['weather'],queryFn:getWeather}); const wx=(wxq.data??[]).filter(w=>mineId==='all'||w.mineId===mineId)
 const sync=useMutation({mutationFn:syncWeather,onSuccess:r=>{qc.invalidateQueries({queryKey:['weather']});qc.invalidateQueries({queryKey:['sources']});toast(r.failed.length?'warning':'success',r.failed.length?`Weather updated for ${r.updated} mines. Failed: ${r.failed.join(', ')}.`:`Weather updated for ${r.updated} mines.`)},onError:(e:any)=>toast('error',e.response?.data?.detail||'Could not update the weather.')})
 if(isError)return <ErrorState retry={refetch}/>
 const d=data
 return <>
  <h1 className="text-xl font-semibold">Control tower</h1>
  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
   <KpiCard loading={isLoading} label="Production today" value={d&&f(d.today)} unit="tonnes" delta={d?.todayDeltaPct}/>
   <KpiCard loading={isLoading} label="Month to date" value={d&&f(d.mtd)} unit="tonnes"/>
   <KpiCard loading={isLoading} label="Equipment availability" value={d&&String(d.availability)} unit="%"/>
   <KpiCard loading={isLoading} label={`Stockpile level${d?.stockpileAsOf?` (as of ${d.stockpileAsOf}${d.stockpileMines<d.totalMines?`, ${d.stockpileMines} of ${d.totalMines} mines`:''})`:''}`} value={d?(d.stockpileT==null?"Not connected":f(d.stockpileT)):""} unit={d?.stockpileT==null?"":"tonnes"}/></div>
  <div className="grid gap-4 xl:grid-cols-2">
   <Card title={`Planned vs actual, ${periodText(days,range)} (tonnes/day)`}>{isLoading?<Skeleton className="h-64"/>:<ResponsiveContainer height={260}><LineChart data={d.trend}><XAxis dataKey="date" tick={{fontSize:10}}/><YAxis tick={{fontSize:10}}/><Tooltip/><Legend/><Line dataKey="planned" stroke="#8A949E" dot={false}/><Line dataKey="actual" stroke="#3FB58A" dot={false}/></LineChart></ResponsiveContainer>}</Card>
   <Card title={`Mine-wise production, ${periodText(days,range)} (tonnes)`}>{isLoading?<Skeleton className="h-64"/>:<ResponsiveContainer height={260}><BarChart data={d.mineWise}><XAxis dataKey="mine" tick={{fontSize:10}}/><YAxis tick={{fontSize:10}}/><Tooltip/><Legend/><Bar dataKey="planned" fill="#8A949E"/><Bar dataKey="actual" fill="#2F6FA8"/></BarChart></ResponsiveContainer>}</Card></div>
  <Card title="Weather and blasting conditions" right={canSync&&<button onClick={()=>sync.mutate()} disabled={sync.isPending} className="rounded border border-line px-3 py-1 text-xs disabled:opacity-50">{sync.isPending?'Updating':'Refresh weather'}</button>}>
   {!wx.length?<EmptyState text={canSync?'No weather data yet. Click Refresh weather.':'No weather data yet. A data engineer or mine manager can refresh it.'}/>:<>
    <DataTable rows={wx} cols={[{key:'mine',label:'Mine'},{key:'tempC',label:'Temperature (°C)',render:r=>r.tempC.toFixed(1)},{key:'rainTodayMm',label:'Rain today (mm)',render:r=>r.rainTodayMm.toFixed(1)},{key:'windKmh',label:'Wind (km/h)',render:r=>r.windKmh.toFixed(0)},{key:'blasting',label:'Blasting',render:r=><span className={`rounded px-2 py-0.5 text-xs font-medium ${wc[r.blasting]}`}>{r.blasting}</span>}]}/>
    <p className="mt-2 text-xs text-mute">Source: Open-Meteo, updated {when(wx[0].observedAt)}. Unsuitable: 10 mm or more rain today, rain falling now, or wind of 40 km/h or more. Caution: 3 mm or more rain today, or wind of 25 km/h or more.</p></>}</Card>
  <Card title="Shortfall risk by mine" right={<span className="text-xs text-mn">AI-generated forecast</span>}>
   <DataTable rows={d?.risks??[]} cols={[{key:'mineName',label:'Mine'},{key:'level',label:'Risk',render:r=><RiskBadge level={r.level}/>},{key:'expectedShortfall',label:'Expected shortfall (tonnes)',render:r=>f(r.expectedShortfall)},{key:'cause',label:'Main cause'},{key:'confidence',label:'Confidence (%)'}]}/></Card></>}
