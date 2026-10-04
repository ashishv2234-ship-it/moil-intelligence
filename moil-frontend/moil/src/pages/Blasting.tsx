import { useState } from 'react'
import { useFilters, periodText } from '../store/filters'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getBlastingOperations, getMines, scheduleBlast, completeBlast, delayBlast, getWeatherForecast, syncWeather } from '../services/api'
import { useAuth } from '../store/auth'
import { Card, KpiCard, DataTable, Modal, ErrorState, Skeleton } from '../components/ui'
import type { BlastRecord } from '../types'
type Dlg={kind:'new'}|{kind:'complete'|'delay';b:BlastRecord}
const badge:Record<string,string>={Scheduled:'bg-info/15 text-info',Completed:'bg-ok/15 text-ok',Delayed:'bg-warn/15 text-warn'}
const wc:Record<string,string>={Suitable:'bg-ok/15 text-ok',Caution:'bg-warn/15 text-warn',Unsuitable:'bg-high/15 text-high'}
const f=(n:number)=>Math.round(n).toLocaleString('en-IN')
const dayLabel=(d:string)=>new Date(d+'T00:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})
const iso=(offsetDays:number)=>new Date(Date.now()+offsetDays*864e5).toISOString().slice(0,10)
const input="w-full rounded border border-line bg-ink px-2 py-1.5 text-sm"
export default function Blasting(){
 const canEdit=['admin','mine_manager'].includes(useAuth(s=>s.user!.role)); const qc=useQueryClient()
 const fc=useQuery({queryKey:['forecast'],queryFn:getWeatherForecast,retry:false}); const [wxBusy,setWxBusy]=useState(false); const [wxMsg,setWxMsg]=useState('')
 const refreshWx=async()=>{setWxBusy(true);setWxMsg('');try{await syncWeather();await Promise.all([qc.invalidateQueries({queryKey:['forecast']}),qc.invalidateQueries({queryKey:['blasts']})])}catch(e:any){setWxMsg(e.response?.data?.detail??'Could not refresh the forecast.')}finally{setWxBusy(false)}}
 const blasts=useQuery({queryKey:['blasts'],queryFn:getBlastingOperations}); const mines=useQuery({queryKey:['mines'],queryFn:getMines})
 const gm=useFilters(s=>s.mineId); const days=useFilters(s=>s.days); const range=useFilters(s=>s.range); const mine=gm==='all'?'All':gm; const [st,setSt]=useState('All'); const [dlg,setDlg]=useState<Dlg|null>(null)
 const [bench,setBench]=useState(''); const [date,setDate]=useState(iso(2)); const [planned,setPlanned]=useState(''); const [mineId,setMineId]=useState('')
 const [actual,setActual]=useState(''); const [reason,setReason]=useState(''); const [err,setErr]=useState('')
 const close=()=>{setDlg(null);setErr('');setBench('');setPlanned('');setActual('');setReason('')}
 const m=useMutation({mutationFn:async()=>{
   if(!dlg)return
   if(dlg.kind==='new'){const mid=mineId||mines.data?.[0]?.id; if(!mid||!bench.trim()||!date||!(+planned>0))throw new Error('Fill in the mine, bench, date and planned tonnes (more than 0).'); return scheduleBlast({mineId:mid,bench:bench.trim(),date,plannedT:+planned})}
   if(dlg.kind==='complete'){if(actual===''||+actual<0)throw new Error('Enter the actual tonnes (zero or more).'); return completeBlast(dlg.b.id,+actual)}
   if(reason.trim().length<3)throw new Error('Enter a reason (at least 3 characters).'); return delayBlast(dlg.b.id,reason.trim())},
  onSuccess:()=>{qc.invalidateQueries({queryKey:['blasts']});close()},
  onError:(e:any)=>setErr(e.response?.data?.detail?.[0]?.msg||(typeof e.response?.data?.detail==='string'?e.response.data.detail:'')||e.message||'Could not save.')})
 if(blasts.isError)return <ErrorState retry={blasts.refetch}/>
 const all=blasts.data??[]; const name=(id:string)=>mines.data?.find(x=>x.id===id)?.name??`Mine ${id}`
 const rows=all.filter(b=>(mine==='All'||b.mineId===mine)&&(st==='All'||b.status===st))
 const bad=rows.filter(b=>b.weather?.kind==='current'&&b.weather.status==='Unsuitable')
 const soon=rows.filter(b=>b.weather?.kind==='forecast'&&b.weather.status==='Unsuitable').sort((a,b)=>a.date.localeCompare(b.date))
 const outlook=(fc.data??[]).filter(x=>mine==='All'||x.mineId===mine)
 const pickMine=mineId||mines.data?.[0]?.id||''; const pickDay=(fc.data??[]).find(x=>x.mineId===pickMine)?.days.find(d=>d.day===date)
 const today=iso(0), in7=iso(7), from=range?range.from:iso(-days), to=range?range.to:'9999-12-31'
 const inPeriod=(d:string)=>d>=from&&d<=to; const per=periodText(days,range); const capped=all.length>=200
 const scope=all.filter(b=>mine==='All'||b.mineId===mine)  // the figures below follow the top-bar mine and period
 const upcoming=scope.filter(b=>b.status==='Scheduled'&&b.date>=today&&b.date<=in7).length
 const delayed=scope.filter(b=>b.status==='Delayed'&&inPeriod(b.date)).length
 const done=scope.filter(b=>b.status==='Completed'&&inPeriod(b.date)); const dp=done.reduce((a,b)=>a+b.plannedT,0), da=done.reduce((a,b)=>a+(b.actualT??0),0)
 const sel="rounded border border-line bg-panel px-2 py-1.5 text-sm"
 return <>
  <div className="flex flex-wrap items-center gap-3"><h1 className="mr-auto text-xl font-semibold">Blasting</h1>
   
   <select aria-label="Status" value={st} onChange={e=>setSt(e.target.value)} className={sel}>{['All','Scheduled','Completed','Delayed'].map(x=><option key={x}>{x}</option>)}</select>
   {canEdit&&<button onClick={()=>setDlg({kind:'new'})} className="rounded bg-mn px-3 py-1.5 text-sm text-ink">Schedule blast</button>}</div>
  {bad.length>0&&<p role="alert" className="rounded border border-high/40 bg-high/10 px-3 py-2 text-sm text-high">{bad.length===1?'1 blast is':`${bad.length} blasts are`} scheduled for today but conditions are unsuitable (heavy rain or strong wind). Consider delaying.</p>}
  {soon.length>0&&<p role="status" className="rounded border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">{soon.length===1?'1 scheduled blast has':`${soon.length} scheduled blasts have`} an unsuitable weather forecast: {soon.slice(0,4).map(b=>`${name(b.mineId)} ${b.bench} on ${dayLabel(b.date)}${b.weather?.nextSuitable?` (next suitable day ${dayLabel(b.weather.nextSuitable)})`:''}`).join('; ')}{soon.length>4?` and ${soon.length-4} more`:''}. Forecasts can change, so check again closer to the day.</p>}
  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
   <KpiCard loading={blasts.isLoading} label="Scheduled, next 7 days" value={String(upcoming)} unit="blasts"/>
   <KpiCard loading={blasts.isLoading} label={`Delayed, ${per}`} value={String(delayed)} unit="blasts"/>
   <KpiCard loading={blasts.isLoading} label={`Blasted, ${per}`} value={f(da)} unit="tonnes"/>
   <KpiCard loading={blasts.isLoading} label={`Plan adherence, ${per}`} value={dp?String(Math.round(da/dp*100)):'n/a'} unit={dp?'%':''}/></div>
  {capped&&<p role="status" className="text-xs text-warn">Only the latest 200 blasts are loaded, so totals for a long period may be incomplete.</p>}
  <Card title="Blasting outlook, next 7 days" right={<span className="flex items-center gap-3 text-xs text-mute">{fc.data?.[0]&&<span>Forecast fetched {new Date(fc.data[0].fetchedAt.endsWith('Z')?fc.data[0].fetchedAt:fc.data[0].fetchedAt+'Z').toLocaleString('en-IN')}</span>}{canEdit&&<button onClick={refreshWx} disabled={wxBusy} className="rounded border border-line px-2 py-1 disabled:opacity-50">{wxBusy?'Refreshing...':'Refresh forecast'}</button>}</span>}>
   {fc.isLoading?<Skeleton className="h-24"/>:fc.isError?<ErrorState retry={fc.refetch}/>:!outlook.length?<p className="text-sm text-mute">No recent forecast yet.{canEdit?' Click "Refresh forecast" (needs internet).':' Ask a mine manager to refresh it.'}</p>:
   <div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="text-left text-mute"><th className="py-1 pr-3 font-medium">Mine</th>{outlook[0].days.slice(0,8).map(d=><th key={d.day} className="px-1 py-1 font-medium">{dayLabel(d.day)}</th>)}</tr></thead>
    <tbody>{outlook.map(m=><tr key={m.mineId} className="border-t border-line"><td className="py-1 pr-3 font-medium">{m.mine}</td>{m.days.slice(0,8).map(d=><td key={d.day} className="px-1 py-1"><span title={`${d.rainMm} mm rain, wind up to ${d.windKmh} km/h`} className={`rounded px-1.5 py-0.5 ${wc[d.blasting]}`}>{d.blasting}</span></td>)}</tr>)}</tbody></table></div>}
   {wxMsg&&<p role="alert" className="mt-2 text-xs text-crit">{wxMsg}</p>}
   <p className="mt-2 text-xs text-mute">Rule-based early warning from Open-Meteo daily forecasts: Unsuitable at 10 mm or more rain or wind up to 40 km/h or more; Caution at 3 mm or 25 km/h. Hover a cell for the numbers.</p></Card>
  <Card title={`Blast plan (${rows.length})`} right={<span className="text-xs text-mute">Weather check covers scheduled blasts from today to 7 days ahead: live reading for today, forecast after that.</span>}>{blasts.isLoading?<Skeleton className="h-40"/>:
   <DataTable rows={rows} cols={[{key:'date',label:'Date'},{key:'mineId',label:'Mine',render:r=>name(r.mineId)},{key:'bench',label:'Bench'},{key:'plannedT',label:'Planned (tonnes)',render:r=>f(r.plannedT)},{key:'actualT',label:'Actual (tonnes)',render:r=>r.actualT!==undefined?f(r.actualT):'-'},
    {key:'status',label:'Status',render:r=><span className={`rounded px-2 py-0.5 text-xs font-medium ${badge[r.status]}`}>{r.status}</span>},{key:'weather',label:'Weather',render:r=>r.weather?<span className="flex flex-wrap items-center gap-1"><span title={r.weather.kind==='forecast'?`Forecast: ${r.weather.rainMm} mm rain, wind up to ${r.weather.windKmh} km/h`:'Live reading'} className={`rounded px-2 py-0.5 text-xs font-medium ${wc[r.weather.status]}`}>{r.weather.status}</span><span className="text-xs text-mute">{r.weather.kind==='forecast'?'forecast':'now'}</span>{r.weather.nextSuitable&&<span className="text-xs text-mute">next suitable {dayLabel(r.weather.nextSuitable)}</span>}</span>:<span className="text-mute">-</span>},{key:'reason',label:'Note',render:r=>r.reason??''},
    {key:'act',label:'',render:r=>canEdit&&r.status!=='Completed'?<span className="flex gap-2"><button onClick={()=>setDlg({kind:'complete',b:r})} className="text-xs text-mn underline">Mark completed</button>{r.status==='Scheduled'&&<button onClick={()=>setDlg({kind:'delay',b:r})} className="text-xs text-mute underline">Delay</button>}</span>:null}]}/>}</Card>
  <Modal open={!!dlg} title={dlg?.kind==='new'?'Schedule a blast':dlg?.kind==='complete'?'Mark blast completed':'Delay this blast'} onClose={close}>
   {dlg?.kind==='new'&&<div className="space-y-3 text-sm">
    <label className="block">Mine<select value={mineId||mines.data?.[0]?.id||''} onChange={e=>setMineId(e.target.value)} className={input}>{mines.data?.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
    <label className="block">Bench<input value={bench} onChange={e=>setBench(e.target.value)} placeholder="Bench 3" className={input}/></label>
    <label className="block">Date<input type="date" value={date} onChange={e=>setDate(e.target.value)} className={input}/>{pickDay?<span className={`mt-1 inline-block rounded px-2 py-0.5 text-xs ${wc[pickDay.blasting]}`}>Forecast for this day: {pickDay.blasting} ({pickDay.rainMm} mm rain, wind up to {pickDay.windKmh} km/h)</span>:<span className="mt-1 block text-xs text-mute">No forecast for this day (the forecast covers the next 7 days).</span>}</label>
    <label className="block">Planned tonnes<input type="number" min="1" value={planned} onChange={e=>setPlanned(e.target.value)} className={input}/></label></div>}
   {dlg?.kind==='complete'&&<label className="block text-sm"><span className="mb-2 block text-mute">{name(dlg.b.mineId)}, {dlg.b.bench}, planned {f(dlg.b.plannedT)} tonnes</span>Actual tonnes<input type="number" min="0" value={actual} onChange={e=>setActual(e.target.value)} className={input}/></label>}
   {dlg?.kind==='delay'&&<label className="block text-sm"><span className="mb-2 block text-mute">{name(dlg.b.mineId)}, {dlg.b.bench}, {dlg.b.date}</span>Reason<input value={reason} onChange={e=>setReason(e.target.value)} placeholder="For example: heavy rain" className={input}/></label>}
   {err&&<p role="alert" className="mt-3 text-sm text-crit">{err}</p>}
   <button disabled={m.isPending} onClick={()=>m.mutate()} className="mt-4 rounded bg-mn px-3 py-1.5 text-sm text-ink disabled:opacity-40">{m.isPending?'Saving…':'Confirm'}</button></Modal></>}
