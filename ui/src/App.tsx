import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MessageSquare, Settings } from 'lucide-react'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import './index.css'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })

function Nav() {
  const cls = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
    }`

  return (
    <nav className="flex items-center gap-1 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 px-4 py-2 flex-shrink-0">
      <span className="mr-3 text-sm font-bold text-gray-900 dark:text-gray-100">LogSight</span>
      <NavLink to="/chat" className={cls}>
        <MessageSquare size={14} /> Chat
      </NavLink>
      <NavLink to="/admin" className={cls}>
        <Settings size={14} /> Admin
      </NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div className="flex flex-col h-screen bg-white dark:bg-gray-950">
          <Nav />
          <div className="flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
