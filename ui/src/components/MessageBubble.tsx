import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download, ThumbsUp, ThumbsDown } from 'lucide-react'
import { ThinkingBlock } from './ThinkingBlock'
import { ToolCallTrace } from './ToolCallTrace'
import { SourceChips } from './SourceChips'
import { ClarifyPrompt } from './ClarifyPrompt'
import { ChartBlock } from './ChartBlock'
import type { ChatTurn } from '../types'

interface Props {
  turn: ChatTurn
  onClarify: (reply: string) => void
  onFeedback?: (rating: 1 | -1, comment: string) => void
}

function downloadTurn(turn: ChatTurn) {
  const lines: string[] = ['# LogSight Analysis', '', `**Question:** ${turn.question}`, '']
  if (turn.thinkingText) {
    lines.push('<details><summary>Thinking</summary>', '', turn.thinkingText, '', '</details>', '')
  }
  if (turn.answerText) lines.push(turn.answerText, '')
  if (turn.sources.length > 0) {
    lines.push('## Sources', '')
    for (const s of turn.sources) {
      lines.push(`- **${s.process}** on \`${s.machine}\`: ${s.lines_matched} lines matched`)
      for (const f of s.matched_files ?? []) lines.push(`  - \`${f}\``)
    }
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `logsight-${Date.now()}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

function FeedbackButtons({ onFeedback }: { onFeedback?: (rating: 1 | -1, comment: string) => void }) {
  const [submitted, setSubmitted] = useState<1 | -1 | null>(null)
  const [showComment, setShowComment] = useState<1 | -1 | null>(null)
  const [comment, setComment] = useState('')

  if (!onFeedback) return null

  const submit = (rating: 1 | -1) => {
    onFeedback(rating, comment)
    setSubmitted(rating)
    setShowComment(null)
    setComment('')
  }

  if (submitted !== null) {
    return (
      <span className="text-xs text-stone-400 dark:text-stone-500">
        {submitted === 1 ? '👍' : '👎'} Thanks!
      </span>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-0.5">
        <button
          onClick={() => setShowComment(showComment === 1 ? null : 1)}
          className={`p-1 rounded-md transition-colors ${
            showComment === 1
              ? 'text-green-500 bg-green-50 dark:bg-green-950/30'
              : 'text-stone-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-950/20'
          }`}
          title="Helpful"
        >
          <ThumbsUp size={12} />
        </button>
        <button
          onClick={() => setShowComment(showComment === -1 ? null : -1)}
          className={`p-1 rounded-md transition-colors ${
            showComment === -1
              ? 'text-red-500 bg-red-50 dark:bg-red-950/30'
              : 'text-stone-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20'
          }`}
          title="Not helpful"
        >
          <ThumbsDown size={12} />
        </button>
      </div>
      {showComment !== null && (
        <div className="flex gap-1.5">
          <input
            autoFocus
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit(showComment)}
            placeholder="Optional comment…"
            className="flex-1 rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-2 py-0.5 text-xs text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
          />
          <button
            onClick={() => submit(showComment)}
            className="rounded-lg bg-orange-500 hover:bg-orange-600 px-2.5 py-0.5 text-xs text-white transition-colors"
          >
            Send
          </button>
        </div>
      )}
    </div>
  )
}

export function MessageBubble({ turn, onClarify, onFeedback }: Props) {
  const toolCallCount = turn.toolCalls.length
  const hasAnswer = Boolean(turn.answerText)

  return (
    <div className="space-y-3">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[72%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-orange-500 to-orange-600 px-4 py-2.5 text-sm text-white shadow-sm shadow-orange-200 dark:shadow-orange-900/30">
          {turn.question}
        </div>
      </div>

      {/* Assistant response */}
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 shadow-sm px-4 py-3 text-sm text-stone-900 dark:text-stone-100">

          {turn.thinkingText && <ThinkingBlock text={turn.thinkingText} />}
          {turn.toolCalls.length > 0 && <ToolCallTrace toolCalls={turn.toolCalls} />}

          {/* Loading dots */}
          {turn.loading && !turn.answerText && !turn.clarifyQuestion && !turn.error && (
            <div className="flex items-center gap-1 py-1">
              <span className="w-2 h-2 rounded-full bg-orange-400 dot-1" />
              <span className="w-2 h-2 rounded-full bg-orange-400 dot-2" />
              <span className="w-2 h-2 rounded-full bg-orange-400 dot-3" />
            </div>
          )}

          {turn.answerText && (
            <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed prose-stone">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="text-xs border-collapse w-full">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-stone-200 dark:border-stone-700 px-2.5 py-1.5 bg-stone-50 dark:bg-stone-800 text-left font-semibold text-stone-700 dark:text-stone-300 text-xs">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-stone-200 dark:border-stone-700 px-2.5 py-1.5 text-stone-600 dark:text-stone-400 text-xs">
                      {children}
                    </td>
                  ),
                  code: ({ children }) => (
                    <code className="bg-stone-100 dark:bg-stone-800 text-orange-600 dark:text-orange-400 rounded px-1 font-mono text-xs">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-stone-100 dark:bg-stone-800 rounded-xl p-3 overflow-x-auto my-2 text-xs border border-stone-200 dark:border-stone-700">
                      {children}
                    </pre>
                  ),
                }}
              >
                {turn.answerText}
              </ReactMarkdown>
            </div>
          )}

          {turn.chart && <ChartBlock spec={turn.chart} />}

          {turn.clarifyQuestion && (
            <ClarifyPrompt
              question={turn.clarifyQuestion}
              options={turn.clarifyOptions}
              onReply={onClarify}
            />
          )}

          {turn.error && (
            <p className="text-red-500 dark:text-red-400 text-xs">{turn.error}</p>
          )}

          <SourceChips sources={turn.sources} />

          {/* Footer */}
          {(hasAnswer || turn.usage) && (
            <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-stone-100 dark:border-stone-800">
              <div className="flex items-center gap-2">
                {turn.usage && (
                  <span className="text-xs text-stone-400 dark:text-stone-500 tabular-nums">
                    {toolCallCount > 0 && `${toolCallCount} call${toolCallCount !== 1 ? 's' : ''} · `}
                    {turn.usage.total_tokens.toLocaleString()} tokens · ~
                    {turn.usage.cost_usd < 0.001 ? '<$0.001' : `$${turn.usage.cost_usd.toFixed(3)}`}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <FeedbackButtons onFeedback={onFeedback} />
                {hasAnswer && (
                  <button
                    onClick={() => downloadTurn(turn)}
                    className="p-1 rounded-md text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
                    title="Download as Markdown"
                  >
                    <Download size={12} />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
