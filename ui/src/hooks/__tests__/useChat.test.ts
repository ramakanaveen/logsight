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

  it('stores usage data from usage event', async () => {
    const { streamChat } = await import('../../api')
    const usageData = { input_tokens: 200, output_tokens: 80, total_tokens: 280, cost_usd: 0.002 }
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'answer', data: { text: 'Answer' } },
        { type: 'usage', data: usageData },
        { type: 'done', data: { conversation_id: 'c3' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })

    expect(result.current.turns[0].usage).toEqual(usageData)
  })

  it('stores chart data from chart event', async () => {
    const { streamChat } = await import('../../api')
    const chartData = {
      chart_type: 'bar' as const,
      title: 'Errors',
      labels: ['A', 'B'],
      datasets: [{ label: 'Count', data: [1, 2] }],
    }
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'chart', data: chartData },
        { type: 'answer', data: { text: 'See chart.' } },
        { type: 'done', data: { conversation_id: 'c4' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Show me a chart')
    })

    expect(result.current.turns[0].chart).toEqual(chartData)
  })

  it('stores clarifyOptions from clarify event with options', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'clarify', data: { question: 'Which process?', options: ['A', 'B'] } },
        { type: 'done', data: { conversation_id: 'c5' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Check the process')
    })

    expect(result.current.turns[0].clarifyOptions).toEqual(['A', 'B'])
  })

  it('stores messageId from done event', async () => {
    const { streamChat } = await import('../../api')
    vi.mocked(streamChat).mockReturnValue(
      makeStream([
        { type: 'answer', data: { text: 'Done.' } },
        { type: 'done', data: { conversation_id: 'c6', message_id: 'msg-123' } },
      ])
    )

    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Any question')
    })

    expect(result.current.turns[0].messageId).toBe('msg-123')
  })
})
