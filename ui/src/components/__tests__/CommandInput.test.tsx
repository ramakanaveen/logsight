import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CommandInput } from '../CommandInput'
import type { ProcessDefinition } from '../../types'

const processes: ProcessDefinition[] = [
  { id: '1', name: 'CurveBuilder', description: 'Builds curves', example_qa: [], created_at: '', updated_at: '' },
  { id: '2', name: 'RiskEngine', description: 'Calculates risk', example_qa: [], created_at: '', updated_at: '' },
]

describe('CommandInput', () => {
  it('renders a textarea', () => {
    render(<CommandInput processes={processes} onSend={() => {}} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('shows autocomplete suggestions when typing /process', async () => {
    render(<CommandInput processes={processes} onSend={() => {}} />)
    await userEvent.type(screen.getByRole('textbox'), '/curve')
    expect(screen.getByText('CurveBuilder')).toBeInTheDocument()
  })

  it('does not show suggestions for plain text', async () => {
    render(<CommandInput processes={processes} onSend={() => {}} />)
    await userEvent.type(screen.getByRole('textbox'), 'hello world')
    expect(screen.queryByText('CurveBuilder')).not.toBeInTheDocument()
  })

  it('calls onSend with question and hint when suggestion is picked', async () => {
    const onSend = vi.fn()
    render(<CommandInput processes={processes} onSend={onSend} />)
    const input = screen.getByRole('textbox')
    await userEvent.type(input, '/curve')
    fireEvent.click(screen.getByText('CurveBuilder'))
    await userEvent.type(input, 'Is it done?')
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('Is it done?', 'CurveBuilder')
  })

  it('sends without hint for plain text', async () => {
    const onSend = vi.fn()
    render(<CommandInput processes={processes} onSend={onSend} />)
    const input = screen.getByRole('textbox')
    await userEvent.type(input, 'What happened?')
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('What happened?', null)
  })
})
