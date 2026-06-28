import { useState, useRef } from 'react'
import { Send } from 'lucide-react'
import type { ProcessDefinition } from '../types'

interface Props {
  processes: ProcessDefinition[]
  onSend: (question: string, processHint?: string | null) => void
  disabled?: boolean
}

export function CommandInput({ processes, onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const [selectedHint, setSelectedHint] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Derived — no state/effect needed; re-computes on value change without side effects
  const slashMatch = value.match(/^\/(\S*)/)
  const suggestions = slashMatch
    ? processes.filter((p) => p.name.toLowerCase().includes(slashMatch[1].toLowerCase()))
    : []

  const pickSuggestion = (p: ProcessDefinition) => {
    setSelectedHint(p.name)
    setValue(value.replace(/^\/\S*\s*/, ''))
    inputRef.current?.focus()
  }

  const submit = () => {
    const q = value.trim()
    if (!q || disabled) return
    onSend(q, selectedHint)
    setValue('')
    setSelectedHint(null)
  }

  return (
    <div className="relative">
      {suggestions.length > 0 && (
        <div className="absolute bottom-full mb-1 left-0 right-0 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg z-10 max-h-48 overflow-auto">
          {suggestions.map((p) => (
            <button
              key={p.id}
              onClick={() => pickSuggestion(p)}
              className="flex w-full flex-col px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
            >
              <span className="font-medium text-gray-900 dark:text-gray-100">{p.name}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400 truncate">{p.description}</span>
            </button>
          ))}
        </div>
      )}

      {selectedHint && (
        <div className="mb-1 flex items-center gap-1">
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300">
            / {selectedHint}
            <button
              onClick={() => setSelectedHint(null)}
              className="ml-1 hover:text-red-500"
              aria-label="Remove hint"
            >
              ×
            </button>
          </span>
        </div>
      )}

      <div className="flex gap-2 items-end rounded-2xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500">
        <textarea
          ref={inputRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder={selectedHint ? `Ask about ${selectedHint}…` : 'Ask a question about your logs… (type /process to filter)'}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none disabled:opacity-50"
          style={{ maxHeight: 120, overflowY: 'auto' }}
          onInput={(e) => {
            const t = e.target as HTMLTextAreaElement
            t.style.height = 'auto'
            t.style.height = `${Math.min(t.scrollHeight, 120)}px`
          }}
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="flex-shrink-0 rounded-full bg-blue-600 p-1.5 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
          aria-label="Send"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}
