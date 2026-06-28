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
    <aside className="w-60 flex-shrink-0 border-r border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900/50 flex flex-col">
      <div className="p-3 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-stone-400 dark:text-stone-500">
          History
        </span>
        <div className="flex items-center gap-1">
          {onExport && activeId && (
            <button
              onClick={onExport}
              className="rounded-md p-1.5 text-stone-400 hover:text-stone-700 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
              title="Export conversation"
            >
              <Download size={13} />
            </button>
          )}
          <button
            onClick={onNew}
            className="rounded-md p-1.5 text-stone-400 hover:text-orange-500 hover:bg-orange-50 dark:hover:bg-orange-950/30 transition-colors"
            title="New conversation"
          >
            <Plus size={13} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto py-1.5">
        {conversations.length === 0 && (
          <div className="px-4 py-8 text-center">
            <MessageSquare size={20} className="mx-auto mb-2 text-stone-300 dark:text-stone-700" />
            <p className="text-xs text-stone-400 dark:text-stone-600">No conversations yet</p>
          </div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center gap-2 px-3 py-2 mx-1.5 rounded-lg cursor-pointer transition-colors ${
              c.id === activeId
                ? 'bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400'
                : 'text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-stone-200'
            }`}
            onClick={() => onSelect(c.id)}
          >
            <MessageSquare
              size={13}
              className={`flex-shrink-0 ${c.id === activeId ? 'text-orange-500' : 'text-stone-400'}`}
            />
            <span className="flex-1 truncate text-xs font-medium">
              {c.title || 'Untitled'}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(c.id)
              }}
              className="hidden group-hover:flex rounded p-0.5 text-stone-400 hover:text-red-500 transition-colors"
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
