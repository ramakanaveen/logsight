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
      {/* Process suggestions dropdown */}
      {suggestions.length > 0 && (
        <div className="absolute bottom-full mb-2 left-0 right-0 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 shadow-lg shadow-stone-200/50 dark:shadow-stone-950/50 z-10 max-h-48 overflow-auto">
          {suggestions.map((p) => (
            <button
              key={p.id}
              onClick={() => pickSuggestion(p)}
              className="flex w-full flex-col px-3 py-2.5 text-left hover:bg-stone-50 dark:hover:bg-stone-800 first:rounded-t-xl last:rounded-b-xl transition-colors"
            >
              <span className="font-medium text-sm text-stone-900 dark:text-stone-100">{p.name}</span>
              <span className="text-xs text-stone-500 dark:text-stone-400 truncate mt-0.5">{p.description}</span>
            </button>
          ))}
        </div>
      )}

      {/* Selected process hint badge */}
      {selectedHint && (
        <div className="mb-2 flex items-center gap-1">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-orange-100 dark:bg-orange-950/40 border border-orange-200 dark:border-orange-800 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:text-orange-300">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500 flex-shrink-0" />
            {selectedHint}
            <button
              onClick={() => setSelectedHint(null)}
              className="ml-0.5 hover:text-red-500 transition-colors leading-none"
              aria-label="Remove hint"
            >
              ×
            </button>
          </span>
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-3 items-end rounded-2xl border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-4 py-3 focus-within:ring-2 focus-within:ring-orange-400 dark:focus-within:ring-orange-500 focus-within:border-orange-400 dark:focus-within:border-orange-500 transition-shadow shadow-sm">
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
          placeholder={
            selectedHint
              ? `Ask about ${selectedHint}…`
              : 'Ask a question about your logs… (type / to target a process)'
          }
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-600 focus:outline-none disabled:opacity-50"
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
          className="flex-shrink-0 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-40 p-2 text-white transition-colors shadow-sm shadow-orange-200 dark:shadow-orange-900/30"
          aria-label="Send"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}
