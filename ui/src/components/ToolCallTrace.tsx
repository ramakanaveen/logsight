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
    <div className="my-2 rounded border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/30 text-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50 rounded"
      >
        <Wrench size={14} />
        <span className="font-medium">Tool calls ({toolCalls.length})</span>
        {open ? <ChevronDown size={14} className="ml-auto" /> : <ChevronRight size={14} className="ml-auto" />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {toolCalls.map((tc, i) => (
            <div key={i} className="rounded border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center gap-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 text-xs font-mono font-semibold text-blue-700 dark:text-blue-300">
                <Wrench size={11} />
                {tc.tool}
              </div>
              <div className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400">
                <div className="font-medium mb-1">Input:</div>
                <pre className="whitespace-pre-wrap font-mono text-xs overflow-auto max-h-32">
                  {JSON.stringify(tc.input, null, 2)}
                </pre>
                {tc.result !== undefined && (
                  <>
                    <div className="font-medium mt-2 mb-1">Result:</div>
                    <pre className="whitespace-pre-wrap font-mono text-xs overflow-auto max-h-32">
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
