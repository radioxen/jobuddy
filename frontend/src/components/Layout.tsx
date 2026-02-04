import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  FileText,
  MessageSquare,
  Briefcase,
} from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store'
import { useEffect } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/jobs', icon: Search, label: 'Jobs' },
  { to: '/applications', icon: FileText, label: 'Applications' },
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
]

export default function Layout() {
  const { connected, statusUpdates, latestStatus } = useWebSocket()
  const notifications = useAppStore((s) => s.notifications)
  const removeNotification = useAppStore((s) => s.removeNotification)

  // Auto-dismiss notifications after 5s
  useEffect(() => {
    notifications.forEach((n) => {
      setTimeout(() => removeNotification(n.id), 5000)
    })
  }, [notifications, removeNotification])

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <nav
        style={{
          width: 220,
          background: '#1a1a2e',
          color: '#fff',
          padding: '20px 0',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            padding: '0 20px 20px',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <Briefcase size={24} />
          <span style={{ fontSize: 20, fontWeight: 700 }}>JobBuddy</span>
        </div>

        <div style={{ flex: 1, padding: '20px 0' }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 20px',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.6)',
                background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                textDecoration: 'none',
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                borderLeft: isActive ? '3px solid #4CAF50' : '3px solid transparent',
                transition: 'all 0.2s',
              })}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Connection status */}
        <div style={{ padding: '10px 20px', fontSize: 12 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: connected ? '#4CAF50' : '#f44336',
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: connected ? '#4CAF50' : '#f44336',
              }}
            />
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        {/* Status bar */}
        {latestStatus.flow_update && (
          <div
            style={{
              background: '#e3f2fd',
              border: '1px solid #90caf9',
              borderRadius: 8,
              padding: '10px 16px',
              marginBottom: 16,
              fontSize: 14,
              color: '#1565c0',
            }}
          >
            {latestStatus.flow_update.message}
          </div>
        )}

        {/* Notifications */}
        {notifications.map((n) => (
          <div
            key={n.id}
            style={{
              background: n.type === 'error' ? '#fce4ec' : '#e8f5e9',
              border: `1px solid ${n.type === 'error' ? '#ef9a9a' : '#a5d6a7'}`,
              borderRadius: 8,
              padding: '10px 16px',
              marginBottom: 8,
              fontSize: 14,
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            {n.message}
            <button
              onClick={() => removeNotification(n.id)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 16,
              }}
            >
              x
            </button>
          </div>
        ))}

        <Outlet />
      </main>
    </div>
  )
}
