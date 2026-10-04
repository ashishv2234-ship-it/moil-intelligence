import { useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Rectangle, Polygon, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getReserveProspectivity, getDrillHoles, runProspectivityModel, recommendDrilling, getSatelliteLayer, getSatelliteSummary, syncSatellite, uploadSatelliteCsv } from '../services/api'
import { useAuth } from '../store/auth'
import { mines, mineBoundaries, lineaments } from '../lib/mock'
import { Card, Modal, Skeleton, ErrorState, EmptyState, AiLabel } from '../components/ui'
import type { ReserveZone } from '../types'
const BASES={street:{url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',attr:'© OpenStreetMap contributors'},
 satellite:{url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',attr:'Imagery © Esri'}}
const scale=[{min:75,color:'#C8481A',label:'75–100%'},{min:50,color:'#E8963A',label:'50–74%'},{min:25,color:'#E9C46A',label:'25–49%'},{min:0,color:'#B9C0C7',label:'0–24%'}]
const colorOf=(p:number)=>scale.find(s=>p>=s.min)!.color
type Indicator='ndvi'|'soil'|'lst'|'rain'
const LAYERS:Record<Indicator,{label:string;unit:string;from:string;to:string;dp:number}>={
 ndvi:{label:'NDVI (vegetation)',unit:'',from:'#7a5a2e',to:'#2ea84f',dp:2},
 soil:{label:'Soil moisture',unit:'%',from:'#e9d9a6',to:'#2563b8',dp:0},
 lst:{label:'Surface temperature',unit:'°C',from:'#3b82f6',to:'#e5534b',dp:0},
 rain:{label:'Rainfall (last 30 days)',unit:'mm',from:'#dbeafe',to:'#1F4E79',dp:0}}
const f=(n:number)=>n.toLocaleString('en-IN')
const hex=(h:string)=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16))
const mix=(a:string,b:string,t:number)=>{const x=hex(a),y=hex(b);return '#'+x.map((v,i)=>Math.round(v+(y[i]-v)*t).toString(16).padStart(2,'0')).join('')}
const holeColor=(mn:number)=>mn>=35?'#1F4E79':mn>=20?'#5C9BD1':'#8A949E'
type Cell={b:[[number,number],[number,number]];c:string;v:number}
export default function Reserves(){
 const {data,isLoading,isError,refetch}=useQuery({queryKey:['reserves'],queryFn:getReserveProspectivity})
 const qc=useQueryClient(); const canEdit=['admin','geologist'].includes(useAuth(s=>s.user!.role)); const [busy,setBusy]=useState(false); const [err,setErr]=useState('')
 const run=async()=>{setBusy(true);setErr('');try{await runProspectivityModel();await qc.invalidateQueries({queryKey:['reserves']})}catch(e:any){setErr(e.response?.data?.detail??'Could not run the model. Check the backend window for the error.')}finally{setBusy(false)}}
 const confirmDrill=async()=>{if(!sel)return;setErr('')
  try{await recommendDrilling(sel.id);await qc.invalidateQueries({queryKey:['reserves']})}catch(e:any){if(e.response)setErr(e.response.data?.detail??'Could not save the recommendation.');else setDrill(new Set(drill).add(sel.id))}
  setAsking(false)}
 const [base,setBase]=useState<'street'|'satellite'>('satellite')
 const [showZones,setShowZones]=useState(true); const [showMines,setShowMines]=useState(true)
 const [minProb,setMinProb]=useState(0); const [minGrade,setMinGrade]=useState(0); const [conf,setConf]=useState('All')
 const [selId,setSelId]=useState<string|null>(null)
 const [showHoles,setShowHoles]=useState(true); const [showBounds,setShowBounds]=useState(true); const [showLin,setShowLin]=useState(false); const [layer,setLayer]=useState<'none'|Indicator>('none')
 const holes=useQuery({queryKey:['holes'],queryFn:getDrillHoles})
 const sat=useQuery({queryKey:['satellite',layer],queryFn:()=>getSatelliteLayer(layer),enabled:layer!=='none',retry:false})
 const satSum=useQuery({queryKey:['satsum'],queryFn:getSatelliteSummary,retry:false})
 const [satBusy,setSatBusy]=useState(false); const [satMsg,setSatMsg]=useState(''); const fileRef=useRef<HTMLInputElement>(null)
 const refreshSat=()=>{qc.invalidateQueries({queryKey:['satellite']});qc.invalidateQueries({queryKey:['satsum']});qc.invalidateQueries({queryKey:['sources']})}
 const syncSat=async()=>{setSatBusy(true);setSatMsg('');try{const r=await syncSatellite();setSatMsg(`Updated rainfall, soil moisture and temperature (${r.cells} cells).`);refreshSat()}catch(e:any){setSatMsg(e.response?.data?.detail??'Could not update the layers.')}finally{setSatBusy(false)}}
 const uploadSat=async(file?:File)=>{if(!file)return;setSatBusy(true);setSatMsg('');try{const r=await uploadSatelliteCsv(file);setSatMsg(`Imported ${r.imported} cells (${r.indicators.join(', ')}).${r.rejected?` ${r.rejected} rows rejected, first: row ${r.issues[0]?.row}: ${r.issues[0]?.message}`:''}`);refreshSat()}catch(e:any){setSatMsg(e.response?.data?.detail??'Could not read the file.')}finally{setSatBusy(false);if(fileRef.current)fileRef.current.value=''}}
 const cells=useMemo<Cell[]>(()=>{if(layer==='none'||!sat.data?.cells.length)return[];const I=LAYERS[layer];const h=sat.data.cellDeg/2;const span=sat.data.max-sat.data.min
  return sat.data.cells.map(c=>({b:[[c.lat-h,c.lng-h],[c.lat+h,c.lng+h]] as [[number,number],[number,number]],c:mix(I.from,I.to,span>0?(c.value-sat.data!.min)/span:.5),v:c.value}))},[layer,sat.data])
 const [drill,setDrill]=useState<Set<string>>(new Set()); const [asking,setAsking]=useState(false)
 const zones=useMemo(()=>(data??[]).filter(z=>z.probability>=minProb&&z.gradeMnPct>=minGrade&&(conf==='All'||z.confidence===conf)),[data,minProb,minGrade,conf])
 const sel=(data??[]).find(z=>z.id===selId)
 const exportCsv=()=>{
  const rows=[['zone','lat','lng','probability_pct','tonnage_t','grade_mn_pct','confidence','recommended_for_drilling'],...zones.map(z=>[z.id,z.lat.toFixed(4),z.lng.toFixed(4),z.probability,z.tonnage,z.gradeMnPct,z.confidence,(z.drillRecommended||drill.has(z.id))?'yes':'no'])]
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([rows.map(r=>r.join(',')).join('\n')],{type:'text/csv'}));a.download='reserve-zones.csv';a.click()}
 if(isError)return <ErrorState retry={refetch}/>
 return <>
  <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-xl font-semibold">Reserve intelligence</h1>
   <div className="flex flex-wrap items-center gap-3"><p className="text-sm text-mute">{zones.length} zones shown · {f(zones.reduce((a,z)=>a+z.tonnage,0))} tonnes indicative potential · {zones.filter(z=>z.probability>=75).length} high-probability{data?.[0]?.modelVersion&&` · model ${data[0].modelVersion}`}{data?.[0]?.runAt&&` · run ${new Date(data[0].runAt).toLocaleDateString('en-IN')}`}</p>
    {canEdit&&<button onClick={run} disabled={busy} className="rounded border border-line px-3 py-1 text-sm disabled:opacity-50">{busy?'Running...':'Re-run model'}</button>}</div></div>
  {err&&<p role="alert" className="text-sm text-crit">{err}</p>}
  {!isLoading&&!(data??[]).length&&<Card><EmptyState text="The prospectivity model has not been run yet, or there are no drill holes."/>{canEdit&&<button onClick={run} disabled={busy} className="mx-auto block rounded bg-mn px-3 py-1.5 text-sm text-ink disabled:opacity-50">{busy?'Running...':'Run prospectivity model'}</button>}</Card>}
  <Card><div className="flex flex-wrap items-end gap-4 text-sm">
   <label className="flex flex-col gap-1">Minimum probability: {minProb}%<input type="range" min={0} max={100} step={5} value={minProb} onChange={e=>setMinProb(+e.target.value)}/></label>
   <label className="flex flex-col gap-1">Minimum grade: {minGrade}% Mn<input type="range" min={0} max={50} step={2} value={minGrade} onChange={e=>setMinGrade(+e.target.value)}/></label>
   <label className="flex flex-col gap-1">Confidence<select value={conf} onChange={e=>setConf(e.target.value)} className="rounded border border-line bg-ink px-2 py-1">{['All','High','Medium','Low'].map(c=><option key={c}>{c}</option>)}</select></label>
   <label className="flex items-center gap-1"><input type="checkbox" checked={showZones} onChange={e=>setShowZones(e.target.checked)}/>Prospect zones</label>
   <label className="flex items-center gap-1"><input type="checkbox" checked={showMines} onChange={e=>setShowMines(e.target.checked)}/>Mines</label>
   <label className="flex items-center gap-1"><input type="checkbox" checked={showBounds} onChange={e=>setShowBounds(e.target.checked)}/>Mine boundaries</label>
   <label className="flex items-center gap-1"><input type="checkbox" checked={showHoles} onChange={e=>setShowHoles(e.target.checked)}/>Drill holes</label>
   <label className="flex items-center gap-1"><input type="checkbox" checked={showLin} onChange={e=>setShowLin(e.target.checked)}/>Lineaments</label>
   <label className="flex flex-col gap-1">Satellite layer<select value={layer} onChange={e=>setLayer(e.target.value as any)} className="rounded border border-line bg-ink px-2 py-1"><option value="none">None</option>{(Object.keys(LAYERS) as Indicator[]).map(k=>{const n=satSum.data?.find(x=>x.indicator===k)?.count;return <option key={k} value={k}>{LAYERS[k].label}{n===0?' (no data yet)':''}</option>})}</select></label>
   <label className="flex items-center gap-1">Base map<select value={base} onChange={e=>setBase(e.target.value as any)} className="rounded border border-line bg-ink px-2 py-1"><option value="satellite">Satellite</option><option value="street">Street</option></select></label>
   <button onClick={exportCsv} disabled={!zones.length} className="ml-auto rounded border border-line px-3 py-1 disabled:opacity-50">Export zones (CSV)</button></div></Card>
  <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
   <div className="isolate self-start overflow-hidden rounded-lg border border-line">{isLoading?<Skeleton className="h-[65vh]"/>:
    <MapContainer center={[21.5,79.7]} zoom={8} className="h-[65vh] w-full">
     <TileLayer key={base} url={BASES[base].url} attribution={BASES[base].attr}/>
     {cells.map((c,i)=><Rectangle key={i} bounds={c.b} pathOptions={{stroke:false,fillColor:c.c,fillOpacity:.45}}><Tooltip sticky>{LAYERS[layer as Indicator].label}: {c.v.toFixed(LAYERS[layer as Indicator].dp)} {LAYERS[layer as Indicator].unit}</Tooltip></Rectangle>)}
     {showBounds&&mineBoundaries.map(b=><Polygon key={b.id} positions={b.pts} pathOptions={{color:'#3FB58A',weight:2,fillOpacity:.1}}><Tooltip sticky>{b.name} lease boundary</Tooltip></Polygon>)}
     {showLin&&lineaments.map((l,i)=><Polyline key={i} positions={l} pathOptions={{color:'#E5C04B',weight:2,dashArray:'6 4'}}><Tooltip sticky>Lineament L{i+1}</Tooltip></Polyline>)}
     {showZones&&zones.map(z=><CircleMarker key={z.id} center={[z.lat,z.lng]} radius={5+z.tonnage/150000} eventHandlers={{click:()=>setSelId(z.id)}}
       pathOptions={{color:z.id===selId?'#fff':colorOf(z.probability),fillColor:colorOf(z.probability),fillOpacity:.75,weight:z.id===selId?3:1}}>
       <Tooltip>{z.id}: {z.probability}% probability</Tooltip></CircleMarker>)}
     {showHoles&&(holes.data??[]).map(h=><CircleMarker key={h.id} center={[h.lat,h.lng]} radius={4} pathOptions={{color:'#FFFFFF',weight:1,fillColor:holeColor(h.mnPct),fillOpacity:1}}><Tooltip>{h.id}: {h.mnPct}% Mn, {h.depthM} m deep</Tooltip></CircleMarker>)}
     {showMines&&mines.map(m=><CircleMarker key={m.id} center={[m.lat,m.lng]} radius={7} pathOptions={{color:'#3FB58A',fillColor:'#1F2A33',fillOpacity:1,weight:3}}><Tooltip>{m.name} mine</Tooltip></CircleMarker>)}
    </MapContainer>}</div>
   <div className="space-y-4">
    <Card title="Zone details">{!sel?<EmptyState text="Select a zone on the map to see its details."/>:<div className="space-y-2 text-sm">
     <p className="text-base font-semibold">{sel.id.toUpperCase()}</p>
     <p>Prospect probability: <b>{sel.probability}%</b></p><p>Estimated reserve: <b>{f(sel.tonnage)} tonnes</b></p>
     <p>Estimated grade: <b>{sel.gradeMnPct}% Mn</b></p><p>Confidence: <b>{sel.confidence}{sel.confidencePct!==undefined&&` (${sel.confidencePct}%)`}</b></p>
     {sel.holesNearby!==undefined&&<p>Drill holes within 15 km: <b>{sel.holesNearby}</b></p>}
     {sel.drillSuggested&&<p className="text-warn">The model suggests drilling here: high probability but few holes nearby.</p>}
     <p>Location: {sel.lat.toFixed(3)}°N, {sel.lng.toFixed(3)}°E</p>
     {sel.confidencePct!==undefined?<AiLabel confidence={sel.confidencePct}/>:<p className="text-xs text-mn">AI-generated estimate. Verify with drilling before planning.</p>}
     <p className="text-xs text-mute">Indicative potential, not a certified resource estimate. Verify with drilling before planning.</p>
     {(sel.drillRecommended||drill.has(sel.id))?<p className="rounded bg-ok/15 px-3 py-2 text-ok">Recommended for drilling</p>:!canEdit?null:<button onClick={()=>setAsking(true)} className="w-full rounded bg-mn py-2 font-medium text-ink">Recommend for drilling</button>}</div>}</Card>
    <Card title="Prospect probability">{scale.map(s=><p key={s.label} className="flex items-center gap-2 text-sm"><span className="h-3 w-3 rounded-full" style={{background:s.color}}/>{s.label}</p>)}
     <p className="mt-2 text-xs text-mute">Circle size shows estimated tonnage. Green rings are existing mines.</p></Card>
    <Card title="Map layers">
     <p className="text-sm font-medium">Drill holes (Mn grade)</p>
     {[['#1F4E79','35% or more'],['#5C9BD1','20 to 35%'],['#8A949E','below 20%']].map(([c,l])=><p key={l} className="flex items-center gap-2 text-sm"><span className="h-3 w-3 rounded-full" style={{background:c}}/>{l}</p>)}
     {layer!=='none'&&<div className="mt-3"><p className="text-sm font-medium">{LAYERS[layer].label}</p>
      {sat.isLoading?<Skeleton className="h-8"/>:sat.isError?<p className="text-xs text-crit">Could not load this layer.</p>:!sat.data?.cells.length?<p className="text-xs text-mute">No data for this layer yet.{canEdit?' Use "Update layers" or upload a CSV below.':''}</p>:<>
       <div className="mt-1 h-3 rounded" style={{background:`linear-gradient(to right,${LAYERS[layer].from},${LAYERS[layer].to})`}}/>
       <div className="flex justify-between text-xs text-mute"><span>{sat.data.min.toFixed(LAYERS[layer].dp)}{LAYERS[layer].unit}</span><span>{sat.data.max.toFixed(LAYERS[layer].dp)}{LAYERS[layer].unit}</span></div>
       <p className="mt-1 text-xs text-mute">{sat.data.source} · data for {sat.data.observedOn?new Date(sat.data.observedOn).toLocaleDateString('en-IN'):'unknown date'} · {sat.data.cells.length} cells. Colours are stretched between this layer's lowest and highest value.</p></>}</div>}
     {canEdit&&<div className="mt-3 space-y-2 border-t border-line pt-3"><p className="text-sm font-medium">Satellite data</p>
      <button onClick={syncSat} disabled={satBusy} className="w-full rounded border border-line px-3 py-1 text-sm disabled:opacity-50">{satBusy?'Working...':'Update layers (rain, soil, temperature)'}</button>
      <label className="block text-xs text-mute">Upload a layer CSV (for example NDVI)<input ref={fileRef} type="file" accept=".csv" disabled={satBusy} onChange={e=>uploadSat(e.target.files?.[0])} className="mt-1 block w-full text-xs"/></label>
      {satMsg&&<p role="status" className="text-xs">{satMsg}</p>}</div>}
     <p className="mt-3 text-xs text-warn">Prospect zones come from the backend model, which uses the drill holes and mine locations in the database. The drill holes are synthetic demo data. Lease boundaries and lineaments are illustrative only. Rainfall, soil moisture and temperature layers come from Open-Meteo model data, not raw satellite images. NDVI comes from uploaded files. None of these layers feed the prospectivity model yet.</p></Card>
</div></div>
  <Modal open={asking} title="Recommend this zone for drilling?" onClose={()=>setAsking(false)}>
   <p className="mb-4 text-sm text-mute">{sel&&`${sel.id.toUpperCase()} (${sel.probability}% probability, ${f(sel.tonnage)} tonnes) will be marked for the exploration team.`}</p>
   <button onClick={confirmDrill} className="rounded bg-mn px-3 py-1.5 text-sm text-ink">Confirm</button></Modal></>}
