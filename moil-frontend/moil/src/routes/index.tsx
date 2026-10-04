import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout from '../layouts/AppLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Actions from '../pages/Actions'
import Reserves from '../pages/Reserves'
import Forecast from '../pages/Forecast'
import Risks from '../pages/Risks'
import Data from '../pages/Data'
import Equipment from '../pages/Equipment'
import Blasting from '../pages/Blasting'
import Reports from '../pages/Reports'
import Settings from '../pages/Settings'
import Stub from '../pages/Stub'
import { useAuth, home } from '../store/auth'
import { pages } from './access'
const Guard=()=>{const u=useAuth(s=>s.user);return u?<AppLayout/>:<Navigate to="/login" replace/>}
const Role=({path,el}:{path:string;el:JSX.Element})=>{const u=useAuth(s=>s.user)!;return pages.find(p=>p.path===path)!.roles.includes(u.role)?el:<Navigate to={home[u.role]} replace/>}
const els:Record<string,JSX.Element>={dashboard:<Dashboard/>,actions:<Actions/>,reserves:<Reserves/>,forecast:<Forecast/>,risks:<Risks/>,data:<Data/>,equipment:<Equipment/>,blasting:<Blasting/>,reports:<Reports/>,settings:<Settings/>}
export const router=createBrowserRouter([{path:'/login',element:<Login/>},
 {element:<Guard/>,children:[{path:'/',element:<Navigate to="/dashboard" replace/>},
  ...pages.map(p=>({path:'/'+p.path,element:<Role path={p.path} el={els[p.path]??<Stub title={p.label} note="This screen is next in the build. Its API function and types are ready."/>}/>}))]}])
