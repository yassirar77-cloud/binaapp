'use client'

// Recharts is heavy (~100kB+). These chart blocks live in their own module so
// the /founder route can load them lazily via next/dynamic instead of
// bundling recharts into the page's first-load JS.
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

interface NameValue {
  name: string
  value: number
}

export function PlanPieChart({ data }: { data: NameValue[] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip
          contentStyle={{
            background: '#161623',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10,
            fontSize: 12,
          }}
          itemStyle={{ color: '#F7F7FA' }}
          labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ValueBarChart({ data, fill, height = 250 }: { data: NameValue[]; fill: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="name" stroke="#9CA3AF" />
        <YAxis stroke="#9CA3AF" />
        <Tooltip
          contentStyle={{
            background: '#161623',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10,
            fontSize: 12,
          }}
          itemStyle={{ color: '#F7F7FA' }}
          labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
        />
        <Bar dataKey="value" fill={fill} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function UserGrowthChart({ data }: { data: { month: string; users: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="month" stroke="#9CA3AF" />
        <YAxis stroke="#9CA3AF" />
        <Tooltip
          contentStyle={{
            background: '#161623',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10,
            fontSize: 12,
          }}
          itemStyle={{ color: '#F7F7FA' }}
          labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
        />
        <Line type="monotone" dataKey="users" stroke="#3B82F6" strokeWidth={2} dot={{ fill: '#3B82F6' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
