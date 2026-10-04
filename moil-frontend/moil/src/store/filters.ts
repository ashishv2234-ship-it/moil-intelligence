import { create } from 'zustand'
export type Days=7|30|90
export interface Range{from:string;to:string}
interface F{mineId:string;days:Days;range:Range|null;setMine:(id:string)=>void;setDays:(d:Days)=>void;setRange:(r:Range)=>void}
// mineId is 'all' or a mine's id. A custom range (when set) replaces the preset days on the pages that use the period.
export const useFilters=create<F>(set=>({mineId:'all',days:30,range:null,setMine:mineId=>set({mineId}),setDays:days=>set({days,range:null}),setRange:range=>set({range})}))
export const isoDay=(offsetDays=0)=>new Date(Date.now()+offsetDays*864e5).toISOString().slice(0,10)
export const periodText=(days:number,range:Range|null)=>range?`${range.from} to ${range.to}`:`last ${days} days`
