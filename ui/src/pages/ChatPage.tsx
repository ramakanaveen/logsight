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
        updateTurn(idx, {
          answerText: asstMsgs[i]?.content ?? '',
          messageId: asstMsgs[i]?.id,
          loading: false,
          conversationId: id,
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

  const handleFeedback = async (
    turn: ChatTurn,
    rating: 1 | -1,
    comment: string,
  ) => {
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

      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-gray-200 dark:border-gray-800 px-6 py-3 flex items-center gap-3">
          <div>
            <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">LogSight</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Ask questions about your trading logs
            </p>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-auto px-6 py-4 space-y-6">
          {turns.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center space-y-2">
                <p className="text-2xl">🔍</p>
                <p className="text-base font-medium text-gray-700 dark:text-gray-300">
                  Ask a question about your logs
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Type{' '}
                  <code className="rounded bg-gray-100 dark:bg-gray-800 px-1 py-0.5">
                    /process-name
                  </code>{' '}
                  to focus on a specific process
                </p>
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
        <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-4">
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
