import { useEffect, useRef, useState } from 'react'

// Relative URLs — proxied by Vite (dev) or nginx (prod) through port 3000
// This makes the app work behind any public URL (ngrok, Railway, etc.) without rebuilding
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:'

// Deterministic session id for a phone number — re-entering the same phone
// after Logout always maps to the same session, so history can be restored.
function sessionIdFromPhone(phone) {
  return 'webchat_' + phone.replace(/[^a-zA-Z0-9]/g, '')
}

function getSessionId(phone) {
  let id = localStorage.getItem('moei_session_id')
  if (!id) {
    id = phone ? sessionIdFromPhone(phone) : 'webchat_' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem('moei_session_id', id)
  }
  return id
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function Chat() {
  const WELCOME = { role: 'agent', text: 'Hello! I\'m the MOEI AI Assistant. How can I help you today?\nمرحباً! أنا مساعد وزارة الطاقة والبنية التحتية. كيف يمكنني مساعدتك؟', time: new Date() }

  const [phone, setPhone]         = useState(() => localStorage.getItem('moei_phone'))
  const [phoneInput, setPhoneInput] = useState('')
  const [messages, setMessages]   = useState([WELCOME])
  const [input, setInput]         = useState('')
  const [status, setStatus]       = useState('connecting')
  const [isTyping, setIsTyping]   = useState(false)
  const [recording, setRecording] = useState(false)

  const wsRef            = useRef(null)
  const bottomRef        = useRef(null)
  const sessionId        = useRef(getSessionId(phone))
  const mediaRecorderRef = useRef(null)
  const chunksRef        = useRef([])

  useEffect(() => {
    if (!phone) return
    loadHistory()
    connect()
    return () => wsRef.current?.close()
  }, [phone])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  async function loadHistory() {
    try {
      // Passing phone lets the backend prefer the customer's shared
      // cross-channel memory (e.g. a Telegram conversation), so it shows up
      // here too — see /api/session/{session_id}.
      const params = phone ? `?phone=${encodeURIComponent(phone)}` : ''
      const res = await fetch(`/api/session/${sessionId.current}${params}`)
      const history = await res.json()
      if (!history.length) return
      setMessages([WELCOME, ...history.map(m => ({ role: m.role, text: m.text, time: new Date() }))])
    } catch {}
  }

  function newChat() {
    wsRef.current?.close()
    const id = 'webchat_' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem('moei_session_id', id)
    sessionId.current = id
    setMessages([WELCOME])
    setInput('')
    setIsTyping(false)
    connect()
  }

  function submitPhone(e) {
    e.preventDefault()
    const trimmed = phoneInput.trim()
    if (!trimmed) return
    const id = sessionIdFromPhone(trimmed)
    localStorage.setItem('moei_phone', trimmed)
    localStorage.setItem('moei_session_id', id)
    sessionId.current = id
    setPhone(trimmed)
  }

  // Logout: clear identity + session, return to the phone gate. Re-entering
  // the same phone derives the same session id again, so loadHistory()
  // restores the conversation; a different phone starts fresh.
  function logout() {
    wsRef.current?.close()
    localStorage.removeItem('moei_phone')
    localStorage.removeItem('moei_session_id')
    setPhone(null)
    setPhoneInput('')
    setMessages([WELCOME])
    setStatus('connecting')
  }

  function connect() {
    setStatus('connecting')
    const params = phone ? `?phone=${encodeURIComponent(phone)}` : ''
    const ws = new WebSocket(`${WS_PROTOCOL}//${location.host}/ws/${sessionId.current}${params}`)
    ws.onopen  = () => setStatus('connected')
    ws.onclose = () => { setStatus('disconnected'); setTimeout(connect, 3000) }
    ws.onerror = () => setStatus('disconnected')
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setIsTyping(false)
      setMessages(prev => [...prev, { role: 'agent', text: data.text, time: new Date(), ticketId: data.ticket_id }])
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
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  // ── Voice ──────────────────────────────────────────────────────────────────

  async function toggleRecording() {
    if (recording) {
      mediaRecorderRef.current?.stop()
      setRecording(false)
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const mr = new MediaRecorder(stream)
        chunksRef.current = []
        mr.ondataavailable = e => chunksRef.current.push(e.data)
        mr.onstop = () => {
          stream.getTracks().forEach(t => t.stop())
          sendVoiceMessage(new Blob(chunksRef.current, { type: 'audio/webm' }))
        }
        mr.start()
        mediaRecorderRef.current = mr
        setRecording(true)
      } catch {
        alert('Microphone access denied. Please allow microphone access in your browser.')
      }
    }
  }

  async function sendVoiceMessage(blob) {
    setIsTyping(true)
    const form = new FormData()
    form.append('audio', blob, 'recording.webm')
    form.append('session_id', sessionId.current)
    if (phone) form.append('phone', phone)

    try {
      const res  = await fetch('/voice/message', { method: 'POST', body: form })
      const data = await res.json()

      if (data.error) {
        setIsTyping(false)
        setMessages(prev => [...prev, { role: 'agent', text: `⚠️ Voice error: ${data.error}`, time: new Date() }])
        return
      }

      setMessages(prev => [...prev,
        { role: 'user',  text: `🎤 ${data.transcript}`, time: new Date() },
        { role: 'agent', text: data.agent.text, time: new Date(), ticketId: data.agent.ticket_id },
      ])

      if (data.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`)
        audio.play().catch(() => {})
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', text: '⚠️ Voice processing failed. Please try again.', time: new Date() }])
    } finally {
      setIsTyping(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!phone) {
    return (
      <div className="chat-layout">
        <div className="phone-gate">
          <div className="phone-gate-card">
            <div className="chat-header-title" style={{ marginBottom: 8 }}>Welcome to MOEI Customer Support</div>
            <p style={{ color: '#6b7280', fontSize: 13, marginBottom: 16 }}>
              Share your phone number so we recognize you across WhatsApp, voice, and web chat.
            </p>
            <form onSubmit={submitPhone} style={{ display: 'flex', gap: 8 }}>
              <input
                type="tel"
                className="chat-input phone-input"
                placeholder="+9715xxxxxxxx"
                value={phoneInput}
                onChange={e => setPhoneInput(e.target.value)}
                autoFocus
              />
              <button type="submit" className="send-btn" disabled={!phoneInput.trim()}>Continue</button>
            </form>
          </div>
        </div>
      </div>
    )
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
          <button onClick={logout} style={{ fontSize: 12, padding: '4px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: 'white', cursor: 'pointer', color: '#6b7280' }}>
            Logout
          </button>
        </div>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="bubble">{m.text}</div>
            {m.ticketId && <span className="ticket-badge">Ticket #{m.ticketId} created</span>}
            <span className="meta">{formatTime(m.time)}</span>
          </div>
        ))}
        {isTyping && (
          <div className="message agent typing">
            <div className="bubble">{recording ? 'Processing voice…' : 'Assistant is typing…'}</div>
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
          onClick={toggleRecording}
          title={recording ? 'Stop recording' : 'Record voice message'}
          style={{
            padding: '10px 14px',
            borderRadius: 8,
            border: recording ? '2px solid #ef4444' : '1px solid #e5e7eb',
            background: recording ? '#fee2e2' : 'white',
            cursor: 'pointer',
            fontSize: 18,
            transition: 'all 0.2s',
          }}
        >
          {recording ? '⏹' : '🎤'}
        </button>
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
