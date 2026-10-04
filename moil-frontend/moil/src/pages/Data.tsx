import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { IngestKind } from '../services/api'
import { getUploads, getUploadIssues, uploadCsv, getDataSourceStatus } from '../services/api'
import { useAuth } from '../store/auth'
import { Card, KpiCard, DataTable, StatusBadge, EmptyState, ErrorState, Skeleton } from '../components/ui'
import type { UploadReport, QualityIssue } from '../types'
const KINDS:Record<IngestKind,{label:string;title:string;help:string;file:string;template:string}>={
 production:{label:'Production records',title:'Upload production records (CSV)',help:'Columns: mine, date (YYYY-MM-DD), planned_t, actual_t. Rows with errors are rejected. Rows with warnings are imported and flagged. Maximum 2 MB.',file:'production-template.csv',template:'mine,date,planned_t,actual_t\nMansar,2026-10-01,6000,5800\nKandri,2026-10-01,5000,4700\n'},
 telematics:{label:'Fleet telematics',title:'Upload fleet telematics (CSV)',help:'One row per machine. Columns: code, status (Running, Idle, Breakdown or Maintenance), and optionally availability_pct, health_score, downtime_hrs. A blank cell keeps the current value. Unknown codes are rejected: machines are never created here. Maximum 2 MB.',file:'telematics-template.csv',template:'code,status,availability_pct,health_score,downtime_hrs\nEXC-1-1,Running,88,72,4\nDUM-1-2,Breakdown,40,55,12\n'},
 sap:{label:'SAP production export',title:'Upload SAP production export (CSV)',help:'Columns as in a SAP-style export: Plant (the mine name), Posting Date (30.09.2026, 20260930 or 2026-09-30), Target Qty, Confirmed Qty, and optionally Unit (TO, T, MT or KG; blank means tonnes). Results go into the same production records. Rows with errors are rejected; rows with warnings are imported and flagged. Maximum 2 MB.',file:'sap-template.csv',template:'Plant,Posting Date,Target Qty,Confirmed Qty,Unit\nMansar,30.09.2026,1100,1050,TO\nKandri,30.09.2026,1300000,1210000,KG\n'},
 stockpile:{label:'Stockpile levels',title:'Upload stockpile levels (CSV)',help:'Columns: mine, date (YYYY-MM-DD or 30.09.2026) and stockpile_t (closing stockpile in tonnes). The Control tower shows the newest reading of each mine, added together. A second reading for the same mine and day replaces the first. Rows with errors are rejected. Maximum 2 MB.',file:'stockpile-template.csv',template:'mine,date,stockpile_t\nMansar,2026-10-01,18500\nKandri,2026-10-01,22000\n'}}
const when=(s:string)=>new Date(s.endsWith('Z')?s:s+'Z').toLocaleString('en-IN')
const sevCls=(s:string)=>s==='Error'?'bg-crit/15 text-crit':'bg-warn/15 text-warn'
function Issues({issues}:{issues:QualityIssue[]}){
 if(!issues.length)return <p className="text-sm text-ok">No data-quality issues found.</p>
 return <DataTable rows={issues} cols={[{key:'row',label:'Line'},{key:'field',label:'Field'},{key:'severity',label:'Severity',render:r=><span className={`rounded px-2 py-0.5 text-xs font-medium ${sevCls(r.severity)}`}>{r.severity}</span>},{key:'message',label:'What to fix'}]}/>}
