import { useCallback } from 'react'
import { streamChat, getConversations } from '../api'
import { useChatStore } from '../store'

export function useChat() {
  // Select stable action references — Zustand actions never change identity,
  // so these never appear in useCallback deps as changed values.
  const addTurn = useChatStore((s) => s.addTurn)
  const updateTurn = useChatStore((s) => s.updateTurn)
  const appendToolCall = useChatStore((s) => s.appendToolCall)
  const resolveToolCall = useChatStore((s) => s.resolveToolCall)
  const setConversationId = useChatStore((s) => s.setConversationId)
  const setConversations = useChatStore((s) => s.setConversations)

  // Reactive state — subscribes to just these slices, not the whole store object
  const turns = useChatStore((s) => s.turns)
  const conversationId = useChatStore((s) => s.conversationId)

  const sendMessage = useCallback(
    async (question: string, processHint?: string | null) => {
      // Read conversationId at call-time, not at render-time, to avoid stale closure
      const { conversationId: convId } = useChatStore.getState()
      const idx = addTurn(question)

      try {
        for await (const event of streamChat({
          question,
          conversation_id: convId,
          process_hint: processHint,
        })) {
          switch (event.type) {
            case 'thinking':
              updateTurn(idx, { thinkingText: event.data.text })
              break
            case 'tool_call':
              appendToolCall(idx, event.data.tool, event.data.input)
              break
            case 'tool_result':
              resolveToolCall(idx, event.data.tool, event.data.result)
              break
            case 'answer':
              updateTurn(idx, { answerText: event.data.text })
              break
            case 'sources':
              updateTurn(idx, { sources: event.data })
              break
            case 'usage':
              updateTurn(idx, { usage: event.data })
              break
            case 'chart':
              updateTurn(idx, { chart: event.data })
              break
            case 'clarify':
              updateTurn(idx, {
                clarifyQuestion: event.data.question,
                clarifyOptions: event.data.options,
              })
              break
            case 'done':
              setConversationId(event.data.conversation_id)
              updateTurn(idx, {
                loading: false,
                conversationId: event.data.conversation_id,
                messageId: event.data.message_id,
              })
              getConversations().then(setConversations).catch(() => {})
              break
            case 'error':
              updateTurn(idx, { error: event.data.message, loading: false })
              break
          }
        }
      } catch (err) {
        updateTurn(idx, {
          error: err instanceof Error ? err.message : 'Unknown error',
          loading: false,
        })
      }
    },
    [addTurn, updateTurn, appendToolCall, resolveToolCall, setConversationId, setConversations],
  )

  return { sendMessage, turns, conversationId }
}
