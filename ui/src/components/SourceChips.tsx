import { useState } from 'react'
import { ChevronDown, ChevronUp, FileText } from 'lucide-react'
import type { SourceInfo } from '../types'

interface Props {
  sources: SourceInfo[]
}

export function SourceChips({ sources }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  if (sources.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5 mt-3">
      {sources.map((s, i) => (
        <div key={i}>
          <button
            onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
            className="inline-flex items-center gap-1.5 rounded-full bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:text-orange-300 hover:bg-orange-100 dark:hover:bg-orange-900/40 transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
            <span className="font-semibold">{s.process}</span>
            {s.machine && <span className="text-orange-500 dark:text-orange-400">· {s.machine}</span>}
            {s.lines_matched > 0 && (
              <span className="text-orange-400 dark:text-orange-500">· {s.lines_matched} lines</span>
            )}
            {s.matched_files && s.matched_files.length > 0 && (
              expandedIdx === i ? <ChevronUp size={10} /> : <ChevronDown size={10} />
            )}
          </button>
          {expandedIdx === i && s.matched_files && s.matched_files.length > 0 && (
            <div className="ml-3 mt-1.5 flex flex-col gap-0.5 p-2 rounded-lg bg-stone-50 dark:bg-stone-800/50 border border-stone-200 dark:border-stone-700">
              {s.matched_files.map((f) => (
                <span
                  key={f}
                  className="inline-flex items-center gap-1.5 text-xs text-stone-500 dark:text-stone-400 font-mono"
                >
                  <FileText size={10} className="flex-shrink-0 text-stone-400" />
                  {f}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
