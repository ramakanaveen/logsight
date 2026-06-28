import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TopologyView } from '../TopologyView'
import type { NamespaceTopology } from '../../types'
import { vi } from 'vitest'

const topology: NamespaceTopology[] = [
  {
    namespace: { id: 'ns1', name: 'STIRT', description: 'STIRT desk', created_at: '' },
    machines: [
      {
        machine: { id: 'm1', namespace_id: 'ns1', hostname: 'server1.stirt.internal', description: '', created_at: '' },
        sidecar: { id: 's1', machine_id: 'm1', port: 9000, status: 'alive', last_heartbeat: '', registered_at: '' },
        processes: [
          { id: 'p1', name: 'CurveBuilder', log_paths: ['/opt/logs/*.log'] },
          { id: 'p2', name: 'RiskEngine', log_paths: ['/var/logs/*.log'] },
        ],
      },
      {
        machine: { id: 'm2', namespace_id: 'ns1', hostname: 'server2.stirt.internal', description: '', created_at: '' },
        sidecar: null,
        processes: [],
      },
    ],
  },
]

vi.mock('../../api', () => ({
  getTopology: () => Promise.resolve(topology),
  getProcesses: () => Promise.resolve([]),
  getMachineProcesses: () => Promise.resolve([]),
}))

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('TopologyView', () => {
  it('renders namespace name', async () => {
    wrap(<TopologyView />)
    expect(await screen.findByText('STIRT')).toBeInTheDocument()
  })

  it('renders machine hostnames', async () => {
    wrap(<TopologyView />)
    expect(await screen.findByText('server1.stirt.internal')).toBeInTheDocument()
    expect(await screen.findByText('server2.stirt.internal')).toBeInTheDocument()
  })

  it('shows alive badge for alive sidecar', async () => {
    wrap(<TopologyView />)
    expect(await screen.findByText('alive')).toBeInTheDocument()
  })

  it('shows no sidecar badge when sidecar is null', async () => {
    wrap(<TopologyView />)
    expect(await screen.findByText('no sidecar')).toBeInTheDocument()
  })

  it('shows process chips', async () => {
    wrap(<TopologyView />)
    expect(await screen.findByText('CurveBuilder')).toBeInTheDocument()
    expect(await screen.findByText('RiskEngine')).toBeInTheDocument()
  })
})
