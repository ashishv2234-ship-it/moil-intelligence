import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, CartesianGrid } from 'recharts'
import { getShortfallRisks, acknowledgeRisk, resolveRisk, getAssignableUsers, setRiskOwner, getRiskHistory, getRiskFactors, errText } from '../services/api'
import { useAuth } from '../store/auth'
import { Card, RiskBadge, StatusBadge, EmptyState, ErrorState, Skeleton } from '../components/ui'
import { useFilters } from '../store/filters'
import { useToast } from '../components/Toast'
import type { Severity } from '../types'
const LV:Severity[]=['Critical','High','Medium','Low']
const tile:Record<Severity,string>={Critical:'border-crit bg-crit/20',High:'border-high bg-high/20',Medium:'border-warn bg-warn/20',Low:'border-ok bg-ok/20'}
const f=(n:number)=>Math.round(n).toLocaleString('en-IN')
function Why({id,probability}:{id:string;probability:number}){
 const [open,setOpen]=useState(false); const q=useQuery({queryKey:['factors',id],queryFn:()=>getRiskFactors(id),enabled:open,retry:false})
 return <div className="mt-1 text-sm"><button onClick={()=>setOpen(!open)} className="text-xs text-mn underline">{open?'Hide':'Why this probability?'}</button>
  {open&&<div className="mt-1 rounded border border-line p-2 text-xs">{q.isLoading?'Loading…':q.isError?'Could not load the reasons.':!q.data?.length?'Not recorded for this run. Re-run risks to record the reasons.'
   :<><ul>{q.data.map(x=><li key={x.label} className="flex justify-between gap-4"><span>{x.label}</span><b>{x.points>0&&x.label!=='Base'?'+':''}{x.points}</b></li>)}</ul><p className="mt-1 flex justify-between border-t border-line pt-1"><span>Probability</span><b>{probability}%</b></p>
   <p className="mt-1 text-mute">Rule-based points, not a learned model. Weather and rainfall only change the probability, never the level.</p></>}</div>}</div>}
