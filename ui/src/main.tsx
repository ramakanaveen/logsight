import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

// Apply saved theme immediately — before React renders — to avoid flash
const saved = localStorage.getItem('logsight-theme') ?? 'dark'
document.documentElement.classList.toggle('dark', saved === 'dark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
