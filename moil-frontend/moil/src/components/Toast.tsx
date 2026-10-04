import { createContext, useCallback, useContext, useRef, useState, ReactNode } from 'react'
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react'
type Kind='success'|'error'|'warning'|'info'
interface Item{id:number;kind:Kind;text:string}
const Ctx=createContext<(kind:Kind,text:string)=>void>(()=>{})
export const useToast=()=>useContext(Ctx)
const style:Record<Kind,{cls:string;Icon:any}>={success:{cls:'border-ok',Icon:CheckCircle2},error:{cls:'border-crit',Icon:XCircle},warning:{cls:'border-warn',Icon:AlertTriangle},info:{cls:'border-info',Icon:Info}}
export function ToastProvider({children}:{children:ReactNode}){
 const [items,setItems]=useState<Item[]>([]); const n=useRef(0)
 const dismiss=(id:number)=>setItems(l=>l.filter(x=>x.id!==id))
 const push=useCallback((kind:Kind,text:string)=>{const id=++n.current;setItems(l=>[...l.slice(-3),{id,kind,text}]);setTimeout(()=>dismiss(id),kind==='error'?9000:5000)},[])
 return <Ctx.Provider value={push}>{children}
  <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
   {items.map(t=>{const {cls,Icon}=style[t.kind];return <div key={t.id} role={t.kind==='error'?'alert':'status'} className={`pointer-events-auto flex items-start gap-2 rounded-lg border-l-4 border border-line bg-panel p-3 text-sm shadow-lg ${cls}`}>
    <Icon size={18} className="mt-0.5 shrink-0"/><p className="flex-1">{t.text}</p><button aria-label="Dismiss" onClick={()=>dismiss(t.id)}><X size={14}/></button></div>})}</div></Ctx.Provider>}
