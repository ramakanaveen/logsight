import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { ChartSpec } from '../types'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

interface Props {
  spec: ChartSpec
}

export function ChartBlock({ spec }: Props) {
  const { chart_type, title, labels, datasets } = spec

  if (chart_type === 'pie') {
    const data = labels.map((label, i) => ({
      name: label,
      value: datasets[0]?.data[i] ?? 0,
    }))
    return (
      <div className="my-3">
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{title}</p>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const data = labels.map((label, i) => {
    const point: Record<string, string | number> = { name: label }
    for (const ds of datasets) {
      point[ds.label] = ds.data[i] ?? 0
    }
    return point
  })

  if (chart_type === 'line') {
    return (
      <div className="my-3">
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{title}</p>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.3} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            {datasets.length > 1 && <Legend />}
            {datasets.map((ds, i) => (
              <Line
                key={ds.label}
                type="monotone"
                dataKey={ds.label}
                stroke={COLORS[i % COLORS.length]}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // default: bar
  return (
    <div className="my-3">
      <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.3} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {datasets.length > 1 && <Legend />}
          {datasets.map((ds, i) => (
            <Bar key={ds.label} dataKey={ds.label} fill={COLORS[i % COLORS.length]} radius={[2, 2, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
