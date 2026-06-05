import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import Chat from './components/Chat'
import Dashboard from './components/Dashboard'

export default function App() {
  return (
    <BrowserRouter>
      <nav className="nav">
        <span className="nav-brand">MOEI AI Assistant</span>
        <div className="nav-links">
          <NavLink to="/chat" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
            Web Chat
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
            Dashboard
          </NavLink>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
