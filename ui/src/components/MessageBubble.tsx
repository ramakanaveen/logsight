import { ThinkingBlock } from './ThinkingBlock'
import { ToolCallTrace } from './ToolCallTrace'
import { SourceChips } from './SourceChips'
import { ClarifyPrompt } from './ClarifyPrompt'
import type { ChatTurn } from '../types'

interface Props {
  turn: ChatTurn
  onClarify: (reply: string) => void
}

export function MessageBubble({ turn, onClarify }: Props) {
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
            <p className="whitespace-pre-wrap leading-relaxed">{turn.answerText}</p>
          )}

          {turn.clarifyQuestion && (
            <ClarifyPrompt question={turn.clarifyQuestion} onReply={onClarify} />
          )}

          {turn.error && (
            <p className="text-red-500 dark:text-red-400">{turn.error}</p>
          )}

          <SourceChips sources={turn.sources} />
        </div>
      </div>
    </div>
  )
}
