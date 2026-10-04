import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdminUsers, createAdminUser, updateAdminUser, resetUserPassword, getAuditLogs, getAuditActions } from '../services/api'
import { useAuth } from '../store/auth'
import { Card, DataTable, Modal, Skeleton, ErrorState } from '../components/ui'
import type { AdminUser, AuditEntry, Role } from '../types'
const ROLES:{v:Role;l:string}[]=[{v:'admin',l:'Admin'},{v:'mine_manager',l:'Mine manager'},{v:'geologist',l:'Geologist'},{v:'planning_engineer',l:'Planning engineer'},{v:'maintenance_engineer',l:'Maintenance engineer'},{v:'executive',l:'Executive'},{v:'data_engineer',l:'Data engineer'}]
const roleLabel=(r:string)=>ROLES.find(x=>x.v===r)?.l??r
const when=(s:string)=>new Date(/Z|[+-]\d\d:\d\d$/.test(s)?s:s+'Z').toLocaleString('en-IN')
const msg=(e:any)=>{const d=e?.response?.data?.detail;return typeof d==='string'?d:Array.isArray(d)?'Please check the fields: '+d.map((x:any)=>x.loc?.slice(-1)[0]).join(', '):'Something went wrong. Check the backend window for the error.'}
const input="rounded border border-line bg-ink px-2 py-1.5 text-sm"
type Dlg={kind:'add'}|{kind:'password';u:AdminUser}|{kind:'toggle';u:AdminUser}|null
export default function Settings(){
 const [tab,setTab]=useState<'users'|'audit'>('users')
 return <>
  <h1 className="text-xl font-semibold">Administration</h1>
  <div className="flex gap-2">{(['users','audit'] as const).map(t=><button key={t} onClick={()=>setTab(t)} className={`rounded px-3 py-1.5 text-sm ${tab===t?'bg-mn text-ink':'border border-line'}`}>{t==='users'?'Users':'Audit log'}</button>)}</div>
  {tab==='users'?<Users/>:<Audit/>}</>}
function Users(){
 const qc=useQueryClient(); const me=useAuth(s=>s.user!.id)
 const q=useQuery({queryKey:['admin-users'],queryFn:getAdminUsers})
 const [dlg,setDlg]=useState<Dlg>(null); const [err,setErr]=useState(''); const [note,setNote]=useState('')
 const [f,setF]=useState({name:'',email:'',password:'',role:'executive' as Role}); const [pw,setPw]=useState('')
 const act=useMutation({mutationFn:(fn:()=>Promise<unknown>)=>fn()})
 const run=(fn:()=>Promise<unknown>,text:string)=>{setErr('');setNote('')
  act.mutate(fn,{onSuccess:async()=>{setDlg(null);setNote(text);await qc.invalidateQueries({queryKey:['admin-users']});qc.invalidateQueries({queryKey:['audit']})},onError:e=>setErr(msg(e))})}
 const open=(d:Dlg)=>{setErr('');setNote('');setPw('');setDlg(d)}
 if(q.isError)return <ErrorState retry={q.refetch}/>
 const rows=q.data??[]
 return <>
  <Card title={`Users (${rows.length})`} right={<button onClick={()=>{setF({name:'',email:'',password:'',role:'executive'});open({kind:'add'})}} className="rounded bg-mn px-3 py-1 text-sm text-ink">Add user</button>}>
   {note&&<p role="status" className="mb-3 text-sm text-ok">{note}</p>}
   {!dlg&&err&&<p role="alert" className="mb-3 text-sm text-crit">{err}</p>}
   {q.isLoading?<Skeleton className="h-40"/>:<DataTable rows={rows} cols={[
    {key:'name',label:'Name'},{key:'email',label:'Email'},
    {key:'role',label:'Role',render:(u:AdminUser)=>u.id===+me?<span>{roleLabel(u.role)} (you)</span>:
      <select aria-label={`Role for ${u.name}`} value={u.role} onChange={e=>run(()=>updateAdminUser(u.id,{role:e.target.value as Role}),`${u.name} is now ${roleLabel(e.target.value)}.`)} className={input}>{ROLES.map(r=><option key={r.v} value={r.v}>{r.l}</option>)}</select>},
    {key:'isActive',label:'Account',render:(u:AdminUser)=><span className={u.isActive?'text-ok':'text-crit'}>{u.isActive?'Active':'Disabled'}{u.locked&&' · locked'}</span>},
    {key:'actions',label:'',render:(u:AdminUser)=><div className="flex flex-wrap gap-2 text-xs">
      {u.locked&&<button onClick={()=>run(()=>updateAdminUser(u.id,{unlock:true}),`${u.name} is unlocked.`)} className="rounded border border-line px-2 py-1">Unlock</button>}
      <button onClick={()=>open({kind:'password',u})} className="rounded border border-line px-2 py-1">Reset password</button>
      {u.id!==+me&&<button onClick={()=>u.isActive?open({kind:'toggle',u}):run(()=>updateAdminUser(u.id,{isActive:true}),`${u.name} is enabled again.`)} className="rounded border border-line px-2 py-1">{u.isActive?'Disable':'Enable'}</button>}</div>}]}/>}
  </Card>
  <Modal open={dlg?.kind==='add'} title="Add user" onClose={()=>setDlg(null)}>
   <div className="space-y-3 text-sm">
    <label className="flex flex-col gap-1">Full name<input value={f.name} onChange={e=>setF({...f,name:e.target.value})} className={input}/></label>
    <label className="flex flex-col gap-1">Email<input type="email" value={f.email} onChange={e=>setF({...f,email:e.target.value})} className={input}/></label>
    <label className="flex flex-col gap-1">Starting password (at least 8 characters)<input type="text" value={f.password} onChange={e=>setF({...f,password:e.target.value})} className={input}/></label>
    <label className="flex flex-col gap-1">Role<select value={f.role} onChange={e=>setF({...f,role:e.target.value as Role})} className={input}>{ROLES.map(r=><option key={r.v} value={r.v}>{r.l}</option>)}</select></label>
    {err&&<p role="alert" className="text-crit">{err}</p>}
    <button disabled={act.isPending||!f.name||!f.email||f.password.length<8} onClick={()=>run(()=>createAdminUser(f),`${f.name} was added.`)} className="rounded bg-mn px-3 py-1.5 text-ink disabled:opacity-50">{act.isPending?'Saving...':'Add user'}</button></div></Modal>
  <Modal open={dlg?.kind==='password'} title={dlg?.kind==='password'?`Reset password for ${dlg.u.name}`:''} onClose={()=>setDlg(null)}>
   <div className="space-y-3 text-sm"><p className="text-mute">This signs the user out everywhere and unlocks the account. Share the new password with them yourself.</p>
    <label className="flex flex-col gap-1">New password (at least 8 characters)<input type="text" value={pw} onChange={e=>setPw(e.target.value)} className={input}/></label>
    {err&&<p role="alert" className="text-crit">{err}</p>}
    <button disabled={act.isPending||pw.length<8} onClick={()=>{if(dlg?.kind==='password'){const id=dlg.u.id,name=dlg.u.name;run(()=>resetUserPassword(id,pw),`Password reset for ${name}.`)}}} className="rounded bg-mn px-3 py-1.5 text-ink disabled:opacity-50">Reset password</button></div></Modal>
  <Modal open={dlg?.kind==='toggle'} title={dlg?.kind==='toggle'?`Disable ${dlg.u.name}?`:''} onClose={()=>setDlg(null)}>
   <p className="mb-4 text-sm text-mute">They will be signed out and cannot log in until you enable the account again. Their data and history stay.</p>
   {err&&<p role="alert" className="mb-3 text-sm text-crit">{err}</p>}
   <button disabled={act.isPending} onClick={()=>{if(dlg?.kind==='toggle'){const id=dlg.u.id,name=dlg.u.name;run(()=>updateAdminUser(id,{isActive:false}),`${name} is disabled.`)}}} className="rounded bg-crit px-3 py-1.5 text-sm text-white disabled:opacity-50">Disable account</button></Modal></>}
