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
    <div className="flex flex-col gap-1 mt-2">
      {sources.map((s, i) => (
        <div key={i}>
          <button
            onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
            className="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800/60 transition-colors"
          >
            <span className="font-medium">{s.process}</span>
            {s.machine && <span>· {s.machine}</span>}
            {s.lines_matched > 0 && <span>· {s.lines_matched} lines</span>}
            {s.matched_files && s.matched_files.length > 0 && (
              expandedIdx === i ? <ChevronUp size={10} /> : <ChevronDown size={10} />
            )}
          </button>
          {expandedIdx === i && s.matched_files && s.matched_files.length > 0 && (
            <div className="ml-2 mt-1 flex flex-col gap-0.5">
              {s.matched_files.map((f) => (
                <span
                  key={f}
                  className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 font-mono"
                >
                  <FileText size={10} className="flex-shrink-0" />
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
