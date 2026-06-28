import { create } from 'zustand'
import type { ChatTurn, Conversation } from './types'

interface ChatState {
  conversationId: string | null
  turns: ChatTurn[]
  conversations: Conversation[]
  clarifyPending: boolean

  setConversationId: (id: string | null) => void
  addTurn: (question: string) => number
  updateTurn: (idx: number, patch: Partial<ChatTurn>) => void
  appendToolCall: (idx: number, tool: string, input: Record<string, unknown>) => void
  resolveToolCall: (idx: number, tool: string, result: unknown) => void
  setConversations: (convs: Conversation[]) => void
  reset: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  turns: [],
  conversations: [],
  clarifyPending: false,

  setConversationId: (id) => set({ conversationId: id }),

  addTurn: (question) => {
    let idx = -1
    set((s) => {
      idx = s.turns.length
      return {
        turns: [...s.turns, { question, toolCalls: [], sources: [], loading: true }],
      }
    })
    return idx
  },

  updateTurn: (idx, patch) =>
    set((s) => {
      const turns = [...s.turns]
      turns[idx] = { ...turns[idx], ...patch }
      return { turns }
    }),

  appendToolCall: (idx, tool, input) =>
    set((s) => {
      const turns = [...s.turns]
      turns[idx] = { ...turns[idx], toolCalls: [...turns[idx].toolCalls, { tool, input }] }
      return { turns }
    }),

  resolveToolCall: (idx, tool, result) =>
    set((s) => {
      const turns = [...s.turns]
      const toolCalls = [...turns[idx].toolCalls]
      const tcIdx = [...toolCalls].reverse().findIndex((tc) => tc.tool === tool && tc.result === undefined)
      if (tcIdx >= 0) {
        const realIdx = toolCalls.length - 1 - tcIdx
        toolCalls[realIdx] = { ...toolCalls[realIdx], result }
      }
      turns[idx] = { ...turns[idx], toolCalls }
      return { turns }
    }),

  setConversations: (conversations) => set({ conversations }),

  reset: () => set({ conversationId: null, turns: [] }),
}))

// ── Theme ────────────────────────────────────────────────────────────────────

interface ThemeState {
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: (localStorage.getItem('logsight-theme') as 'dark' | 'light') ?? 'dark',
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('logsight-theme', next)
      document.documentElement.classList.toggle('dark', next === 'dark')
      return { theme: next }
    }),
}))
