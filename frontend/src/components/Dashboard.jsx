import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell, PieChart, Pie, Legend } from 'recharts'

// Relative URL — proxied through port 3000, works behind any public URL
const BACKEND_URL = ''
const POLL_INTERVAL = 5000

const CHANNEL_COLORS = {
  telegram: '#0088cc',
  webchat: '#006241',
  whatsapp: '#25d366',
  voice: '#c8a951',
}

const STATUS_COLORS = {
  open: '#22c55e',
  in_progress: '#f59e0b',
  resolved: '#94a3b8',
  escalated: '#ef4444',
}

const SENTIMENT_COLORS = {
  positive: '#22c55e',
  neutral: '#94a3b8',
  negative: '#ef4444',
}

const SENTIMENT_EMOJI = { positive: '😊', neutral: '😐', negative: '😟' }

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [copilot, setCopilot] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [])

  async function fetchAll() {
    await Promise.all([fetchMetrics(), fetchCopilot()])
    setLastUpdated(new Date())
  }

  async function fetchMetrics() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/metrics`)
      setData(await res.json())
    } catch {}
  }

  async function fetchCopilot() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/copilot`)
      setCopilot(await res.json())
    } catch {}
  }

  if (!data) return <div style={{ padding: 32, color: '#6b7280' }}>Loading metrics…</div>

  const channelData = Object.entries(data.messages_by_channel || {}).map(([name, value]) => ({ name, value }))

  const statusData = Object.entries(data.tickets || {})
    .filter(([k]) => ['open', 'in_progress', 'resolved', 'escalated'].includes(k))
    .map(([name, value]) => ({ name, value }))

  const sentimentData = ['positive', 'neutral', 'negative'].map(s => ({
    name: s,
    value: data.sentiment_stats?.[s] || 0,
  })).filter(d => d.value > 0)

  const escalatedCount = data.tickets?.escalated || 0

  return (
    <div className="dashboard-layout">
      <div className="dashboard-title">Operations Dashboard</div>

      {/* Stats row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Active Sessions</div>
          <div className="stat-value">{data.active_sessions}</div>
        </div>
        <div className="stat-card accent">
          <div className="stat-label">Total Tickets</div>
          <div className="stat-value">{data.tickets?.total || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open Tickets</div>
          <div className="stat-value">{data.tickets?.open || 0}</div>
        </div>
        <div className="stat-card warn">
          <div className="stat-label">Escalated</div>
          <div className="stat-value">{escalatedCount}</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-title">Messages by Channel</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={channelData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {channelData.map((entry) => (
                  <Cell key={entry.name} fill={CHANNEL_COLORS[entry.name] || '#006241'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <div className="chart-title">Tickets by Status</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={statusData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
                labelLine={false}
              >
                {statusData.map((entry) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#94a3b8'} />
                ))}
              </Pie>
              <Tooltip />
              <Legend iconSize={10} iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <div className="chart-title">Customer Sentiment</div>
          {sentimentData.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: 13, paddingTop: 16 }}>No sentiment data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={sentimentData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => `${SENTIMENT_EMOJI[name] || ''} ${name}: ${value}`}
                  labelLine={false}
                >
                  {sentimentData.map((entry) => (
                    <Cell key={entry.name} fill={SENTIMENT_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconSize={10} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Co-pilot panel */}
      <div className="table-card">
        <div className="chart-title">AI Co-pilot — Suggested Replies</div>
        <p style={{ color: '#6b7280', fontSize: 12, margin: '0 0 12px' }}>
          Live view of recent conversations. Use these AI-generated suggestions to respond faster.
        </p>
        {!copilot?.suggestions?.length ? (
          <p style={{ color: '#9ca3af', fontSize: 14 }}>No active conversations.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {copilot.suggestions.map((s, i) => (
              <div key={i} style={{
                border: '1px solid #e5e7eb',
                borderRadius: 8,
                padding: '12px 16px',
                background: s.sentiment === 'negative' ? '#fff5f5' : s.sentiment === 'positive' ? '#f0fdf4' : '#fafafa',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, color: '#6b7280' }}>
                    <strong>{s.channel}</strong> · {s.session_id} · {new Date(s.timestamp).toLocaleTimeString()}
                  </span>
                  <span style={{ fontSize: 11 }}>
                    {SENTIMENT_EMOJI[s.sentiment] || ''} {s.sentiment}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>
                  <strong>Customer:</strong> {s.user_message}
                </div>
                {s.suggested_reply && (
                  <div style={{ fontSize: 13, color: '#006241', background: '#f0fdf4', padding: '6px 10px', borderRadius: 6 }}>
                    <strong>AI suggestion:</strong> {s.suggested_reply}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent tickets */}
      <div className="table-card">
        <div className="chart-title">Recent Tickets</div>
        {data.recent_tickets?.length === 0 ? (
          <p style={{ color: '#6b7280', fontSize: 14, padding: '8px 0' }}>No tickets yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Channel</th>
                <th>Status</th>
                <th>Escalated</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_tickets?.map(t => (
                <tr key={t.id}>
                  <td>#{t.id}</td>
                  <td>{t.channel}</td>
                  <td><span className={`badge ${t.status}`}>{t.status}</span></td>
                  <td>{t.escalate ? '🔴 Yes' : '—'}</td>
                  <td>{new Date(t.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {lastUpdated && (
          <div className="refresh-note">Auto-refresh every 5s · Last updated {lastUpdated.toLocaleTimeString()}</div>
        )}
      </div>
    </div>
  )
}
