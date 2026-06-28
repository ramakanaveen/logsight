import { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'

interface Props {
  text: string
}

export function ThinkingBlock({ text }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="my-2 rounded border border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/30 text-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded"
      >
        <Brain size={14} />
        <span className="font-medium">{"Claude's thinking"}</span>
        {open ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}
      </button>
      {open && (
        <pre className="px-3 pb-3 pt-1 text-xs text-purple-800 dark:text-purple-200 whitespace-pre-wrap font-mono overflow-auto max-h-64">
          {text}
        </pre>
      )}
    </div>
  )
}
