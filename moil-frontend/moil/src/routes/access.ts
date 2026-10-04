import type { Role } from '../types'
const all:Role[]=['admin','mine_manager','geologist','planning_engineer','maintenance_engineer','executive','data_engineer']
export const pages:{path:string;label:string;roles:Role[]}[]=[
 {path:'dashboard',label:'Control tower',roles:['admin','mine_manager','executive','planning_engineer','data_engineer']},
 {path:'reserves',label:'Reserve intelligence',roles:['admin','geologist','executive']},
 {path:'forecast',label:'Production forecast',roles:['admin','mine_manager','planning_engineer','executive']},
 {path:'risks',label:'Shortfall risk',roles:['admin','mine_manager','planning_engineer','executive']},
 {path:'equipment',label:'Equipment',roles:['admin','mine_manager','maintenance_engineer']},
 {path:'blasting',label:'Blasting',roles:['admin','mine_manager']},
 {path:'actions',label:'Corrective actions',roles:['admin','mine_manager','planning_engineer']},
 {path:'data',label:'Data quality',roles:['admin','geologist','data_engineer']},
 {path:'reports',label:'Reports',roles:all},
 {path:'settings',label:'Administration',roles:['admin']}]
export const navItems=(r:Role)=>pages.filter(p=>p.roles.includes(r))
