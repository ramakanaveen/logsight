import { useState } from 'react'
import { TopologyView } from '../components/TopologyView'
import { ProcessDefinitions } from '../components/ProcessDefinitions'

type Tab = 'topology' | 'processes'

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('topology')

  return (
    <div className="flex flex-col h-full bg-stone-50 dark:bg-stone-950">
      <header className="border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-6 py-4">
        <h1 className="text-base font-semibold text-stone-900 dark:text-stone-100">Fleet Admin</h1>
        <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
          Manage fleet topology and process definitions
        </p>
      </header>

      <div className="border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-6">
        <nav className="flex gap-6">
          {(['topology', 'processes'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? 'border-orange-500 text-orange-600 dark:text-orange-400'
                  : 'border-transparent text-stone-500 dark:text-stone-400 hover:text-stone-800 dark:hover:text-stone-200 hover:border-stone-300 dark:hover:border-stone-600'
              }`}
            >
              {t === 'topology' ? 'Fleet Topology' : 'Process Definitions'}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {tab === 'topology' && <TopologyView />}
        {tab === 'processes' && <ProcessDefinitions />}
      </div>
    </div>
  )
}
