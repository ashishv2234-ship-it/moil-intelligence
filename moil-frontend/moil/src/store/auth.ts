import { create } from 'zustand'
import axios from 'axios'
import type { User, Role } from '../types'
const base=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api/v1'
export const home:Record<Role,string>={admin:'/settings',mine_manager:'/dashboard',geologist:'/reserves',planning_engineer:'/forecast',maintenance_engineer:'/equipment',executive:'/dashboard',data_engineer:'/data'}
interface S{user:User|null;theme:'dark'|'light';login:(email:string,password:string)=>Promise<Role>;logout:()=>void;toggleTheme:()=>void}
const saved=localStorage.getItem('user')
export const useAuth=create<S>((set,get)=>({user:saved?JSON.parse(saved):null,theme:'light',
 login:async(email,password)=>{
  const {data}=await axios.post(`${base}/auth/login`,{email,password})
  const me=(await axios.get(`${base}/auth/me`,{headers:{Authorization:`Bearer ${data.access_token}`}})).data
  const user:User={id:String(me.id),name:me.name,email:me.email,role:me.role.toLowerCase() as Role}
  localStorage.setItem('token',data.access_token);localStorage.setItem('refresh',data.refresh_token);localStorage.setItem('user',JSON.stringify(user))
  set({user});return user.role},
 logout:()=>{const rt=localStorage.getItem('refresh');if(rt)axios.post(`${base}/auth/logout`,{refresh_token:rt}).catch(()=>{});localStorage.clear();set({user:null})},
 toggleTheme:()=>{const t=get().theme==='dark'?'light':'dark';document.documentElement.dataset.theme=t;set({theme:t})}}))
