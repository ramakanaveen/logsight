import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getProcesses,
  getConversations,
  getConversationMessages,
  deleteConversation,
  submitFeedback,
} from '../api'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../store'
import { CommandInput } from '../components/CommandInput'
import { MessageBubble } from '../components/MessageBubble'
import { ConversationSidebar } from '../components/ConversationSidebar'
import type { ChatTurn } from '../types'

function exportConversation(turns: ChatTurn[]) {
  const lines: string[] = ['# LogSight Conversation', '']
  for (const turn of turns) {
    lines.push(`## Question`, '', turn.question, '')
    if (turn.answerText) {
      lines.push(`### Answer`, '', turn.answerText, '')
    }
    if (turn.sources.length > 0) {
      lines.push('### Sources', '')
      for (const s of turn.sources) {
        lines.push(`- **${s.process}** on \`${s.machine}\`: ${s.lines_matched} lines`)
        for (const f of s.matched_files ?? []) {
          lines.push(`  - \`${f}\``)
        }
      }
      lines.push('')
    }
    lines.push('---', '')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `logsight-conversation-${Date.now()}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

const EXAMPLE_PROMPTS = [
  'Is curve building complete for today?',
  'Any errors in the last hour?',
  'Which processes are still running?',
  'Show me recent shutdown events',
]

export function ChatPage() {
  const { sendMessage, turns } = useChat()
  const conversationId = useChatStore((s) => s.conversationId)
  const setConversations = useChatStore((s) => s.setConversations)
  const reset = useChatStore((s) => s.reset)
  const setConversationId = useChatStore((s) => s.setConversationId)
  const addTurn = useChatStore((s) => s.addTurn)
  const updateTurn = useChatStore((s) => s.updateTurn)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: processes = [] } = useQuery({ queryKey: ['processes'], queryFn: getProcesses })
  const { data: conversations = [], refetch: refetchConvs } = useQuery({
    queryKey: ['conversations'],
    queryFn: getConversations,
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  useEffect(() => {
    setConversations(conversations)
  }, [conversations, setConversations])

  const isLoading = turns.some((t) => t.loading)

  const loadConversation = async (id: string) => {
    reset()
    setConversationId(id)
    try {
      const msgs = await getConversationMessages(id)
      const userMsgs = msgs.filter((m) => m.role === 'user')
      const asstMsgs = msgs.filter((m) => m.role === 'assistant')
      for (let i = 0; i < userMsgs.length; i++) {
        const idx = addTurn(userMsgs[i].content)
        const asst = asstMsgs[i]
        updateTurn(idx, {
          answerText: asst?.content ?? '',
          messageId: asst?.id,
          loading: false,
          conversationId: id,
          // Restore rich data persisted in metadata
          chart: asst?.metadata?.chart as import('../types').ChartSpec | undefined,
          sources: (asst?.metadata?.sources as import('../types').SourceInfo[]) ?? [],
          usage: asst?.metadata?.usage as import('../types').UsageInfo | undefined,
        })
      }
    } catch {
      // fallback: just set the id
    }
  }

  const handleDelete = async (id: string) => {
    await deleteConversation(id)
    if (conversationId === id) reset()
    refetchConvs()
  }

  const handleFeedback = async (turn: ChatTurn, rating: 1 | -1, comment: string) => {
    if (!turn.conversationId || !turn.messageId) return
    try {
      await submitFeedback({
        conversation_id: turn.conversationId,
        message_id: turn.messageId,
        rating,
        comment,
      })
    } catch {
      // best-effort
    }
  }

  return (
    <div className="flex h-full overflow-hidden">
      <ConversationSidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={loadConversation}
        onNew={() => reset()}
        onDelete={handleDelete}
        onExport={() => exportConversation(turns)}
      />

      <main className="flex flex-1 flex-col overflow-hidden bg-stone-50 dark:bg-stone-950">
        {/* Messages */}
        <div className="flex-1 overflow-auto px-6 py-6 space-y-6">
          {turns.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center space-y-5 max-w-md">
                <div className="flex justify-center">
                  <div className="w-16 h-16 rounded-2xl bg-stone-900 dark:bg-stone-800 flex items-center justify-center shadow-lg">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                      <circle cx="13.5" cy="13.5" r="6.5" stroke="#F97316" strokeWidth="2.4" fill="none" />
                      <circle cx="11.5" cy="11.5" r="2.2" fill="#FBBF24" fillOpacity="0.4" />
                      <line x1="18.5" y1="18.5" x2="26" y2="26" stroke="#F97316" strokeWidth="2.4" strokeLinecap="round" />
                    </svg>
                  </div>
                </div>
                <div>
                  <p className="text-lg font-semibold text-stone-800 dark:text-stone-100">
                    Ask your logs anything
                  </p>
                  <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">
                    Questions are answered in seconds — no SSH, no grep
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {EXAMPLE_PROMPTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => sendMessage(p, null)}
                      disabled={isLoading}
                      className="text-xs px-3 py-1.5 rounded-full border border-stone-300 dark:border-stone-700 text-stone-600 dark:text-stone-400 hover:border-orange-400 hover:text-orange-600 dark:hover:border-orange-600 dark:hover:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-950/20 transition-colors disabled:opacity-50"
                    >
                      {p}
                    </button>
                  ))}
                </div>
                {processes.length > 0 && (
                  <p className="text-xs text-stone-400 dark:text-stone-600">
                    Type <kbd className="px-1.5 py-0.5 rounded bg-stone-200 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-mono">/</kbd> to target a specific process
                  </p>
                )}
              </div>
            </div>
          )}
          {turns.map((turn, i) => (
            <MessageBubble
              key={i}
              turn={turn}
              onClarify={(reply) => sendMessage(reply, null)}
              onFeedback={(rating, comment) => handleFeedback(turn, rating, comment)}
            />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-6 py-4">
          <CommandInput
            processes={processes}
            onSend={(q, hint) => sendMessage(q, hint)}
            disabled={isLoading}
          />
        </div>
      </main>
    </div>
  )
}
