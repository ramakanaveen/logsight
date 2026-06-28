import { renderHook, act } from '@testing-library/react'
import { useChat } from '../useChat'
import { useChatStore } from '../../store'
import { vi } from 'vitest'
import type { SSEEvent } from '../../types'

beforeEach(() => {
  useChatStore.getState().reset()
})

async function* makeStream(events: SSEEvent[]): AsyncGenerator<SSEEvent> {
  for (const e of events) {
    yield e
  }
}

vi.mock('../../api', () => ({
  streamChat: vi.fn(),
  getConversations: vi.fn().mockResolvedValue([]),
}))

describe('useChat', () => {
  it('adds a loading turn when sendMessage is called', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'answer', data: { text: 'Done.' } },
        { type: 'sources', data: [] },
        { type: 'done', data: { conversation_id: 'abc' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Is curve done?')
    })

    expect(result.current.turns).toHaveLength(1)
    expect(result.current.turns[0].question).toBe('Is curve done?')
    expect(result.current.turns[0].answerText).toBe('Done.')
    expect(result.current.turns[0].loading).toBe(false)
  })

  it('sets conversationId on done event', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'answer', data: { text: 'Answer' } },
        { type: 'sources', data: [] },
        { type: 'done', data: { conversation_id: 'conv-xyz' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Test question')
    })

    expect(result.current.conversationId).toBe('conv-xyz')
  })

  it('records thinking text from thinking event', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'thinking', data: { text: 'Let me check the sidecars.' } },
        { type: 'answer', data: { text: 'Found it.' } },
        { type: 'sources', data: [] },
        { type: 'done', data: { conversation_id: 'c1' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })

    expect(result.current.turns[0].thinkingText).toBe('Let me check the sidecars.')
  })

  it('records clarifyQuestion from clarify event', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'clarify', data: { question: 'Which time range?' } },
        { type: 'done', data: { conversation_id: 'c2' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Ambiguous question')
    })

    expect(result.current.turns[0].clarifyQuestion).toBe('Which time range?')
  })

  it('sets error on error event', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([{ type: 'error', data: { message: 'Something went wrong' } }])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Bad question')
    })

    expect(result.current.turns[0].error).toBe('Something went wrong')
    expect(result.current.turns[0].loading).toBe(false)
  })
})
