import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { router } from './routes'
import { ToastProvider } from './components/Toast'
import './styles/index.css'
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={new QueryClient()}><ToastProvider><RouterProvider router={router}/></ToastProvider></QueryClientProvider></React.StrictMode>)
