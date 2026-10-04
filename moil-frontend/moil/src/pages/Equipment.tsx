import { useState } from 'react'
import { useFilters, periodText } from '../store/filters'
import { useQuery } from '@tanstack/react-query'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, CartesianGrid } from 'recharts'
import { getEquipmentStatus, getMines, getEquipmentHistory } from '../services/api'
import { Card, KpiCard, DataTable, StatusBadge, RiskBadge, ErrorState, Skeleton, EmptyState } from '../components/ui'
import type { Equipment as Eq, Severity } from '../types'
const avg=(a:number[])=>a.length?Math.round(a.reduce((x,y)=>x+y,0)/a.length):0
const order:Record<Severity,number>={Critical:0,High:1,Medium:2,Low:3}
// Transparent rules, not a trained model: each flag states why it fired.
function flag(e:Eq):{level:Severity;why:string}|null{
 if(e.status==='Breakdown')return{level:'Critical',why:'Currently in breakdown'}
 if(e.health<60)return{level:'High',why:`Health score ${Math.round(e.health)} is below 60`}
 if(e.availability<75)return{level:'Medium',why:`Availability ${Math.round(e.availability)}% is below 75%`}
 return null}
const Health=({v}:{v:number})=><div className="flex items-center gap-2"><div className="h-1.5 w-20 rounded bg-line"><div className={`h-1.5 rounded ${v>=75?'bg-ok':v>=60?'bg-warn':'bg-crit'}`} style={{width:`${Math.max(0,Math.min(100,v))}%`}}/></div><span>{Math.round(v)}</span></div>
export default function Equipment(){
 const eq=useQuery({queryKey:['equipment'],queryFn:getEquipmentStatus}); const mines=useQuery({queryKey:['mines'],queryFn:getMines})
 const gm=useFilters(s=>s.mineId); const mine=gm==='all'?'All':gm; const [st,setSt]=useState('All')
 const days=useFilters(s=>s.days); const range=useFilters(s=>s.range)
 const hist=useQuery({queryKey:['equipment-history',gm,days,range],queryFn:()=>getEquipmentHistory(gm,days,range),retry:false})
 if(eq.isError)return <ErrorState retry={eq.refetch}/>
 const all=eq.data??[]; const name=(id:string)=>mines.data?.find(m=>m.id===id)?.name??`Mine ${id}`
 const rows=all.filter(e=>(mine==='All'||e.mineId===mine)&&(st==='All'||e.status===st))
 const flagged=all.map(e=>({e,f:flag(e)})).filter(x=>x.f).sort((a,b)=>order[a.f!.level]-order[b.f!.level]||a.e.health-b.e.health).slice(0,8)
 const byMine=(mines.data??[]).map(m=>({mine:m.name,availability:avg(all.filter(e=>e.mineId===m.id).map(e=>e.availability))}))
 const sel="rounded border border-line bg-panel px-2 py-1.5 text-sm"
 return <>
  <div className="flex flex-wrap items-center gap-3"><h1 className="mr-auto text-xl font-semibold">Equipment and maintenance</h1>
   
   <select aria-label="Status" value={st} onChange={e=>setSt(e.target.value)} className={sel}>{['All','Running','Idle','Breakdown','Maintenance'].map(x=><option key={x}>{x}</option>)}</select></div>
  <p className="text-xs text-mute">The tiles, charts and list below are the latest snapshot and ignore the top-bar period. Only the history card follows the period and mine.</p>
  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
   <KpiCard loading={eq.isLoading} label="Fleet availability" value={String(avg(all.map(e=>e.availability)))} unit="%"/>
   <KpiCard loading={eq.isLoading} label="Average health score" value={String(avg(all.map(e=>e.health)))} unit="/ 100"/>
   <KpiCard loading={eq.isLoading} label="Machines running" value={String(all.filter(e=>e.status==='Running').length)} unit={`of ${all.length}`}/>
   <KpiCard loading={eq.isLoading} label="Breakdowns" value={String(all.filter(e=>e.status==='Breakdown').length)}/></div>
  <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
   <Card title="Average availability by mine (%)">{eq.isLoading?<Skeleton className="h-60"/>:<ResponsiveContainer height={240}><BarChart data={byMine}><XAxis dataKey="mine" tick={{fontSize:10}}/><YAxis domain={[0,100]} tick={{fontSize:10}}/><Tooltip/><Bar dataKey="availability" name="Availability %" fill="#2F6FA8"/></BarChart></ResponsiveContainer>}</Card>
   <Card title="Maintenance priority" right={<span className="text-xs text-mute">Rule-based flags, each with its reason</span>}>
    {eq.isLoading?<Skeleton className="h-60"/>:!flagged.length?<EmptyState text="No machines need attention."/>:
    <ul className="space-y-2">{flagged.map(({e,f})=><li key={e.id} className="flex flex-wrap items-center gap-2 border-b border-line pb-2 text-sm last:border-0"><RiskBadge level={f!.level}/><b>{e.id}</b><span className="text-mute">{e.type} · {name(e.mineId)}</span><span className="ml-auto text-xs text-mute">{f!.why}</span></li>)}</ul>}
    <p className="mt-2 text-xs text-mute">Due dates and task history need maintenance-system data, which is not connected yet.</p></Card></div>
  <Card title={`Availability history, ${periodText(days,range)}`} right={<span className="text-xs text-mute">One point per telematics import</span>}>
   {hist.isLoading?<Skeleton className="h-48"/>:hist.isError?<ErrorState retry={hist.refetch}/>:!hist.data?.length?<EmptyState text="No telematics imports in this period. History is saved from each real (not check-only) import made after this feature was added."/>
   :<ResponsiveContainer height={220}><LineChart data={hist.data} margin={{left:0,right:10}}><CartesianGrid strokeDasharray="3 3" opacity={.3}/><XAxis dataKey="at" tick={{fontSize:9}} tickFormatter={(v:string)=>v.slice(5,10)}/><YAxis domain={[0,100]} tick={{fontSize:10}} width={35}/>
    <Tooltip formatter={(v:any)=>[`${v}%`,'Average availability']} labelFormatter={(l:any,p:any)=>{const x=p?.[0]?.payload;return x?`${l} · ${x.machines} machines · ${x.breakdowns} in breakdown · health ${x.health}`:l}}/><Line type="monotone" dataKey="availability" stroke="#2F6FA8" dot={{r:3}}/></LineChart></ResponsiveContainer>}
   <p className="mt-2 text-xs text-mute">Each point averages only the machines in that file, so a file with a few machines can move the line. Times are UTC. Earlier availability was not saved, so history cannot go back before the first import after this update.</p></Card>
  <Card title={`Equipment list (${rows.length})`}>{eq.isLoading?<Skeleton className="h-40"/>:
   <DataTable rows={rows} cols={[{key:'id',label:'Code'},{key:'type',label:'Type'},{key:'mineId',label:'Mine',render:r=>name(r.mineId)},{key:'status',label:'Status',render:r=><StatusBadge s={r.status}/>},{key:'availability',label:'Availability',render:r=>`${Math.round(r.availability)}%`},{key:'health',label:'Health',render:r=><Health v={r.health}/>},{key:'downtimeHrs',label:'Downtime (hrs)',render:r=>Math.round(r.downtimeHrs)}]}/>}</Card></>}
