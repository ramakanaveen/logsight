export interface ProcessDefinition {
  id: string
  name: string
  description: string
  example_qa: { question: string; answer: string }[]
  created_at: string
  updated_at: string
}

export interface Namespace {
  id: string
  name: string
  description: string
  created_at: string
}

export interface Machine {
  id: string
  namespace_id: string
  hostname: string
  description: string
  created_at: string
}

export interface SidecarInstance {
  id: string
  machine_id: string
  port: number
  status: 'alive' | 'dead'
  version: string | null
  last_heartbeat: string
  registered_at: string
}

export interface MachineProcess {
  id: string
  machine_id: string
  process_definition_id: string
  process_name: string
  log_paths: string[]
}

export interface ProcessInTopology {
  id: string
  name: string
  log_paths: string[]
}

export interface MachineInTopology {
  machine: Machine
  sidecar: SidecarInstance | null
  processes: ProcessInTopology[]
}

export interface NamespaceTopology {
  namespace: Namespace
  machines: MachineInTopology[]
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface SourceInfo {
  process: string
  machine: string
  files_searched: number
  lines_matched: number
  matched_files: string[]
}

export interface UsageInfo {
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
}

export interface ChartDataset {
  label: string
  data: number[]
}

export interface ChartSpec {
  chart_type: 'bar' | 'line' | 'pie'
  title: string
  labels: string[]
  datasets: ChartDataset[]
}

// SSE event types emitted by POST /v1/chat/stream
export type SSEEvent =
  | { type: 'thinking'; data: { text: string } }
  | { type: 'tool_call'; data: { tool: string; input: Record<string, unknown> } }
  | { type: 'tool_result'; data: { tool: string; result: unknown } }
  | { type: 'clarify'; data: { question: string; options?: string[] } }
  | { type: 'answer'; data: { text: string } }
  | { type: 'sources'; data: SourceInfo[] }
  | { type: 'usage'; data: UsageInfo }
  | { type: 'chart'; data: ChartSpec }
  | { type: 'done'; data: { conversation_id: string; message_id?: string; clarify?: boolean } }
  | { type: 'error'; data: { message: string } }

export interface ChatTurn {
  question: string
  thinkingText?: string
  toolCalls: { tool: string; input: Record<string, unknown>; result?: unknown }[]
  answerText?: string
  sources: SourceInfo[]
  usage?: UsageInfo
  chart?: ChartSpec
  conversationId?: string
  messageId?: string
  clarifyQuestion?: string
  clarifyOptions?: string[]
  error?: string
  loading: boolean
}
