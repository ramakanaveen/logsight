import { Download, MessageSquare, Plus, Trash2 } from 'lucide-react'
import type { Conversation } from '../types'

interface Props {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onExport?: () => void
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onExport,
}: Props) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 flex flex-col">
      <div className="p-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          History
        </span>
        <div className="flex items-center gap-1">
          {onExport && activeId && (
            <button
              onClick={onExport}
              className="rounded p-1 hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
              title="Export conversation"
            >
              <Download size={14} />
            </button>
          )}
          <button
            onClick={onNew}
            className="rounded p-1 hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
            title="New conversation"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto py-1">
        {conversations.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-gray-400 dark:text-gray-600">
            No conversations yet
          </p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 ${
              c.id === activeId ? 'bg-blue-50 dark:bg-blue-950/30' : ''
            }`}
            onClick={() => onSelect(c.id)}
          >
            <MessageSquare size={13} className="flex-shrink-0 text-gray-400" />
            <span className="flex-1 truncate text-xs text-gray-700 dark:text-gray-300">
              {c.title || 'Untitled'}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(c.id)
              }}
              className="hidden group-hover:flex rounded p-0.5 hover:text-red-500 text-gray-400"
              title="Delete"
            >
              <Trash2 size={11} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  )
}
