import { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import type { ChatTurn } from '../types'

interface Props {
  toolCalls: ChatTurn['toolCalls']
}

export function ToolCallTrace({ toolCalls }: Props) {
  const [open, setOpen] = useState(false)

  if (toolCalls.length === 0) return null

  return (
    <div className="my-2 rounded-xl border border-stone-200 dark:border-stone-700 bg-stone-50 dark:bg-stone-800/40 text-sm overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-stone-500 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800/60 transition-colors"
      >
        <Wrench size={13} className="flex-shrink-0" />
        <span className="font-medium text-xs">Tool calls ({toolCalls.length})</span>
        {open ? <ChevronDown size={12} className="ml-auto" /> : <ChevronRight size={12} className="ml-auto" />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {toolCalls.map((tc, i) => (
            <div key={i} className="rounded-lg border border-stone-200 dark:border-stone-700 overflow-hidden">
              <div className="flex items-center gap-2 px-2.5 py-1.5 bg-stone-100 dark:bg-stone-800 text-xs font-mono font-semibold text-orange-600 dark:text-orange-400">
                <Wrench size={11} />
                {tc.tool}
              </div>
              <div className="px-2.5 py-2 text-xs text-stone-500 dark:text-stone-400">
                <div className="font-medium text-stone-600 dark:text-stone-300 mb-1">Input</div>
                <pre className="whitespace-pre-wrap font-mono text-xs overflow-auto max-h-32 text-stone-500 dark:text-stone-500">
                  {JSON.stringify(tc.input, null, 2)}
                </pre>
                {tc.result !== undefined && (
                  <>
                    <div className="font-medium text-stone-600 dark:text-stone-300 mt-2 mb-1">Result</div>
                    <pre className="whitespace-pre-wrap font-mono text-xs overflow-auto max-h-32 text-stone-500 dark:text-stone-500">
                      {JSON.stringify(tc.result, null, 2)}
                    </pre>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