export default function Data(){
 const role=useAuth(s=>s.user!.role); const canUpload=role==='admin'||role==='data_engineer'
 const qc=useQueryClient(); const fileRef=useRef<HTMLInputElement>(null)
 const [kind,setKind]=useState<IngestKind>('production'); const K=KINDS[kind]
 const [file,setFile]=useState<File|null>(null); const [dry,setDry]=useState(true)
 const [report,setReport]=useState<{upload:UploadReport;issues:QualityIssue[]}|null>(null); const [open,setOpen]=useState<number|null>(null)
 const ups=useQuery({queryKey:['uploads'],queryFn:getUploads})
 const src=useQuery({queryKey:['sources'],queryFn:getDataSourceStatus,enabled:canUpload,retry:false})
 const detail=useQuery({queryKey:['issues',open],queryFn:()=>getUploadIssues(open!),enabled:open!==null})
 const m=useMutation({mutationFn:()=>uploadCsv(kind,file!,dry),
  onSuccess:r=>{setReport(r);setFile(null);if(fileRef.current)fileRef.current.value='';qc.invalidateQueries({queryKey:['uploads']});if(!r.upload.dryRun){['sources','history','forecast','risks','dashboard','equipment'].forEach(k=>qc.invalidateQueries({queryKey:[k]}))}}})
 const err=(m.error as any)?.response?.data?.detail||(m.isError?'Upload failed. Check that the backend is running.':'')
 const all=ups.data??[]; const real=all.filter(u=>!u.dryRun)
 const rowsIn=real.reduce((a,u)=>a+u.rowsOk,0), rowsOut=real.reduce((a,u)=>a+u.rowsRejected,0)
 const avg=all.length?Math.round(all.reduce((a,u)=>a+u.qualityPct,0)/all.length):0
 return <>
  <div className="flex flex-wrap items-center gap-3"><h1 className="mr-auto text-xl font-semibold">Data ingestion and quality</h1>
   <button onClick={()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([K.template],{type:'text/csv'}));a.download=K.file;a.click()}} className="rounded border border-line px-3 py-1.5 text-sm">Download CSV template</button></div>
  <div className="grid gap-4 sm:grid-cols-3">
   <KpiCard loading={ups.isLoading} label="Rows imported" value={rowsIn.toLocaleString('en-IN')}/>
   <KpiCard loading={ups.isLoading} label="Rows rejected" value={rowsOut.toLocaleString('en-IN')}/>
   <KpiCard loading={ups.isLoading} label="Average file quality" value={String(avg)} unit="%"/></div>
  {canUpload&&<Card title={K.title}>
   <label className="mb-3 flex items-center gap-2 text-sm">Data type<select value={kind} onChange={e=>{setKind(e.target.value as IngestKind);setReport(null);setFile(null);m.reset();if(fileRef.current)fileRef.current.value=''}} className="rounded border border-line bg-ink px-2 py-1">{(Object.keys(KINDS) as IngestKind[]).map(k=><option key={k} value={k}>{KINDS[k].label}</option>)}</select></label>
   <p className="mb-3 text-sm text-mute">{K.help}</p>
   {kind==='sap'&&<p className="mb-3 text-xs text-mute">After importing, run POST /api/v1/risks/shortfall/run so forecasts and shortfall risks use the new production data. Use the check-only option first.</p>}
   {kind==='stockpile'&&<p className="mb-3 text-xs text-mute">After importing, open the Control tower: the Stockpile level tile shows the total of the newest readings. Use the check-only option first.</p>}
   {kind==='telematics'&&<p className="mb-3 text-xs text-mute">After importing, run POST /api/v1/risks/shortfall/run so shortfall risks use the new equipment data.</p>}
   <div className="flex flex-wrap items-center gap-3">
    <input ref={fileRef} type="file" accept=".csv,text/csv" aria-label="CSV file" onChange={e=>{setFile(e.target.files?.[0]??null);setReport(null)}} className="text-sm"/>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={dry} onChange={e=>setDry(e.target.checked)}/>Check only, do not import</label>
    <button disabled={!file||m.isPending} onClick={()=>m.mutate()} className="rounded bg-mn px-3 py-1.5 text-sm text-ink disabled:opacity-40">{m.isPending?'Checking…':dry?'Check file':'Check and import'}</button></div>
   {err&&<p role="alert" className="mt-3 text-sm text-crit">{err}</p>}
   {report&&<div className="mt-4 space-y-3 border-t border-line pt-3">
    <p className="text-sm"><StatusBadge s={report.upload.status==='Failed'?'Failed':report.upload.status==='Validated'?'Warning':'Success'}/> <b>{report.upload.filename}</b>: {report.upload.rowsOk} of {report.upload.rowsTotal} rows {report.upload.dryRun?'passed the check (nothing imported)':'imported'}, {report.upload.rowsRejected} rejected, {report.upload.rowsWarning} with warnings. Quality {report.upload.qualityPct}%.</p>
    <Issues issues={report.issues}/></div>}
  </Card>}
  {canUpload&&<Card title="Data sources">{src.isLoading?<Skeleton className="h-24"/>:src.isError?<ErrorState retry={src.refetch}/>:
   <DataTable rows={src.data??[]} cols={[{key:'name',label:'Source'},{key:'status',label:'Status',render:r=><StatusBadge s={r.status}/>},{key:'records',label:'Records',render:r=>r.records.toLocaleString('en-IN')},{key:'lastSync',label:'Last sync',render:r=>r.lastSync?when(r.lastSync):'Never'}]}/>}</Card>}
  <Card title="Upload history">{ups.isLoading?<Skeleton className="h-24"/>:ups.isError?<ErrorState retry={ups.refetch}/>:!all.length?<EmptyState text="No files uploaded yet."/>:
   <DataTable rows={all} cols={[{key:'filename',label:'File'},{key:'kind',label:'Type',render:r=>r.kind==='telematics'?'Fleet telematics':r.kind==='sap'?'SAP export':r.kind==='stockpile'?'Stockpile':'Production'},{key:'createdAt',label:'When',render:r=>when(r.createdAt)},{key:'status',label:'Result',render:r=><StatusBadge s={r.status==='Failed'?'Failed':r.status==='Validated'?'Warning':'Success'}/>},{key:'mode',label:'Mode',render:r=>r.dryRun?'Check only':'Import'},{key:'rowsOk',label:'OK'},{key:'rowsRejected',label:'Rejected'},{key:'rowsWarning',label:'Warnings'},{key:'qualityPct',label:'Quality',render:r=>`${r.qualityPct}%`},
    {key:'view',label:'',render:r=>r.issuesTotal?<button onClick={()=>setOpen(open===r.id?null:r.id)} className="text-xs text-mn underline">{open===r.id?'Hide issues':`View ${r.issuesTotal} issues`}</button>:null}]}/>}
   {open!==null&&<div className="mt-3 border-t border-line pt-3">{detail.isLoading?<Skeleton className="h-16"/>:detail.isError?<ErrorState retry={detail.refetch}/>:<Issues issues={detail.data??[]}/>}</div>}
  </Card></>}
