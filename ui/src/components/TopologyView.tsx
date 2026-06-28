import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTopology, getNamespaces, getProcesses, getMachineProcesses,
  createNamespace, createMachine, deleteMachine, deleteNamespace,
  assignProcess, removeMachineProcess,
} from '../api'
import { Server, Cpu, Circle, Plus, Trash2, X, ChevronDown, ChevronRight } from 'lucide-react'
import type { NamespaceTopology, ProcessDefinition } from '../types'

// ── helpers ────────────────────────────────────────────────────────────────

function statusColor(status: string | undefined) {
  if (status === 'alive') return 'text-green-500'
  if (status === 'dead') return 'text-red-500'
  return 'text-gray-400'
}

function StatusBadge({ status }: { status: string | undefined }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${statusColor(status)}`}>
      <Circle size={8} fill="currentColor" />
      {status ?? 'no sidecar'}
    </span>
  )
}

// ── small modal ────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 shadow-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500">
            <X size={14} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── assign process modal ───────────────────────────────────────────────────

function AssignProcessModal({
  machineId,
  processes,
  onClose,
}: {
  machineId: string
  processes: ProcessDefinition[]
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState('')
  const [logPaths, setLogPaths] = useState('')

  const { data: existing = [] } = useQuery({
    queryKey: ['machine-processes', machineId],
    queryFn: () => getMachineProcesses(machineId),
  })

  const assignMut = useMutation({
    mutationFn: () =>
      assignProcess(machineId, {
        process_definition_id: selectedId,
        log_paths: logPaths.split('\n').map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['topology'] })
      qc.invalidateQueries({ queryKey: ['machine-processes', machineId] })
      setSelectedId('')
      setLogPaths('')
    },
  })

  const removeMut = useMutation({
    mutationFn: (mpId: string) => removeMachineProcess(machineId, mpId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['topology'] })
      qc.invalidateQueries({ queryKey: ['machine-processes', machineId] })
    },
  })

  const availableProcesses = processes.filter(
    (p) => !existing.some((e) => e.process_definition_id === p.id)
  )

  return (
    <Modal title="Assign processes to machine" onClose={onClose}>
      {existing.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Assigned</p>
          {existing.map((mp) => (
            <div key={mp.id} className="flex items-center justify-between rounded border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm">
              <div>
                <span className="font-medium text-gray-900 dark:text-gray-100">{mp.process_name}</span>
                <span className="ml-2 text-xs text-gray-400">{mp.log_paths.join(', ')}</span>
              </div>
              <button
                onClick={() => removeMut.mutate(mp.id)}
                className="text-gray-400 hover:text-red-500 ml-2"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {availableProcesses.length > 0 && (
        <div className="space-y-2 border-t border-gray-100 dark:border-gray-800 pt-3">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Add process</p>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select process…</option>
            {availableProcesses.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <textarea
            rows={2}
            value={logPaths}
            onChange={(e) => setLogPaths(e.target.value)}
            placeholder="Log paths (one per line)&#10;e.g. /opt/app/logs/*.log"
            className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => assignMut.mutate()}
            disabled={!selectedId || !logPaths.trim()}
            className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Plus size={13} /> Assign
          </button>
        </div>
      )}

      {availableProcesses.length === 0 && existing.length === 0 && (
        <p className="text-xs text-gray-400">No process definitions exist yet. Add some in the Processes tab first.</p>
      )}
    </Modal>
  )
}

// ── machine row ────────────────────────────────────────────────────────────

function MachineRow({
  m,
  processes,
  nsId,
}: {
  m: NamespaceTopology['machines'][0]
  processes: ProcessDefinition[]
  nsId: string
}) {
  const qc = useQueryClient()
  const [showAssign, setShowAssign] = useState(false)

  const deleteMut = useMutation({
    mutationFn: () => deleteMachine(m.machine.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['topology'] }),
  })

  return (
    <>
      <div className="px-4 py-2 group">
        <div className="flex items-center gap-2 text-sm">
          <Cpu size={13} className="text-gray-400 flex-shrink-0" />
          <span className="font-medium text-gray-900 dark:text-gray-100">{m.machine.hostname}</span>
          <StatusBadge status={m.sidecar?.status} />
          {m.sidecar && <span className="text-xs text-gray-400">:{m.sidecar.port}</span>}
          {m.sidecar?.version
            ? <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-500 dark:text-stone-400">v{m.sidecar.version}</span>
            : m.sidecar && <span className="text-xs text-gray-400">v?</span>
          }
          <div className="ml-auto flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => setShowAssign(true)}
              className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30"
            >
              <Plus size={11} /> Processes
            </button>
            <button
              onClick={() => { if (window.confirm(`Delete machine "${m.machine.hostname}"?`)) deleteMut.mutate() }}
              className="rounded p-0.5 text-gray-400 hover:text-red-500"
            >
              <Trash2 size={12} />
            </button>
          </div>
        </div>
        {m.processes.length > 0 && (
          <div className="mt-1 ml-5 flex flex-wrap gap-1">
            {m.processes.map((p) => (
              <span key={p.id} className="rounded-full bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300">
                {p.name}
              </span>
            ))}
          </div>
        )}
      </div>
      {showAssign && (
        <AssignProcessModal
          machineId={m.machine.id}
          processes={processes}
          onClose={() => setShowAssign(false)}
        />
      )}
    </>
  )
}

// ── namespace card ─────────────────────────────────────────────────────────

function NamespaceCard({
  ns,
  processes,
}: {
  ns: NamespaceTopology
  processes: ProcessDefinition[]
}) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(true)
  const [addingMachine, setAddingMachine] = useState(false)
  const [hostname, setHostname] = useState('')
  const [machineDesc, setMachineDesc] = useState('')

  const addMachineMut = useMutation({
    mutationFn: () => createMachine(ns.namespace.id, { hostname: hostname.trim(), description: machineDesc.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['topology'] })
      setAddingMachine(false)
      setHostname('')
      setMachineDesc('')
    },
  })

  const deleteNsMut = useMutation({
    mutationFn: () => deleteNamespace(ns.namespace.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['topology'] }),
  })

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* namespace header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-800 group">
        <button onClick={() => setExpanded((v) => !v)} className="flex items-center gap-2 flex-1 text-left">
          {expanded ? <ChevronDown size={13} className="text-gray-400" /> : <ChevronRight size={13} className="text-gray-400" />}
          <Server size={13} className="text-gray-600 dark:text-gray-300" />
          <span className="font-semibold text-sm text-gray-800 dark:text-gray-200">{ns.namespace.name}</span>
          {ns.namespace.description && (
            <span className="text-xs font-normal text-gray-400">— {ns.namespace.description}</span>
          )}
        </button>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setAddingMachine(true)}
            className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-950/30"
          >
            <Plus size={11} /> Machine
          </button>
          <button
            onClick={() => { if (window.confirm(`Delete namespace "${ns.namespace.name}" and all its machines?`)) deleteNsMut.mutate() }}
            className="rounded p-0.5 text-gray-400 hover:text-red-500"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* machines */}
      {expanded && (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {ns.machines.map((m) => (
            <MachineRow key={m.machine.id} m={m} processes={processes} nsId={ns.namespace.id} />
          ))}
          {ns.machines.length === 0 && (
            <div className="px-4 py-2 text-xs text-gray-400">No machines — hover and click "+ Machine" above to add one</div>
          )}

          {/* inline add-machine form */}
          {addingMachine && (
            <div className="px-4 py-3 bg-blue-50 dark:bg-blue-950/20 space-y-2">
              <p className="text-xs font-medium text-blue-700 dark:text-blue-300">Add machine to {ns.namespace.name}</p>
              <input
                autoFocus
                type="text"
                value={hostname}
                onChange={(e) => setHostname(e.target.value)}
                placeholder="Hostname, e.g. server1.stirt.internal"
                className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={machineDesc}
                onChange={(e) => setMachineDesc(e.target.value)}
                placeholder="Description (optional)"
                className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => addMachineMut.mutate()}
                  disabled={!hostname.trim()}
                  className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  Add
                </button>
                <button
                  onClick={() => { setAddingMachine(false); setHostname(''); setMachineDesc('') }}
                  className="rounded px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── main view ──────────────────────────────────────────────────────────────

export function TopologyView() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['topology'], queryFn: getTopology, refetchInterval: 30000 })
  const { data: processes = [] } = useQuery({ queryKey: ['processes'], queryFn: getProcesses })

  const [addingNs, setAddingNs] = useState(false)
  const [nsName, setNsName] = useState('')
  const [nsDesc, setNsDesc] = useState('')

  const addNsMut = useMutation({
    mutationFn: () => createNamespace({ name: nsName.trim(), description: nsDesc.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['topology'] })
      setAddingNs(false)
      setNsName('')
      setNsDesc('')
    },
  })

  if (isLoading) return <p className="text-sm text-gray-500">Loading topology…</p>
  if (error) return <p className="text-sm text-red-500">Error loading topology</p>

  return (
    <div className="space-y-4">
      {(data ?? []).map((ns) => (
        <NamespaceCard key={ns.namespace.id} ns={ns} processes={processes} />
      ))}

      {(!data || data.length === 0) && !addingNs && (
        <p className="text-sm text-gray-500">No namespaces yet.</p>
      )}

      {/* add namespace */}
      {addingNs ? (
        <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/20 p-4 space-y-2">
          <p className="text-xs font-medium text-blue-700 dark:text-blue-300">New namespace</p>
          <input
            autoFocus
            type="text"
            value={nsName}
            onChange={(e) => setNsName(e.target.value)}
            placeholder="Name, e.g. STIRT"
            className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyDown={(e) => e.key === 'Enter' && nsName.trim() && addNsMut.mutate()}
          />
          <input
            type="text"
            value={nsDesc}
            onChange={(e) => setNsDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <button
              onClick={() => addNsMut.mutate()}
              disabled={!nsName.trim()}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Create
            </button>
            <button
              onClick={() => { setAddingNs(false); setNsName(''); setNsDesc('') }}
              className="rounded px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAddingNs(true)}
          className="flex items-center gap-1 rounded border border-dashed border-gray-300 dark:border-gray-700 px-4 py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 w-full justify-center transition-colors"
        >
          <Plus size={14} /> Add namespace
        </button>
      )}
    </div>
  )
}
