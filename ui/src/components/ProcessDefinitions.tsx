import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProcesses, createProcess, updateProcess, deleteProcess } from '../api'
import { Plus, Pencil, Trash2, X, Save } from 'lucide-react'
import type { ProcessDefinition } from '../types'

interface QAPair { question: string; answer: string }

interface FormState {
  name: string
  description: string
  example_qa: QAPair[]
}

function blankForm(): FormState {
  return { name: '', description: '', example_qa: [] }
}

function ProcessModal({
  initial,
  onSave,
  onClose,
}: {
  initial: FormState
  onSave: (f: FormState) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<FormState>(initial)

  const addQA = () => setForm((f) => ({ ...f, example_qa: [...f.example_qa, { question: '', answer: '' }] }))
  const removeQA = (i: number) =>
    setForm((f) => ({ ...f, example_qa: f.example_qa.filter((_, idx) => idx !== i) }))
  const updateQA = (i: number, field: 'question' | 'answer', val: string) =>
    setForm((f) => {
      const qa = [...f.example_qa]
      qa[i] = { ...qa[i], [field]: val }
      return { ...f, example_qa: qa }
    })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-900 shadow-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {initial.name ? `Edit ${initial.name}` : 'New Process'}
          </h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-3">
          <label className="block">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Name</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="mt-1 w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="CurveBuilder"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Description</span>
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className="mt-1 w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Builds yield curves each morning"
            />
          </label>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Example Q&A</span>
              <button onClick={addQA} className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
                <Plus size={11} /> Add
              </button>
            </div>
            <div className="space-y-2">
              {form.example_qa.map((qa, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <div className="flex-1 space-y-1">
                    <input
                      type="text"
                      value={qa.question}
                      onChange={(e) => updateQA(i, 'question', e.target.value)}
                      placeholder="Question"
                      className="w-full rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                    <input
                      type="text"
                      value={qa.answer}
                      onChange={(e) => updateQA(i, 'answer', e.target.value)}
                      placeholder="Expected answer hint"
                      className="w-full rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <button onClick={() => removeQA(i)} className="mt-1 text-gray-400 hover:text-red-500">
                    <X size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            disabled={!form.name.trim()}
            className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save size={13} /> Save
          </button>
        </div>
      </div>
    </div>
  )
}

export function ProcessDefinitions() {
  const qc = useQueryClient()
  const { data: processes = [], isLoading } = useQuery({ queryKey: ['processes'], queryFn: getProcesses })
  const [editing, setEditing] = useState<ProcessDefinition | null | 'new'>(null)

  const refresh = () => qc.invalidateQueries({ queryKey: ['processes'] })

  const saveMutation = useMutation({
    mutationFn: async (form: FormState) => {
      if (!editing || editing === 'new') {
        return createProcess(form)
      }
      return updateProcess(editing.id, form)
    },
    onSuccess: () => { refresh(); setEditing(null) },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProcess(id),
    onSuccess: refresh,
  })

  const initialForm = (p: ProcessDefinition | null): FormState =>
    p
      ? { name: p.name, description: p.description, example_qa: p.example_qa }
      : blankForm()

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button
          onClick={() => setEditing('new')}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          <Plus size={13} /> Add Process
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}

      <div className="space-y-2">
        {processes.map((p) => (
          <div
            key={p.id}
            className="flex items-start justify-between rounded border border-gray-200 dark:border-gray-700 px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.name}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{p.description}</p>
              {p.example_qa.length > 0 && (
                <p className="text-xs text-gray-400 mt-0.5">{p.example_qa.length} Q&A pair(s)</p>
              )}
            </div>
            <div className="flex gap-1 ml-4 flex-shrink-0">
              <button
                onClick={() => setEditing(p)}
                className="rounded p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
              >
                <Pencil size={13} />
              </button>
              <button
                onClick={() => { if (window.confirm(`Delete "${p.name}"?`)) deleteMutation.mutate(p.id) }}
                className="rounded p-1.5 hover:bg-red-50 dark:hover:bg-red-950/30 text-gray-500 hover:text-red-500"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
        {!isLoading && processes.length === 0 && (
          <p className="text-sm text-gray-500">No processes registered yet.</p>
        )}
      </div>

      {editing !== null && (
        <ProcessModal
          initial={initialForm(editing === 'new' ? null : editing)}
          onSave={(form) => saveMutation.mutate(form)}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}
