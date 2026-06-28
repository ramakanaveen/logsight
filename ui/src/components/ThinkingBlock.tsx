import { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'

interface Props {
  text: string
}

export function ThinkingBlock({ text }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="my-2 rounded-xl border border-violet-200 dark:border-violet-800/50 bg-violet-50 dark:bg-violet-950/20 text-sm overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-violet-600 dark:text-violet-400 hover:bg-violet-100 dark:hover:bg-violet-900/20 transition-colors"
      >
        <Brain size={13} className="flex-shrink-0" />
        <span className="font-medium text-xs">{"Claude's thinking"}</span>
        {open ? <ChevronDown size={12} className="ml-auto" /> : <ChevronRight size={12} className="ml-auto" />}
      </button>
      {open && (
        <pre className="px-3 pb-3 pt-1 text-xs text-violet-700 dark:text-violet-300 whitespace-pre-wrap font-mono overflow-auto max-h-56 leading-relaxed">
          {text}
        </pre>
      )}
    </div>
  )
}
