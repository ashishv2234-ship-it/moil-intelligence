import { Card, EmptyState } from '../components/ui'
export default function Stub({title,note}:{title:string;note:string}){return <><h1 className="text-xl font-semibold">{title}</h1><Card><EmptyState text={note}/></Card></>}
