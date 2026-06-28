import { render, screen } from '@testing-library/react'
import { MessageBubble } from '../MessageBubble'
import type { ChatTurn } from '../../types'

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // URL.createObjectURL is not available in jsdom
  global.URL.createObjectURL = vi.fn(() => 'blob:mock')
  global.URL.revokeObjectURL = vi.fn()
})

function makeTurn(overrides: Partial<ChatTurn> = {}): ChatTurn {
  return {
    question: 'Is curve building done?',
    toolCalls: [],
    sources: [],
    loading: false,
    ...overrides,
  }
}

describe('MessageBubble', () => {
  it('renders the user question', () => {
    render(<MessageBubble turn={makeTurn()} onClarify={() => {}} />)
    expect(screen.getByText('Is curve building done?')).toBeInTheDocument()
  })

  it('renders markdown answer as formatted HTML (table)', () => {
    const turn = makeTurn({
      answerText: '| Server | Status |\n|--------|--------|\n| server1 | OK |',
    })
    render(<MessageBubble turn={turn} onClarify={() => {}} />)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Server')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
  })

  it('renders loading indicator when loading and no answer', () => {
    const turn = makeTurn({ loading: true })
    render(<MessageBubble turn={turn} onClarify={() => {}} />)
    // Three animated dots
    const dots = document.querySelectorAll('.dot-1, .dot-2, .dot-3')
    expect(dots.length).toBe(3)
  })

  it('renders usage pill when usage is present', () => {
    const turn = makeTurn({
      answerText: 'Done.',
      usage: { input_tokens: 100, output_tokens: 50, total_tokens: 150, cost_usd: 0.002 },
    })
    render(<MessageBubble turn={turn} onClarify={() => {}} />)
    expect(screen.getByText(/150 tokens/)).toBeInTheDocument()
  })

  it('renders download button when answer is present', () => {
    const turn = makeTurn({ answerText: 'Curve is done.' })
    render(<MessageBubble turn={turn} onClarify={() => {}} />)
    expect(screen.getByTitle('Download as Markdown')).toBeInTheDocument()
  })

  it('renders error text when error is present', () => {
    const turn = makeTurn({ error: 'Something went wrong' })
    render(<MessageBubble turn={turn} onClarify={() => {}} />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders feedback buttons when onFeedback prop is provided', () => {
    const turn = makeTurn({ answerText: 'Done.' })
    render(<MessageBubble turn={turn} onClarify={() => {}} onFeedback={() => {}} />)
    expect(screen.getByTitle('Helpful')).toBeInTheDocument()
    expect(screen.getByTitle('Not helpful')).toBeInTheDocument()
  })
})
