import { useEffect, useRef, useState } from 'react'

const BACKEND_WS  = import.meta.env.VITE_BACKEND_WS_URL  || 'ws://localhost:8000'
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL     || 'http://localhost:8000'

function getSessionId() {
  let id = localStorage.getItem('moei_session_id')
  if (!id) {
    id = 'webchat_' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem('moei_session_id', id)
  }
  return id
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function Chat() {
  const WELCOME = { role: 'agent', text: 'Hello! I\'m the MOEI AI Assistant. How can I help you today?\nمرحباً! أنا مساعد وزارة الطاقة والبنية التحتية. كيف يمكنني مساعدتك؟', time: new Date() }

  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('connecting')
  const [isTyping, setIsTyping] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const sessionId = useRef(getSessionId())

  useEffect(() => {
    loadHistory()
    connect()
    return () => wsRef.current?.close()
  }, [])

  async function loadHistory() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/session/${sessionId.current}`)
      const history = await res.json()
      if (!history.length) return
      const restored = history.map(m => ({ role: m.role, text: m.text, time: new Date() }))
      setMessages([WELCOME, ...restored])
    } catch {}
  }

  function newChat() {
    wsRef.current?.close()
    localStorage.removeItem('moei_session_id')
    sessionId.current = getSessionId()
    setMessages([WELCOME])
    setInput('')
    setIsTyping(false)
    connect()
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  function connect() {
    setStatus('connecting')
    const ws = new WebSocket(`${BACKEND_WS}/ws/${sessionId.current}`)

    ws.onopen = () => setStatus('connected')
    ws.onclose = () => {
      setStatus('disconnected')
      setTimeout(connect, 3000)
    }
    ws.onerror = () => setStatus('disconnected')

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        role: 'agent',
        text: data.text,
        time: new Date(),
        ticketId: data.ticket_id,
        escalate: data.escalate,
      }])
    }

    wsRef.current = ws
  }

  function send() {
    const text = input.trim()
    if (!text || status !== 'connected') return

    setMessages(prev => [...prev, { role: 'user', text, time: new Date() }])
    setInput('')
    setIsTyping(true)
    wsRef.current.send(text)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-layout">
      <div className="chat-header">
        <div>
          <span className="chat-header-title">Customer Support</span>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sessionId.current}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="status-text">
            <span className={`status-dot ${status}`} />
            {status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Reconnecting...'}
          </span>
          <button onClick={newChat} style={{ fontSize: 12, padding: '4px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: 'white', cursor: 'pointer', color: '#6b7280' }}>
            New Chat
          </button>
        </div>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="bubble">{m.text}</div>
            {m.ticketId && (
              <span className="ticket-badge">Ticket #{m.ticketId} created</span>
            )}
            <span className="meta">{formatTime(m.time)}</span>
          </div>
        ))}
        {isTyping && (
          <div className="message agent typing">
            <div className="bubble">Assistant is typing…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          rows={1}
          placeholder="Type a message… (Enter to send)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={status !== 'connected'}
        />
        <button
          className="send-btn"
          onClick={send}
          disabled={!input.trim() || status !== 'connected'}
        >
          Send
        </button>
      </div>
    </div>
  )
}
