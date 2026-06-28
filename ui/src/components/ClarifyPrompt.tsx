import { useState } from 'react'
import { Send } from 'lucide-react'

interface Props {
  question: string
  onReply: (reply: string) => void
}

export function ClarifyPrompt({ question, onReply }: Props) {
  const [reply, setReply] = useState('')

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30 p-3 my-2">
      <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-2">{question}</p>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (reply.trim()) {
            onReply(reply.trim())
            setReply('')
          }
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          placeholder="Your answer…"
          className="flex-1 rounded border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
          autoFocus
        />
        <button
          type="submit"
          disabled={!reply.trim()}
          className="flex items-center gap-1 rounded bg-amber-500 px-3 py-1 text-sm text-white hover:bg-amber-600 disabled:opacity-50"
        >
          <Send size={13} /> Send
        </button>
      </form>
    </div>
  )
}
