import { useState } from 'react'
import { Send } from 'lucide-react'

interface Props {
  question: string
  options?: string[]
  onReply: (reply: string) => void
}

export function ClarifyPrompt({ question, options, onReply }: Props) {
  const [reply, setReply] = useState('')

  return (
    <div className="rounded-xl border border-amber-200 dark:border-amber-800/50 bg-amber-50 dark:bg-amber-950/20 p-3 my-2">
      <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-2.5">{question}</p>

      {options && options.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => onReply(opt)}
              className="px-3 py-1.5 rounded-full text-xs font-medium border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 hover:border-amber-400 transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (reply.trim()) { onReply(reply.trim()); setReply('') }
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            placeholder="Your answer…"
            className="flex-1 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-stone-900 px-2.5 py-1 text-xs text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
            autoFocus
          />
          <button
            type="submit"
            disabled={!reply.trim()}
            className="inline-flex items-center gap-1 rounded-lg bg-amber-500 hover:bg-amber-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-50 transition-colors"
          >
            <Send size={11} /> Send
          </button>
        </form>
      )}
    </div>
  )
}
