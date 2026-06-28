import { render, screen, fireEvent } from '@testing-library/react'
import { ThinkingBlock } from '../ThinkingBlock'

describe('ThinkingBlock', () => {
  it('renders collapsed by default', () => {
    render(<ThinkingBlock text="Let me think about this." />)
    expect(screen.getByText("Claude's thinking")).toBeInTheDocument()
    expect(screen.queryByText('Let me think about this.')).not.toBeInTheDocument()
  })

  it('expands on click and shows thinking text', () => {
    render(<ThinkingBlock text="Let me think about this." />)
    fireEvent.click(screen.getByText("Claude's thinking"))
    expect(screen.getByText('Let me think about this.')).toBeInTheDocument()
  })

  it('collapses again on second click', () => {
    render(<ThinkingBlock text="Let me think about this." />)
    const btn = screen.getByText("Claude's thinking")
    fireEvent.click(btn)
    expect(screen.getByText('Let me think about this.')).toBeInTheDocument()
    fireEvent.click(btn)
    expect(screen.queryByText('Let me think about this.')).not.toBeInTheDocument()
  })
})
