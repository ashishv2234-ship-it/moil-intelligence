import { ReactNode } from 'react'
import { AlertTriangle, Inbox, X } from 'lucide-react'
import type { Severity } from '../types'
const sev:Record<Severity,string>={Low:'bg-ok/15 text-ok',Medium:'bg-warn/15 text-warn',High:'bg-high/15 text-high',Critical:'bg-crit/15 text-crit'}
export const RiskBadge=({level}:{level:Severity})=><span className={`rounded px-2 py-0.5 text-xs font-medium ${sev[level]}`}>{level}</span>
const st:Record<string,string>={Success:'bg-ok/15 text-ok',Running:'bg-ok/15 text-ok',Warning:'bg-warn/15 text-warn',Idle:'bg-info/15 text-info',Failed:'bg-crit/15 text-crit',Breakdown:'bg-crit/15 text-crit',Maintenance:'bg-high/15 text-high'}
export const StatusBadge=({s}:{s:string})=><span className={`rounded px-2 py-0.5 text-xs font-medium ${st[s]??'bg-mute/20 text-mute'}`}>{s}</span>
export const AiLabel=({confidence}:{confidence:number})=><span className="text-xs text-mn">AI-generated recommendation · {confidence}% confidence</span>
export const Skeleton=({className=''}:{className?:string})=><div className={`animate-pulse rounded bg-line ${className}`}/>
export const Card=({title,children,right}:{title?:string;children:ReactNode;right?:ReactNode})=>
 <section className="rounded-lg border border-line bg-panel p-4">{title&&<header className="-mx-4 -mt-4 mb-3 flex items-center justify-between border-b border-line bg-ink/70 px-4 py-2"><h2 className="text-[13px] font-semibold uppercase tracking-wide text-mute">{title}</h2>{right}</header>}{children}</section>
export const KpiCard=({label,value,unit,delta,loading}:{label:string;value:string;unit?:string;delta?:number;loading?:boolean})=>
 <Card>{loading?<Skeleton className="h-14"/>:<><p className="text-xs text-mute">{label}</p><p className="mt-1 text-2xl font-semibold tabular-nums">{value} <span className="text-sm font-normal text-mute">{unit}</span></p>
 {delta!==undefined&&<p className={`mt-1 text-xs ${delta>=0?'text-ok':'text-crit'}`}>{delta>=0?'Surplus':'Shortfall'} {Math.abs(delta)}% vs plan</p>}</>}</Card>
export const EmptyState=({text}:{text:string})=><div className="flex flex-col items-center gap-2 py-10 text-mute"><Inbox/><p className="text-sm">{text}</p></div>
export const ErrorState=({retry}:{retry?:()=>void})=><div className="flex flex-col items-center gap-2 py-10 text-crit"><AlertTriangle/><p className="text-sm">Couldn't load this data. Check your connection and try again.</p>{retry&&<button onClick={retry} className="rounded border border-line px-3 py-1 text-fg">Retry</button>}</div>
export const Modal=({open,title,children,onClose}:{open:boolean;title:string;children:ReactNode;onClose:()=>void})=>!open?null:
 <div role="dialog" aria-modal className="fixed inset-0 z-50 grid place-items-center bg-black/50"><div className="w-full max-w-md rounded-lg border border-line bg-panel p-5">
 <div className="mb-3 flex justify-between"><h3 className="font-semibold">{title}</h3><button aria-label="Close" onClick={onClose}><X size={16}/></button></div>{children}</div></div>
export function DataTable<T extends Record<string,any>>({cols,rows}:{cols:{key:string;label:string;render?:(r:T)=>ReactNode}[];rows:T[]}){
 if(!rows.length)return <EmptyState text="No records match these filters."/>
 return <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-ink text-[11px] uppercase tracking-wide text-mute"><tr>{cols.map(c=><th key={c.key} className="px-3 py-2 font-medium">{c.label}</th>)}</tr></thead>
 <tbody>{rows.map((r,i)=><tr key={i} className="border-t border-line hover:bg-ink/60">{cols.map(c=><td key={c.key} className="px-3 py-2 tabular-nums">{c.render?c.render(r):r[c.key]}</td>)}</tr>)}</tbody></table></div>}
