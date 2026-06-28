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
  const lines: string[] = [
    '# LogSight Analysis',
    '',
    `**Question:** ${turn.question}`,
    '',
  ]
  if (turn.thinkingText) {
    lines.push('<details><summary>Thinking</summary>', '', turn.thinkingText, '', '</details>', '')
  }
  if (turn.answerText) {
    lines.push(turn.answerText, '')
  }
  if (turn.sources.length > 0) {
    lines.push('## Sources', '')
    for (const s of turn.sources) {
      lines.push(`- **${s.process}** on \`${s.machine}\`: ${s.lines_matched} lines matched`)
      for (const f of s.matched_files ?? []) {
        lines.push(`  - \`${f}\``)
      }
    }
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `logsight-${Date.now()}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

function FeedbackButtons({
  onFeedback,
}: {
  onFeedback?: (rating: 1 | -1, comment: string) => void
}) {
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
      <span className="text-xs text-gray-400 dark:text-gray-500">
        {submitted === 1 ? '👍' : '👎'} Thanks for the feedback
      </span>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <button
          onClick={() => setShowComment(showComment === 1 ? null : 1)}
          className={`p-1 rounded hover:text-green-600 transition-colors ${showComment === 1 ? 'text-green-600' : 'text-gray-400'}`}
          title="Helpful"
        >
          <ThumbsUp size={13} />
        </button>
        <button
          onClick={() => setShowComment(showComment === -1 ? null : -1)}
          className={`p-1 rounded hover:text-red-500 transition-colors ${showComment === -1 ? 'text-red-500' : 'text-gray-400'}`}
          title="Not helpful"
        >
          <ThumbsDown size={13} />
        </button>
      </div>
      {showComment !== null && (
        <div className="flex gap-1">
          <input
            autoFocus
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit(showComment)}
            placeholder="Optional comment…"
            className="flex-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-0.5 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <button
            onClick={() => submit(showComment)}
            className="rounded bg-blue-600 px-2 py-0.5 text-xs text-white hover:bg-blue-700"
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
    <div className="space-y-2">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2 text-sm text-white">
          {turn.question}
        </div>
      </div>

      {/* Assistant response */}
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-gray-100 dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
          {turn.thinkingText && <ThinkingBlock text={turn.thinkingText} />}
          {turn.toolCalls.length > 0 && <ToolCallTrace toolCalls={turn.toolCalls} />}

          {turn.loading && !turn.answerText && !turn.clarifyQuestion && !turn.error && (
            <div className="flex items-center gap-2 text-gray-400 dark:text-gray-500">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse delay-100">●</span>
              <span className="animate-pulse delay-200">●</span>
            </div>
          )}

          {turn.answerText && (
            <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ children }) => (
                    <table className="text-xs border-collapse w-full my-2">{children}</table>
                  ),
                  th: ({ children }) => (
                    <th className="border border-gray-300 dark:border-gray-600 px-2 py-1 bg-gray-50 dark:bg-gray-700 text-left font-medium">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-gray-300 dark:border-gray-600 px-2 py-1">
                      {children}
                    </td>
                  ),
                  code: ({ children }) => (
                    <code className="bg-gray-200 dark:bg-gray-700 rounded px-1 font-mono text-xs">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-gray-200 dark:bg-gray-700 rounded p-3 overflow-x-auto my-2 text-xs">
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
            <p className="text-red-500 dark:text-red-400">{turn.error}</p>
          )}

          <SourceChips sources={turn.sources} />

          {/* Footer: usage pill + download + feedback */}
          {(hasAnswer || turn.usage) && (
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                {turn.usage && (
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    {toolCallCount > 0 && `${toolCallCount} tool call${toolCallCount !== 1 ? 's' : ''} · `}
                    {turn.usage.total_tokens.toLocaleString()} tokens
                    {' · '}~${turn.usage.cost_usd < 0.001
                      ? '<$0.001'
                      : `$${turn.usage.cost_usd.toFixed(3)}`}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <FeedbackButtons onFeedback={onFeedback} />
                {hasAnswer && (
                  <button
                    onClick={() => downloadTurn(turn)}
                    className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    title="Download analysis as Markdown"
                  >
                    <Download size={13} />
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
