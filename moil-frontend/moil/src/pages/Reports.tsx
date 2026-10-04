import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getReport, downloadReport } from '../services/api'
import { useAuth } from '../store/auth'
import { useFilters } from '../store/filters'
import { useToast } from '../components/Toast'
import { Card, DataTable, EmptyState, ErrorState, Skeleton } from '../components/ui'
import type { ReportData, Role } from '../types'
const plan:Role[]=['admin','mine_manager','planning_engineer','executive']
const REPORTS:{id:string;label:string;desc:string;roles:Role[];days?:boolean}[]=[
 {id:'production',label:'Production summary',desc:'Planned vs actual tonnes by mine.',roles:plan,days:true},
 {id:'risks',label:'Shortfall risk',desc:'Latest risk level, expected shortfall and cause for each mine.',roles:plan},
 {id:'actions',label:'Corrective actions',desc:'All recommended actions with cost, recovery and status.',roles:plan},
 {id:'equipment',label:'Equipment status',desc:'Availability, health and downtime for every machine.',roles:['admin','mine_manager','maintenance_engineer','executive']},
 {id:'blasting',label:'Blasting log',desc:'Scheduled, completed and delayed blasts.',roles:['admin','mine_manager','executive'],days:true}]
const esc=(s:unknown)=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c] as string))
function printPdf(d:ReportData,blocked:()=>void){
 const w=window.open('','_blank'); if(!w){blocked();return}
 w.document.write(`<!doctype html><html><head><title>${esc(d.title)}</title><style>body{font-family:Arial,sans-serif;margin:24px;color:#111}h1{font-size:18px}p{font-size:12px;color:#444}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #bbb;padding:4px 6px;text-align:left}th{background:#eee}</style></head><body><h1>MOIL: ${esc(d.title)}</h1><p>Generated ${esc(new Date(d.generatedAt).toLocaleString('en-IN'))}</p>${d.note?`<p><b>${esc(d.note)}</b></p>`:''}<table><thead><tr>${d.columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${d.rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></body></html>`)
 w.document.close(); w.focus(); setTimeout(()=>w.print(),300)}
export default function Reports(){
 const role=useAuth(s=>s.user!.role); const toast=useToast(); const mine=REPORTS.filter(r=>r.roles.includes(role))
 const [kind,setKind]=useState(''); const days=useFilters(s=>s.days); const range=useFilters(s=>s.range); const [busy,setBusy]=useState(''); const [err,setErr]=useState('')
 const cur=mine.find(r=>r.id===kind)??mine[0]
 const q=useQuery({queryKey:['report',cur?.id,days,range?.from,range?.to],queryFn:()=>getReport(cur!.id,days,range),enabled:!!cur})
 if(!cur)return <><h1 className="text-xl font-semibold">Reports</h1><Card><EmptyState text="No reports are available for your role yet."/></Card></>
 const dl=async(fmt:'csv'|'xlsx')=>{setBusy(fmt);setErr('');try{await downloadReport(cur.id,fmt,days,range)}catch(e:any){setErr(e.response?.status===403?'Your role cannot download this report.':'Download failed. Check that the backend is running.')}finally{setBusy('')}}
 const d=q.data; const btn="rounded border border-line px-3 py-1.5 text-sm disabled:opacity-40"
 return <>
  <h1 className="text-xl font-semibold">Reports</h1>
  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{mine.map(r=><button key={r.id} onClick={()=>setKind(r.id)} className={`rounded-lg border p-3 text-left ${r.id===cur.id?'border-mn bg-mn/10':'border-line bg-panel'}`}><p className="text-sm font-semibold">{r.label}</p><p className="mt-1 text-xs text-mute">{r.desc}</p></button>)}</div>
  <Card title={d?.title??cur.label} right={<div className="flex flex-wrap items-center gap-2">
    {cur.days&&<span className="text-xs text-mute">{range?`${range.from} to ${range.to}`:`Last ${days} days`} (set in the top bar)</span>}
    {!cur.days&&<span className="text-xs text-mute">Current position (the top-bar period does not apply)</span>}
    <button disabled={!d||busy!==''} onClick={()=>dl('xlsx')} className={btn}>{busy==='xlsx'?'Preparing…':'Excel'}</button>
    <button disabled={!d||busy!==''} onClick={()=>dl('csv')} className={btn}>{busy==='csv'?'Preparing…':'CSV'}</button>
    <button disabled={!d} onClick={()=>printPdf(d!,()=>toast('warning','Allow pop-ups for this site, then try again.'))} className="rounded bg-mn px-3 py-1.5 text-sm text-ink disabled:opacity-40">PDF</button></div>}>
   {err&&<p role="alert" className="mb-2 text-sm text-crit">{err}</p>}
   {q.isLoading?<Skeleton className="h-40"/>:q.isError?<ErrorState retry={q.refetch}/>:d&&<>
    {d.note&&<p className="mb-2 text-xs text-mn">{d.note}</p>}
    <DataTable rows={d.rows.slice(0,15).map(r=>Object.fromEntries(r.map((v,i)=>['c'+i,v])))} cols={d.columns.map((c,i)=>({key:'c'+i,label:c,render:(r:any)=>typeof r['c'+i]==='number'?r['c'+i].toLocaleString('en-IN'):String(r['c'+i])}))}/>
    <p className="mt-2 text-xs text-mute">{d.rows.length>15?`Showing 15 of ${d.rows.length} rows. Downloads contain all rows.`:`${d.rows.length} rows.`} PDF opens the print dialog: choose "Save as PDF".</p></>}</Card></>}
