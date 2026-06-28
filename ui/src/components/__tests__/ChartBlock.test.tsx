import { render, screen } from '@testing-library/react'
import { ChartBlock } from '../ChartBlock'
import type { ChartSpec } from '../../types'

const barSpec: ChartSpec = {
  chart_type: 'bar',
  title: 'Errors by Hour',
  labels: ['10:00', '11:00', '12:00'],
  datasets: [{ label: 'Errors', data: [3, 7, 1] }],
}

const lineSpec: ChartSpec = {
  chart_type: 'line',
  title: 'Latency over Time',
  labels: ['T1', 'T2', 'T3'],
  datasets: [{ label: 'ms', data: [100, 150, 90] }],
}

const pieSpec: ChartSpec = {
  chart_type: 'pie',
  title: 'Error Distribution',
  labels: ['Timeout', 'Connection', 'Other'],
  datasets: [{ label: 'Count', data: [10, 5, 2] }],
}

// recharts uses ResizeObserver internally — provide a no-op mock
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
})

describe('ChartBlock', () => {
  it('renders bar chart without crashing', () => {
    render(<ChartBlock spec={barSpec} />)
    expect(screen.getByText('Errors by Hour')).toBeInTheDocument()
  })

  it('renders line chart without crashing', () => {
    render(<ChartBlock spec={lineSpec} />)
    expect(screen.getByText('Latency over Time')).toBeInTheDocument()
  })

  it('renders pie chart without crashing', () => {
    render(<ChartBlock spec={pieSpec} />)
    expect(screen.getByText('Error Distribution')).toBeInTheDocument()
  })
})