function History({mines,initial}:{mines:{id:string;name:string}[];initial:string}){
 const [sel,setSel]=useState(initial); const id=mines.some(m=>m.id===sel)?sel:mines[0]?.id
 const q=useQuery({queryKey:['risk-history',id],queryFn:()=>getRiskHistory(id),enabled:!!id,retry:false})
 return <Card title="Shortfall history" right={<select aria-label="History mine" value={id} onChange={e=>setSel(e.target.value)} className="rounded border border-line bg-panel px-2 py-1 text-xs">{mines.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select>}>
  {q.isLoading?<Skeleton className="h-48"/>:q.isError?<ErrorState retry={q.refetch}/>:(q.data?.length??0)<2?<EmptyState text="Run the risk check at least twice to see a trend for this mine."/>:
  <div className="grid gap-4 md:grid-cols-2">{[['probability','Probability (%)','#2F6FA8'],['expectedShortfall','Expected shortfall (tonnes)','#E8A15D']].map(([k,t,c])=><div key={k}><p className="mb-1 text-xs text-mute">{t}</p>
   <ResponsiveContainer height={200}><LineChart data={q.data} margin={{left:0,right:10}}><CartesianGrid strokeDasharray="3 3" opacity={.3}/><XAxis dataKey="at" tick={{fontSize:9}} tickFormatter={(v:string)=>v.slice(5,10)}/><YAxis tick={{fontSize:10}} width={45}/>
    <Tooltip formatter={(v:any)=>[k==='probability'?`${v}%`:`${f(v)} t`,t]} labelFormatter={(l:any,p:any)=>`${l} · ${p?.[0]?.payload?.level??''}`}/><Line type="monotone" dataKey={k} stroke={c} dot={{r:3}}/></LineChart></ResponsiveContainer></div>)}</div>}
  <p className="mt-2 text-xs text-mute">One point per saved risk run (latest 30), so several runs on one day show as several points. Level and cause are shown in the tooltip.</p></Card>}
export default function Risks(){
 const {data,isLoading,isError,refetch}=useQuery({queryKey:['risks'],queryFn:getShortfallRisks})
 const gm=useFilters(s=>s.mineId); const [lv,setLv]=useState('All'); const [st,setSt]=useState('All')
 const qc=useQueryClient(); const toast=useToast(); const ack=useMutation({mutationFn:acknowledgeRisk,onSuccess:()=>{qc.invalidateQueries({queryKey:['risks']});toast('success','Risk acknowledged and moved to In Progress.')},onError:(e:any)=>toast('error',e.response?.data?.detail||'Could not acknowledge this risk.')})
 const res=useMutation({mutationFn:resolveRisk,onSuccess:()=>{qc.invalidateQueries({queryKey:['risks']});toast('success','Risk marked as Resolved.')},onError:(e:any)=>toast('error',e.response?.data?.detail||'Could not resolve this risk.')}); const canResolve=['admin','mine_manager','planning_engineer'].includes(useAuth(s=>s.user!.role))
 const canAssign=['admin','mine_manager'].includes(useAuth(s=>s.user!.role)); const [edit,setEdit]=useState<string|null>(null); const [pick,setPick]=useState('')
 const users=useQuery({queryKey:['assignable'],queryFn:getAssignableUsers,enabled:canAssign,retry:false})
 const own=useMutation({mutationFn:(p:{mineId:string;userId:number|null})=>setRiskOwner(p.mineId,p.userId),onSuccess:(_,p)=>{qc.invalidateQueries({queryKey:['risks']});setEdit(null);toast('success',p.userId===null?'Owner cleared.':'Owner saved.')},onError:(e:any)=>toast('error',errText(e,'Could not save the owner.'))})
 if(isError)return <ErrorState retry={refetch}/>
 const all=(data??[]).filter(r=>gm==='all'||r.mineId===gm); const rows=all.filter(r=>(lv==='All'||r.level===lv)&&(st==='All'||r.status===st)).sort((a,b)=>b.expectedShortfall-a.expectedShortfall)
 const causes=Object.entries(all.reduce<Record<string,number>>((m,r)=>({...m,[r.cause]:(m[r.cause]??0)+r.expectedShortfall}),{})).map(([cause,tonnes])=>({cause,tonnes:Math.round(tonnes)})).sort((a,b)=>b.tonnes-a.tonnes)
 return <>
  <div className="flex flex-wrap items-center gap-3"><h1 className="mr-auto text-xl font-semibold">Shortfall risk</h1>
   <select aria-label="Risk level" value={lv} onChange={e=>setLv(e.target.value)} className="rounded border border-line bg-panel px-2 py-1.5 text-sm">{['All',...LV].map(x=><option key={x}>{x}</option>)}</select>
   <select aria-label="Status" value={st} onChange={e=>setSt(e.target.value)} className="rounded border border-line bg-panel px-2 py-1.5 text-sm">{['All','Open','In Progress','Resolved'].map(x=><option key={x}>{x}</option>)}</select></div>
  <Card title="Risk by mine, next 30 days" right={<span className="text-xs text-mn">AI-generated forecast</span>}>
   {isLoading?<Skeleton className="h-20"/>:<div className="flex flex-wrap gap-2">{all.map(r=><div key={r.id} className={`w-36 rounded border-l-4 p-2 text-sm ${tile[r.level]}`}><p className="font-medium">{r.mineName}</p><p className="text-xs">{r.level} · {f(r.expectedShortfall)} tonnes</p></div>)}</div>}
   <p className="mt-2 text-xs text-mute">Pit and bench level risk needs bench-level production data, which is not connected yet.</p></Card>
  {!isLoading&&all.length>0&&<History mines={Array.from(new Map(all.map(r=>[r.mineId,{id:r.mineId,name:r.mineName}])).values())} initial={gm==='all'?all[0].mineId:gm}/>}
  <div className="grid gap-4 xl:grid-cols-[1fr_2fr]">
   <Card title="Expected shortfall by cause (tonnes)">{isLoading?<Skeleton className="h-64"/>:<ResponsiveContainer height={260}><BarChart data={causes} layout="vertical" margin={{left:40}}><XAxis type="number" tick={{fontSize:10}}/><YAxis type="category" dataKey="cause" width={130} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="tonnes" fill="#2F6FA8"/></BarChart></ResponsiveContainer>}</Card>
   <div className="space-y-3">{isLoading?<Skeleton className="h-40"/>:!rows.length?<Card><EmptyState text="No risks match these filters."/></Card>:rows.map(r=>
    <Card key={r.id}><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{r.mineName}</p><div className="flex gap-2"><RiskBadge level={r.level}/><StatusBadge s={r.status}/></div></div>
     <p className="mt-2 text-sm">Expected shortfall <b>{f(r.expectedShortfall)} tonnes</b> · probability <b>{r.probability}%</b></p>
     <p className="text-sm text-mute">Main cause: {r.cause} · Owner: {r.owner} · Recommended: {r.action}</p>
     {canAssign&&(edit===r.mineId?<div className="mt-2 flex flex-wrap items-center gap-2 text-sm"><select aria-label="Owner" value={pick} onChange={e=>setPick(e.target.value)} className="rounded border border-line bg-panel px-2 py-1">
       <option value="">{users.isLoading?'Loading…':users.isError?'Could not load people':'Choose a person'}</option>{(users.data??[]).map(u=><option key={u.id} value={u.id}>{u.name} · {u.role.toLowerCase().replace(/_/g,' ')}</option>)}</select>
       <button disabled={!pick||own.isPending} onClick={()=>own.mutate({mineId:r.mineId,userId:+pick})} className="rounded bg-mn px-3 py-1 text-xs text-ink disabled:opacity-40">Save</button>
       {r.owner!=='Unassigned'&&<button disabled={own.isPending} onClick={()=>own.mutate({mineId:r.mineId,userId:null})} className="rounded border border-line px-3 py-1 text-xs">Clear owner</button>}
       <button onClick={()=>setEdit(null)} className="text-xs text-mute underline">Cancel</button></div>
      :<button onClick={()=>{setEdit(r.mineId);setPick('')}} className="mt-1 text-xs text-mn underline">{r.owner==='Unassigned'?'Assign owner':'Change owner'}</button>)}
     <Why id={r.id} probability={r.probability}/>
     <div className="mt-1 flex items-center justify-between"><p className="text-xs text-mn">AI-generated forecast · {Math.round(r.confidence)}% confidence</p>{r.status==='Open'&&<button onClick={()=>ack.mutate(r.id)} className="rounded border border-line px-3 py-1 text-xs">Acknowledge</button>}{r.status==='In Progress'&&canResolve&&<button disabled={res.isPending} onClick={()=>res.mutate(r.id)} className="rounded border border-line px-3 py-1 text-xs disabled:opacity-40">Mark resolved</button>}</div></Card>)}</div></div></>}
