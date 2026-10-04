import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCorrectiveActions, updateCorrectiveActionStatus, getAssignableUsers, assignAction, getActionComments, addActionComment, errText } from '../services/api'
import { useAuth } from '../store/auth'
import { Card, Modal, AiLabel, StatusBadge, Skeleton } from '../components/ui'
import { useToast } from '../components/Toast'
import type { CorrectiveAction } from '../types'
const TITLE:Record<string,string>={Approved:'Approve this action?',Rejected:'Reject this action?','In Progress':'Start work on this action?',Completed:'Mark this action as completed?'}
const when=(s:string)=>new Date(s.endsWith('Z')?s:s+'Z').toLocaleString('en-IN')
function Comments({id,canPost}:{id:string;canPost:boolean}){
 const qc=useQueryClient(); const toast=useToast(); const q=useQuery({queryKey:['comments',id],queryFn:()=>getActionComments(id)}); const [text,setText]=useState('')
 const add=useMutation({mutationFn:()=>addActionComment(id,text.trim()),onSuccess:()=>{setText('');qc.invalidateQueries({queryKey:['comments',id]})},onError:(e:any)=>toast('error',errText(e,'Could not save the comment.'))})
 return <div className="mt-3 space-y-2 border-t border-line pt-3">
  {q.isLoading?<Skeleton className="h-10"/>:q.isError?<p className="text-sm text-crit">Could not load comments.</p>:!q.data!.length?<p className="text-sm text-mute">No comments yet.</p>:
   <ul className="space-y-2">{q.data!.map(c=><li key={c.id} className="text-sm"><span className="font-medium">{c.author}</span>{c.role&&<span className="text-xs text-mute"> · {c.role.toLowerCase().replace(/_/g,' ')}</span>}<span className="text-xs text-mute"> · {when(c.createdAt)}</span><p className="whitespace-pre-wrap">{c.text}</p></li>)}</ul>}
  {canPost?<div className="flex flex-wrap items-start gap-2"><textarea aria-label="New comment" value={text} maxLength={500} rows={2} onChange={e=>setText(e.target.value)} placeholder="Add a note (up to 500 characters)" className="min-w-60 flex-1 rounded border border-line bg-ink px-2 py-1.5 text-sm"/>
   <button disabled={!text.trim()||add.isPending} onClick={()=>add.mutate()} className="rounded bg-mn px-3 py-1.5 text-sm text-ink disabled:opacity-40">{add.isPending?'Saving…':'Add comment'}</button></div>
  :<p className="text-xs text-mute">Your role can read comments but not add them.</p>}</div>}
export default function Actions(){
 const qc=useQueryClient(); const toast=useToast(); const {data,isLoading}=useQuery({queryKey:['actions'],queryFn:getCorrectiveActions})
 const role=useAuth(s=>s.user!.role); const canAssign=['admin','mine_manager'].includes(role); const canMove=['admin','mine_manager','planning_engineer'].includes(role); const canPost=['admin','mine_manager','planning_engineer','maintenance_engineer'].includes(role)
 const users=useQuery({queryKey:['assignable'],queryFn:getAssignableUsers,enabled:canAssign,retry:false}); const [open,setOpen]=useState<string|null>(null); const [assigning,setAssigning]=useState<string|null>(null); const [pick,setPick]=useState('')
 const asg=useMutation({mutationFn:(p:{id:string;owner:string})=>assignAction(p.id,p.owner),onSuccess:()=>{qc.invalidateQueries({queryKey:['actions']});setAssigning(null);toast('success','Owner saved.')},onError:(e:any)=>toast('error',errText(e,'Could not save the owner.'))})
 const [local,setLocal]=useState<Record<string,CorrectiveAction['status']>>({}); const [pending,setPending]=useState<{a:CorrectiveAction;to:CorrectiveAction['status']}|null>(null)
 const m=useMutation({mutationFn:(p:{id:string;s:CorrectiveAction['status']})=>updateCorrectiveActionStatus(p.id,p.s),onSuccess:(_,p)=>{setLocal(l=>({...l,[p.id]:p.s}));qc.invalidateQueries({queryKey:['actions']});toast('success',`${p.s}: ${pending?.a.title??'action'}`);setPending(null)},onError:(e:any)=>{setPending(null);toast('error',e.response?.data?.detail||'Could not update this action.')}})
 return <><h1 className="text-xl font-semibold">Corrective actions</h1>
 {isLoading?<Skeleton className="h-40"/>:data!.map(a=>{const s=local[a.id]??a.status;return <Card key={a.id}><div className="flex flex-wrap items-center gap-3">
  <div className="min-w-60 flex-1"><p className="font-medium">{a.title}</p><AiLabel confidence={a.confidence}/>
   <p className="mt-1 text-sm text-mute">Recovers {a.recoveryT.toLocaleString('en-IN')} tonnes · ₹{a.costInrLakh} lakh · {a.feasibility} feasibility · {a.owner} · due {a.deadline}</p></div>
  <StatusBadge s={s}/>{s==='Proposed'&&<><button onClick={()=>setPending({a,to:'Approved'})} className="rounded bg-mn px-3 py-1 text-sm text-ink">Approve</button><button onClick={()=>setPending({a,to:'Rejected'})} className="rounded border border-line px-3 py-1 text-sm">Reject</button></>}{canMove&&s==='Approved'&&<button onClick={()=>setPending({a,to:'In Progress'})} className="rounded bg-mn px-3 py-1 text-sm text-ink">Start work</button>}{canMove&&s==='In Progress'&&<button onClick={()=>setPending({a,to:'Completed'})} className="rounded bg-mn px-3 py-1 text-sm text-ink">Mark completed</button>}</div>
  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
   {canAssign&&(assigning===a.id?<span className="flex flex-wrap items-center gap-2"><select aria-label="Owner" value={pick} onChange={e=>setPick(e.target.value)} className="rounded border border-line bg-panel px-2 py-1 text-sm"><option value="">{users.isLoading?'Loading…':users.isError?'Could not load people':'Choose a person'}</option>{(users.data??[]).map(u=><option key={u.id} value={u.name}>{u.name} · {u.role.toLowerCase().replace(/_/g,' ')}</option>)}</select>
    <button disabled={!pick||asg.isPending} onClick={()=>asg.mutate({id:a.id,owner:pick})} className="rounded bg-mn px-3 py-1 text-ink disabled:opacity-40">Save</button><button onClick={()=>setAssigning(null)} className="text-mute underline">Cancel</button></span>
    :<button onClick={()=>{setAssigning(a.id);setPick('')}} className="text-mn underline">{a.owner==='Unassigned'?'Assign owner':'Change owner'}</button>)}
   <button onClick={()=>setOpen(open===a.id?null:a.id)} className="text-mn underline">{open===a.id?'Hide comments':'Comments'}</button></div>
  {open===a.id&&<Comments id={a.id} canPost={canPost}/>}</Card>})}
 <Modal open={!!pending} title={pending?TITLE[pending.to]??'Update this action?':''} onClose={()=>setPending(null)}>
  <p className="mb-4 text-sm text-mute">{pending?.a.title}. The status change is logged. No notification is sent.</p>
  <button onClick={()=>m.mutate({id:pending!.a.id,s:pending!.to})} className="rounded bg-mn px-3 py-1.5 text-sm text-ink">Confirm</button></Modal></>}
