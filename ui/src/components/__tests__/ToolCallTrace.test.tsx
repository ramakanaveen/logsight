import { render, screen, fireEvent } from '@testing-library/react'
import { ToolCallTrace } from '../ToolCallTrace'
import type { ChatTurn } from '../../types'

const makeCalls = (): ChatTurn['toolCalls'] => [
  { tool: 'list_sidecars', input: { status: 'alive' }, result: [{ sidecar_id: 'abc', machine_host: 'srv1' }] },
  { tool: 'search_logs', input: { sidecar_id: 'abc', process_name: 'CurveBuilder', keywords: ['done'] } },
]

describe('ToolCallTrace', () => {
  it('renders nothing when toolCalls is empty', () => {
    const { container } = render(<ToolCallTrace toolCalls={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows count and is collapsed by default', () => {
    render(<ToolCallTrace toolCalls={makeCalls()} />)
    expect(screen.getByText('Tool calls (2)')).toBeInTheDocument()
    expect(screen.queryByText('list_sidecars')).not.toBeInTheDocument()
  })

  it('expands and shows tool names on click', () => {
    render(<ToolCallTrace toolCalls={makeCalls()} />)
    fireEvent.click(screen.getByText('Tool calls (2)'))
    expect(screen.getAllByText('list_sidecars').length).toBeGreaterThan(0)
    expect(screen.getAllByText('search_logs').length).toBeGreaterThan(0)
  })

  it('shows result for resolved tool calls', () => {
    render(<ToolCallTrace toolCalls={makeCalls()} />)
    fireEvent.click(screen.getByText('Tool calls (2)'))
    expect(screen.getByText('Result')).toBeInTheDocument()
  })
})
