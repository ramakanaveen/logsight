import { useState } from 'react'
import { TopologyView } from '../components/TopologyView'
import { ProcessDefinitions } from '../components/ProcessDefinitions'

type Tab = 'topology' | 'processes'

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('topology')

  return (
    <div className="flex flex-col h-full">
      <header className="border-b border-gray-200 dark:border-gray-800 px-6 py-3">
        <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Admin</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">Manage fleet topology and process definitions</p>
      </header>

      <div className="border-b border-gray-200 dark:border-gray-800 px-6">
        <nav className="flex gap-4">
          {(['topology', 'processes'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
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
