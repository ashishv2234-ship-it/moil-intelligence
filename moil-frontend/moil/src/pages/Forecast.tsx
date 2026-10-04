import { useState } from 'react'
import { useFilters } from '../store/filters'
import { useQuery } from '@tanstack/react-query'
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import { getMines, getProductionHistory, getProductionForecastInfo, getShortfallRisks, getCorrectiveActions } from '../services/api'
import { Card, KpiCard, DataTable, RiskBadge, ErrorState, Skeleton } from '../components/ui'
const f=(n:number)=>Math.round(n).toLocaleString('en-IN')
export default function Forecast(){
 const [mineId,setMineId]=useState(''); const [horizon,setHorizon]=useState(30)
 const mines=useQuery({queryKey:['mines'],queryFn:getMines})
 const gm=useFilters(s=>s.mineId); const sel=gm!=='all'?gm:(mineId||mines.data?.[0]?.id)
 const fc=useQuery({queryKey:['forecast',sel,horizon],queryFn:()=>getProductionForecastInfo(sel!,horizon),enabled:!!sel})
 const risks=useQuery({queryKey:['risks'],queryFn:getShortfallRisks}); const acts=useQuery({queryKey:['actions'],queryFn:getCorrectiveActions})
 const hist=useQuery({queryKey:['history',sel],queryFn:()=>getProductionHistory(sel!,30),enabled:!!sel})
 const cap=Math.max(1,...(hist.data??[]).map(h=>h.planned),...(fc.data?.points??[]).map(p=>p.planned))*2; const tall=(hist.data??[]).filter(h=>h.actual>cap)
 const pts=fc.data?.points??[]; const planned=pts.reduce((a,p)=>a+p.planned,0), fore=pts.reduce((a,p)=>a+p.forecast,0)
 const pct=planned?Math.round((fore-planned)/planned*100):0
 const rows=(mines.data??[]).map(m=>{const r=risks.data?.find(x=>x.mineName===m.name); const a=acts.data?.find(x=>x.title.endsWith(` at ${m.name}`))
  const p=m.dailyTarget*30, gap=r?.expectedShortfall??0
  return{mine:m.name,planned:p,forecast:p-gap,gap:-gap,level:r?.level??'Low',reason:r?.cause??'On track',action:a?a.title.split(' at ')[0]:'None needed'}})
 if(fc.isError)return <ErrorState retry={fc.refetch}/>
 return <>
  <div className="flex flex-wrap items-center gap-3"><h1 className="mr-auto text-xl font-semibold">Production forecast</h1>
   <select aria-label="Mine" disabled={gm!=='all'} title={gm!=='all'?'Change the mine in the top bar':undefined} value={sel??''} onChange={e=>setMineId(e.target.value)} className="rounded border border-line bg-panel px-2 py-1.5 text-sm">{mines.data?.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select>
   <select aria-label="Horizon" value={horizon} onChange={e=>setHorizon(+e.target.value)} className="rounded border border-line bg-panel px-2 py-1.5 text-sm">{[7,30,90].map(h=><option key={h} value={h}>Next {h} days</option>)}</select></div>
  <div className="grid gap-4 sm:grid-cols-3">
   <KpiCard loading={fc.isLoading} label={`Planned, next ${horizon} days`} value={f(planned)} unit="tonnes"/>
   <KpiCard loading={fc.isLoading} label="Forecast" value={f(fore)} unit="tonnes" delta={pct}/>
   <KpiCard loading={fc.isLoading} label="Gap to plan" value={f(fore-planned)} unit="tonnes"/></div>
  <Card title="Planned, actual and forecast (tonnes/day)" right={<span className="text-xs text-mn">AI-generated forecast · shaded band is the 80% confidence range</span>}>
   {fc.isLoading?<Skeleton className="h-72"/>:<ResponsiveContainer height={300}><ComposedChart data={[...(hist.data??[]).map(h=>({date:h.date,planned:h.planned,actual:h.actual})),...pts.map(p=>({date:p.date,planned:p.planned,forecast:p.forecast,range:[p.lower,p.upper]}))]}>
    <XAxis dataKey="date" tick={{fontSize:10}} minTickGap={30}/><YAxis tick={{fontSize:10}} allowDataOverflow domain={['auto',(max:number)=>Math.ceil(Math.min(max,cap))]}/><Tooltip/><Legend/>
    <Area dataKey="range" name="Confidence range" stroke="none" fill="#2F6FA8" fillOpacity={.2}/><Line dataKey="planned" name="Planned" stroke="#8A949E" dot={false}/><Line dataKey="actual" name="Actual (last 30 days)" stroke="#3FB58A" dot={false}/><Line dataKey="forecast" name="Forecast" stroke="#2F6FA8" strokeWidth={2} dot={false}/></ComposedChart></ResponsiveContainer>}
   {tall.length>0&&<p className="mt-2 text-xs text-warn">{tall.length===1?'1 day is':`${tall.length} days are`} above the chart range and not drawn to scale: {tall.map(h=>`${h.date} (${h.actual.toLocaleString('en-IN')} t)`).join(', ')}. The forecast ignores extreme high days. Check them on the Data quality page.</p>}
   {fc.data&&<p className="mt-2 text-xs text-mute">{fc.data.seasonalAdjusted?'Seasonal adjustment applied. A monthly pattern was learned from about a year of history (each month limited to 70-130% of the average), so a monsoon dip is not mistaken for a lasting trend and recovery after it is expected.':'No seasonal adjustment. It needs about a year of dated history (330 days or more, with at least 10 days in a month). Until then recent output is treated as the normal level, so a seasonal dip may be read as a lasting trend.'}{fc.data.outliersReplaced>0&&` ${fc.data.outliersReplaced} unusually high ${fc.data.outliersReplaced===1?'day':'days'} in the last 56 days ${fc.data.outliersReplaced===1?'was':'were'} replaced by the typical value before forecasting.`}</p>}</Card>
  <Card title="30-day outlook by mine" right={<span className="text-xs text-mn">AI-generated · gap equals the expected shortfall</span>}>
   <DataTable rows={rows} cols={[{key:'mine',label:'Mine'},{key:'planned',label:'Planned (tonnes)',render:r=>f(r.planned)},{key:'forecast',label:'Forecast (tonnes)',render:r=>f(r.forecast)},{key:'gap',label:'Gap (tonnes)',render:r=>f(r.gap)},{key:'level',label:'Risk',render:r=><RiskBadge level={r.level}/>},{key:'reason',label:'Main reason'},{key:'action',label:'Recommended action'}]}/></Card></>}
