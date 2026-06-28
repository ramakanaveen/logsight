import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MessageSquare, Settings, Sun, Moon } from 'lucide-react'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import { useThemeStore } from './store'
import './index.css'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })

const LogoIcon = () => (
  <svg width="20" height="20" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="7" fill="#1C1917" />
    <circle cx="13.5" cy="13.5" r="6.5" stroke="#F97316" strokeWidth="2.4" fill="none" />
    <circle cx="11.5" cy="11.5" r="2.2" fill="#FBBF24" fillOpacity="0.35" />
    <line x1="18.5" y1="18.5" x2="26" y2="26" stroke="#F97316" strokeWidth="2.4" strokeLinecap="round" />
  </svg>
)

function Nav() {
  const { theme, toggleTheme } = useThemeStore()

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-orange-50 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400'
        : 'text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800'
    }`

  return (
    <nav className="flex items-center gap-1 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-4 py-2.5 flex-shrink-0">
      <span className="mr-5 flex items-center gap-2">
        <LogoIcon />
        <span className="text-sm font-bold tracking-tight select-none">
          <span className="text-stone-900 dark:text-stone-100">Log</span>
          <span className="text-orange-500">Sight</span>
        </span>
      </span>

      <NavLink to="/chat" className={linkCls}>
        <MessageSquare size={14} /> Chat
      </NavLink>
      <NavLink to="/admin" className={linkCls}>
        <Settings size={14} /> Admin
      </NavLink>

      <button
        onClick={toggleTheme}
        className="ml-auto p-2 rounded-lg text-stone-400 dark:text-stone-500 hover:text-stone-700 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div className="flex flex-col h-screen bg-stone-50 dark:bg-stone-950">
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