function Audit(){
 const [page,setPage]=useState(1); const [action,setAction]=useState(''); const [days,setDays]=useState(0)
 const acts=useQuery({queryKey:['audit-actions'],queryFn:getAuditActions})
 const q=useQuery({queryKey:['audit',page,action,days],queryFn:()=>getAuditLogs({page,action,days}),placeholderData:p=>p})
 if(q.isError)return <ErrorState retry={q.refetch}/>
 const d=q.data; const pages=d?Math.max(1,Math.ceil(d.total/d.size)):1
 return <Card title={`Audit log${d?` (${d.total.toLocaleString('en-IN')} entries)`:''}`}>
  <div className="mb-3 flex flex-wrap items-end gap-3 text-sm">
   <label className="flex flex-col gap-1">Action<select value={action} onChange={e=>{setAction(e.target.value);setPage(1)}} className={input}><option value="">All actions</option>{(acts.data??[]).map(a=><option key={a} value={a}>{a}</option>)}</select></label>
   <label className="flex flex-col gap-1">Period<select value={days} onChange={e=>{setDays(+e.target.value);setPage(1)}} className={input}>{([[0,'All time'],[1,'Last 24 hours'],[7,'Last 7 days'],[30,'Last 30 days']] as [number,string][]).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label></div>
  {q.isLoading?<Skeleton className="h-64"/>:<DataTable rows={d?.items??[]} cols={[
   {key:'at',label:'When',render:(a:AuditEntry)=>when(a.at)},
   {key:'user',label:'User',render:(a:AuditEntry)=>a.userEmail?<span title={a.userEmail}>{a.userName??a.userEmail}</span>:<span className="text-mute">Unknown or signed out</span>},
   {key:'action',label:'Action'},
   {key:'detail',label:'Details',render:(a:AuditEntry)=>{const t=Object.entries(a.detail).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):String(v)}`).join(', ');return <span title={t} className="block max-w-md truncate text-mute">{t||'-'}</span>}}]}/>}
  <div className="mt-3 flex items-center justify-between text-sm"><span className="text-mute">Page {page} of {pages}</span>
   <div className="flex gap-2"><button disabled={page<=1} onClick={()=>setPage(page-1)} className="rounded border border-line px-3 py-1 disabled:opacity-50">Previous</button><button disabled={page>=pages} onClick={()=>setPage(page+1)} className="rounded border border-line px-3 py-1 disabled:opacity-50">Next</button></div></div></Card>}
