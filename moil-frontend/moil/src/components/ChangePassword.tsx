import { useState } from 'react'
import { Modal } from './ui'
import { changePassword } from '../services/api'
const input='rounded border border-line bg-ink px-3 py-2 text-sm'
const msg=(e:any)=>{const d=e?.response?.data?.detail;return typeof d==='string'?d:Array.isArray(d)?'New password must be at least 8 characters.':'Could not change the password. Check that the backend is running.'}
export default function ChangePassword({open,onClose}:{open:boolean;onClose:()=>void}){
 const [cur,setCur]=useState(''); const [next,setNext]=useState(''); const [again,setAgain]=useState('')
 const [err,setErr]=useState(''); const [done,setDone]=useState(false); const [busy,setBusy]=useState(false)
 const close=()=>{setCur('');setNext('');setAgain('');setErr('');setDone(false);onClose()}
 const submit=async()=>{
  if(next.length<8)return setErr('New password must be at least 8 characters.')
  if(next!==again)return setErr('The two new passwords do not match.')
  setBusy(true);setErr('')
  try{await changePassword(cur,next);setDone(true)}catch(e){setErr(msg(e))}finally{setBusy(false)}}
 return <Modal open={open} title="Change password" onClose={close}>{done?<div className="space-y-3 text-sm"><p className="text-ok">Password changed. Other devices were signed out.</p><button onClick={close} className="rounded bg-mn px-3 py-1.5 text-ink">Close</button></div>:
  <div className="flex flex-col gap-3 text-sm">
   <label className="flex flex-col gap-1">Current password<input type="password" value={cur} onChange={e=>setCur(e.target.value)} className={input} autoComplete="current-password"/></label>
   <label className="flex flex-col gap-1">New password (at least 8 characters)<input type="password" value={next} onChange={e=>setNext(e.target.value)} className={input} autoComplete="new-password"/></label>
   <label className="flex flex-col gap-1">Repeat new password<input type="password" value={again} onChange={e=>setAgain(e.target.value)} className={input} autoComplete="new-password"/></label>
   {err&&<p role="alert" className="text-crit">{err}</p>}
   <button onClick={submit} disabled={busy||!cur||!next} className="self-start rounded bg-mn px-3 py-1.5 font-medium text-ink disabled:opacity-60">{busy?'Saving':'Change password'}</button></div>}</Modal>}
