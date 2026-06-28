import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClarifyPrompt } from '../ClarifyPrompt'

describe('ClarifyPrompt', () => {
  it('renders the question', () => {
    render(<ClarifyPrompt question="Which time range?" onReply={() => {}} />)
    expect(screen.getByText('Which time range?')).toBeInTheDocument()
  })

  it('calls onReply with user input on submit', async () => {
    const onReply = vi.fn()
    render(<ClarifyPrompt question="Which time range?" onReply={onReply} />)
    const input = screen.getByPlaceholderText('Your answer…')
    await userEvent.type(input, 'Today only')
    fireEvent.submit(input.closest('form')!)
    expect(onReply).toHaveBeenCalledWith('Today only')
  })

  it('does not call onReply on empty submit', () => {
    const onReply = vi.fn()
    render(<ClarifyPrompt question="Which time range?" onReply={onReply} />)
    fireEvent.submit(screen.getByPlaceholderText('Your answer…').closest('form')!)
    expect(onReply).not.toHaveBeenCalled()
  })
})
