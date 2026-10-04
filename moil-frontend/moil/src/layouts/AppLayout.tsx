import { NavLink, Outlet } from 'react-router-dom'
import { useState } from 'react'
import { LayoutDashboard, Map, TrendingUp, ShieldAlert, Truck, Bomb, ListChecks, Database, FileText, Settings, Menu, Sun, LogOut, KeyRound } from 'lucide-react'
import { useAuth } from '../store/auth'
import { navItems } from '../routes/access'
import { useQuery } from '@tanstack/react-query'
import { getMines } from '../services/api'
import { useFilters, isoDay } from '../store/filters'
import ChangePassword from '../components/ChangePassword'
const icons:Record<string,any>={dashboard:LayoutDashboard,reserves:Map,forecast:TrendingUp,risks:ShieldAlert,equipment:Truck,blasting:Bomb,actions:ListChecks,data:Database,reports:FileText,settings:Settings}
export default function AppLayout(){
 const {user,logout,toggleTheme}=useAuth(); const [open,setOpen]=useState(true); const [pw,setPw]=useState(false); const {mineId,days,range,setMine,setDays,setRange}=useFilters(); const [draft,setDraft]=useState({from:'',to:''}); const [rerr,setRerr]=useState(''); const mines=useQuery({queryKey:['mines'],queryFn:getMines})
 const apply=(r:{from:string;to:string})=>{setDraft(r); if(!r.from||!r.to){setRerr('');return}; if(r.from>r.to){setRerr('The from date must be on or before the to date.');return}; if((Date.parse(r.to)-Date.parse(r.from))/864e5+1>366){setRerr('Choose 366 days or fewer.');return}; setRerr(''); setRange(r)}
 return <div className="flex min-h-screen">
  <aside className={`${open?'w-56':'w-14'} shrink-0 bg-[#1F2A33] text-slate-300 transition-[width]`}>
   <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3"><button aria-label="Toggle menu" onClick={()=>setOpen(!open)}><Menu size={18}/></button>{open&&<div className="leading-tight"><p className="text-sm font-semibold text-white">MOIL Limited</p><p className="text-[11px] text-slate-400">Mining Intelligence System</p></div>}</div>
   <nav className="mt-2 flex flex-col">{navItems(user!.role).map(n=>{const I=icons[n.path];return <NavLink key={n.path} to={'/'+n.path} className={({isActive})=>`flex items-center gap-3 border-l-2 px-4 py-2 text-sm ${isActive?'border-[#6FA8DC] bg-white/10 text-white':'border-transparent text-slate-300 hover:bg-white/5 hover:text-white'}`}><I size={18}/>{open&&n.label}</NavLink>})}</nav>
  </aside>
  <div className="flex min-w-0 flex-1 flex-col">
   <header className="flex items-center gap-3 border-b border-line bg-panel px-6 py-3">
    <input aria-label="Search" placeholder="Search mines, equipment, zones" className="w-64 rounded border border-line bg-ink px-3 py-1.5 text-sm"/>
    <select aria-label="Mine" value={mineId} onChange={e=>setMine(e.target.value)} className="rounded border border-line bg-ink px-2 py-1.5 text-sm"><option value="all">All mines</option>{mines.data?.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select>
    <select aria-label="Period" value={range?'custom':days} onChange={e=>{const v=e.target.value; setRerr(''); if(v==='custom'){const r={from:isoDay(-29),to:isoDay(0)}; setDraft(r); setRange(r)} else setDays(+v as 7|30|90)}} className="rounded border border-line bg-ink px-2 py-1.5 text-sm">{[7,30,90].map(d=><option key={d} value={d}>Last {d} days</option>)}<option value="custom">Custom range</option></select>
    {range&&<><input type="date" aria-label="From date" value={draft.from} max={isoDay(0)} onChange={e=>apply({...draft,from:e.target.value})} className="rounded border border-line bg-ink px-2 py-1.5 text-sm"/><span className="text-sm text-mute">to</span><input type="date" aria-label="To date" value={draft.to} max={isoDay(0)} onChange={e=>apply({...draft,to:e.target.value})} className="rounded border border-line bg-ink px-2 py-1.5 text-sm"/>{rerr&&<span role="alert" className="text-xs text-crit">{rerr}</span>}</>}
    <span className="ml-auto text-sm text-mute">{user!.name} · {user!.role.replace('_',' ')}</span>
    <button aria-label="Change password" title="Change password" onClick={()=>setPw(true)}><KeyRound size={18}/></button><button aria-label="Toggle theme" onClick={toggleTheme}><Sun size={18}/></button><button aria-label="Log out" onClick={logout}><LogOut size={18}/></button>
   </header>
   <main className="flex-1 space-y-4 p-5"><Outlet/></main></div><ChangePassword open={pw} onClose={()=>setPw(false)}/></div>}
