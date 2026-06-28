import type { SourceInfo } from '../types'

interface Props {
  sources: SourceInfo[]
}

export function SourceChips({ sources }: Props) {
  if (sources.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {sources.map((s, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300"
        >
          <span className="font-medium">{s.process}</span>
          {s.machine && <span>· {s.machine}</span>}
          {s.lines_matched > 0 && <span>· {s.lines_matched} lines</span>}
        </span>
      ))}
    </div>
  )
}
