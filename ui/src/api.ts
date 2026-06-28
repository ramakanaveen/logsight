import type { ProcessDefinition, Namespace, Machine, MachineProcess, NamespaceTopology, Conversation, Message, SSEEvent } from './types'

const BASE = '/v1'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${body}`)
  }
  return res.json()
}

// Process definitions
export const getProcesses = () => req<ProcessDefinition[]>('/processes')
export const createProcess = (body: Partial<ProcessDefinition>) => req<ProcessDefinition>('/processes', { method: 'POST', body: JSON.stringify(body) })
export const updateProcess = (id: string, body: Partial<ProcessDefinition>) => req<ProcessDefinition>(`/processes/${id}`, { method: 'PUT', body: JSON.stringify(body) })
export const deleteProcess = (id: string) => fetch(BASE + `/processes/${id}`, { method: 'DELETE' })

// Namespaces
export const getNamespaces = () => req<Namespace[]>('/namespaces')
export const createNamespace = (body: { name: string; description?: string }) => req<Namespace>('/namespaces', { method: 'POST', body: JSON.stringify(body) })
export const updateNamespace = (id: string, body: { name?: string; description?: string }) => req<Namespace>(`/namespaces/${id}`, { method: 'PUT', body: JSON.stringify(body) })
export const deleteNamespace = (id: string) => fetch(BASE + `/namespaces/${id}`, { method: 'DELETE' })

// Machines
export const getMachines = (nsId: string) => req<Machine[]>(`/namespaces/${nsId}/machines`)
export const createMachine = (nsId: string, body: { hostname: string; description?: string }) => req<Machine>(`/namespaces/${nsId}/machines`, { method: 'POST', body: JSON.stringify(body) })
export const updateMachine = (id: string, body: { hostname?: string; description?: string }) => req<Machine>(`/machines/${id}`, { method: 'PUT', body: JSON.stringify(body) })
export const deleteMachine = (id: string) => fetch(BASE + `/machines/${id}`, { method: 'DELETE' })

// Machine processes
export const getMachineProcesses = (machineId: string) => req<MachineProcess[]>(`/machines/${machineId}/processes`)
export const assignProcess = (machineId: string, body: { process_definition_id: string; log_paths: string[] }) =>
  req<MachineProcess>(`/machines/${machineId}/processes`, { method: 'POST', body: JSON.stringify(body) })
export const removeMachineProcess = (machineId: string, mpId: string) => fetch(BASE + `/machines/${machineId}/processes/${mpId}`, { method: 'DELETE' })

// Topology
export const getTopology = () => req<NamespaceTopology[]>('/topology')

// Conversations
export const getConversations = () => req<Conversation[]>('/conversations')
export const getConversationMessages = (id: string) => req<Message[]>(`/conversations/${id}/messages`)
export const deleteConversation = (id: string) => fetch(BASE + `/conversations/${id}`, { method: 'DELETE' })

// Feedback
export const submitFeedback = (body: {
  conversation_id: string
  message_id: string
  rating: 1 | -1
  comment: string
}) => req('/feedback', { method: 'POST', body: JSON.stringify(body) })

// Chat streaming
export async function* streamChat(payload: {
  question: string
  conversation_id?: string | null
  process_hint?: string | null
}): AsyncGenerator<SSEEvent> {
  const res = await fetch(BASE + '/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok || !res.body) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${body}`)
  }

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch {
          // skip malformed
        }
      }
    }
  }
}
